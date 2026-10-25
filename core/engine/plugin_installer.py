"""AegisGate Plugin Auto-Installer & Virtual Environment Service (Idea 2).

Handles 1-Click installation of external plugins from:
1. Uploaded ZIP archive
2. Remote Git repository URL
3. Local template folder

Features:
- Hardened ZIP extraction (Zip Slip, symlinks, zip bombs, Windows ADS / drive paths)
- Strict plugin id (it becomes a directory name) and path containment checks
- Git clone restricted to allow-listed HTTPS hosts, no option injection, no prompts
- Entrypoint / requirements validation (no shell metacharacters, no `python -c`, no pip options/URLs)
- Replace-with-rollback: an existing plugin is only removed after the new one is in place
- Isolated virtualenv creation (`python -m venv .venv`) and pip installation
- Automatic database registration and Knowledge Store schema ingestion
- Real-time SSE broadcasting (`plugin_installed`)

NOTE: validation reduces the attack surface of *installing* a plugin. A plugin is still
arbitrary Python that runs with the Core's OS privileges; only install code you trust.
"""

import asyncio
import io
import json
import logging
import os
import re
import shutil
import stat
import subprocess
import sys
import uuid
import venv
import zipfile
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from sqlmodel import Session, select

from core.config import settings
from core.database import PluginProfile, utc_now
from core.engine.plugin_linter import PluginLinter
from core.gateway.sse_broadcaster import sse_broadcaster
from core.storage.knowledge_store import KnowledgeStore

logger = logging.getLogger(__name__)

PLUGIN_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
RESERVED_PLUGIN_IDS: frozenset[str] = frozenset({"templates", "__pycache__"})
_SHELL_META = re.compile(r"[;&|<>`$^%\r\n\"'(){}\\]")
_ENTRY_ARG = re.compile(r"^--?[A-Za-z0-9][A-Za-z0-9_.=:-]*$")
_PYTHON_NAMES: frozenset[str] = frozenset({"python", "python3", "py"})
_GIT_BRANCH = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,100}$")
_REQ_LINE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._\[\],<>=!~*+ ;\"'()-]*$")
_COPY_CHUNK = 64 * 1024


class PluginInstallerError(Exception):
    """Raised when plugin installation fails."""


def _rmtree(path: Path) -> None:
    """rmtree that also removes read-only files (git objects on Windows)."""

    def _on_error(func: Any, target: str, _exc: Any) -> None:
        try:
            os.chmod(target, stat.S_IWRITE)
            func(target)
        except OSError:
            pass

    shutil.rmtree(path, onerror=_on_error)


class PluginInstaller:
    """Manages the lifecycle of installing, extracting, building, and registering plugins."""

    def __init__(self, session: Session, plugins_dir: Path | None = None) -> None:
        self.session = session
        self.plugins_dir: Path = plugins_dir or settings.PLUGINS_DIR
        self.plugins_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ validation

    def _find_manifest(self, root_dir: Path) -> tuple[Path, dict[str, Any]]:
        """Locate manifest.json directly or in the single top-level directory of extracted archive."""
        direct_manifest = root_dir / "manifest.json"
        if direct_manifest.is_file():
            try:
                with open(direct_manifest, encoding="utf-8") as f:
                    return direct_manifest, json.load(f)
            except Exception as exc:
                raise PluginInstallerError(f"Failed to read manifest.json: {exc!s}") from exc

        # Check subdirectories
        subdirs = [p for p in root_dir.iterdir() if p.is_dir() and not p.name.startswith(".")]
        if len(subdirs) == 1:
            nested_manifest = subdirs[0] / "manifest.json"
            if nested_manifest.is_file():
                try:
                    with open(nested_manifest, encoding="utf-8") as f:
                        return nested_manifest, json.load(f)
                except Exception as exc:
                    raise PluginInstallerError(f"Failed to read nested manifest.json: {exc!s}") from exc

        raise PluginInstallerError(f"No valid manifest.json found in {root_dir}")

    def _validate_manifest(self, manifest: dict[str, Any]) -> None:
        """Validate required manifest schema fields (and that the id is a safe directory name)."""
        required_fields = ["id", "name", "driver", "entrypoint"]
        missing = [field for field in required_fields if field not in manifest or not str(manifest[field]).strip()]
        if missing:
            raise PluginInstallerError(f"Manifest missing required field(s): {', '.join(missing)}")

        plugin_id = str(manifest["id"]).strip()
        if not PLUGIN_ID_PATTERN.fullmatch(plugin_id):
            raise PluginInstallerError(
                f"Invalid plugin id '{plugin_id}': use 1-64 chars of a-z, 0-9, '_' or '-', starting with a letter or digit."
            )
        if plugin_id in RESERVED_PLUGIN_IDS:
            raise PluginInstallerError(f"Plugin id '{plugin_id}' is reserved.")

    def _plugin_path(self, plugin_id: str) -> Path:
        """Resolve the install directory for an id and prove it stays directly inside plugins/."""
        if not PLUGIN_ID_PATTERN.fullmatch(plugin_id) or plugin_id in RESERVED_PLUGIN_IDS:
            raise PluginInstallerError(f"Invalid plugin id '{plugin_id}'.")
        root = self.plugins_dir.resolve()
        target = (root / plugin_id).resolve()
        if target.parent != root:
            raise PluginInstallerError(f"Plugin id '{plugin_id}' escapes the plugins directory.")
        return target

    @staticmethod
    def _validate_entrypoint(entrypoint: str, plugin_dir: Path) -> None:
        """Entrypoint must be `python <relative_script.py> [--flag ...]` with no shell syntax."""
        entry = entrypoint.strip()
        if _SHELL_META.search(entry):
            raise PluginInstallerError("Entrypoint contains forbidden shell characters.")
        tokens = entry.split()
        if len(tokens) < 2 or tokens[0].lower() not in _PYTHON_NAMES:
            raise PluginInstallerError("Entrypoint must look like: python <script.py> [--flag ...]")

        script = tokens[1]
        if script.startswith("-"):
            raise PluginInstallerError("Entrypoint must name a script file (python -c / -m are not allowed).")
        if os.path.isabs(script) or re.match(r"^[A-Za-z]:", script) or ".." in Path(script).parts:
            raise PluginInstallerError("Entrypoint script must be a relative path inside the plugin.")
        root = plugin_dir.resolve()
        resolved = (root / script).resolve()
        if root not in resolved.parents or resolved.suffix != ".py" or not resolved.is_file():
            raise PluginInstallerError(f"Entrypoint script '{script}' must be an existing .py file inside the plugin.")

        for arg in tokens[2:]:
            if not _ENTRY_ARG.fullmatch(arg):
                raise PluginInstallerError(f"Entrypoint argument '{arg}' is not allowed.")

    @staticmethod
    def _validate_requirements(requirements_file: Path) -> None:
        """Only plain package specifiers: no pip options, URLs, VCS, local paths or direct references."""
        if not requirements_file.is_file():
            return
        try:
            lines = requirements_file.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeDecodeError) as exc:
            raise PluginInstallerError(f"Cannot read requirements.txt: {exc!s}") from exc
        for raw in lines:
            line = raw.split(" #", 1)[0].strip()
            if not line or line.startswith("#"):
                continue
            has_option = any(tok.startswith("-") for tok in line.split())  # --index-url, -r, --install-option=...
            if (
                has_option
                or "://" in line
                or "@" in line
                or "/" in line
                or "\\" in line
                or not _REQ_LINE.fullmatch(line)
            ):
                raise PluginInstallerError(f"requirements.txt line not allowed: '{line}'")

    @staticmethod
    def _reject_symlinks(root: Path) -> None:
        for dirpath, dirnames, filenames in os.walk(root):
            for name in dirnames + filenames:
                if (Path(dirpath) / name).is_symlink():
                    raise PluginInstallerError(f"Symbolic links are not allowed in plugins: {name}")

    @staticmethod
    def _validate_git_url(git_url: str) -> str:
        url = git_url.strip()
        if not url or url.startswith("-") or any(c.isspace() or ord(c) < 32 for c in url):
            raise PluginInstallerError("Invalid Git URL.")
        parsed = urlparse(url)
        if parsed.scheme != "https":
            raise PluginInstallerError("Only https:// Git URLs are allowed.")
        if parsed.username or parsed.password:
            raise PluginInstallerError("Credentials in Git URLs are not allowed.")
        host = (parsed.hostname or "").lower()
        allowed = {h.lower() for h in settings.PLUGIN_GIT_ALLOWED_HOSTS}
        if host not in allowed:
            raise PluginInstallerError(
                f"Git host '{host}' is not allowed. Allowed hosts: {', '.join(sorted(allowed)) or '(none)'}."
            )
        if parsed.port not in (None, 443):
            raise PluginInstallerError("Custom ports are not allowed for Git URLs.")
        return url

    # ------------------------------------------------------------------ ZIP extraction

    @staticmethod
    def _safe_extract(zip_file: zipfile.ZipFile, dest: Path) -> None:
        """Extract with Zip Slip / symlink / zip-bomb protection."""
        infos = zip_file.infolist()
        if len(infos) > settings.PLUGIN_MAX_ZIP_ENTRIES:
            raise PluginInstallerError(f"ZIP has too many entries (max {settings.PLUGIN_MAX_ZIP_ENTRIES}).")
        if sum(i.file_size for i in infos) > settings.PLUGIN_MAX_UNZIPPED_BYTES:
            raise PluginInstallerError("ZIP expands beyond the allowed size.")

        dest_root = dest.resolve()
        written_total = 0
        for info in infos:
            name = info.filename
            if (
                "\x00" in name
                or name.startswith(("/", "\\"))
                or re.match(r"^[A-Za-z]:", name)
                or ":" in name  # NTFS alternate data streams
            ):
                raise PluginInstallerError(f"Unsafe path in ZIP: {name!r}")
            if stat.S_ISLNK(info.external_attr >> 16):
                raise PluginInstallerError(f"Symbolic links are not allowed in ZIP: {name!r}")

            target = (dest_root / name).resolve()
            if target != dest_root and dest_root not in target.parents:
                raise PluginInstallerError(f"ZIP entry escapes the target directory: {name!r}")

            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue

            target.parent.mkdir(parents=True, exist_ok=True)
            with zip_file.open(info) as src, open(target, "wb") as dst:
                while True:
                    chunk = src.read(_COPY_CHUNK)
                    if not chunk:
                        break
                    written_total += len(chunk)
                    if written_total > settings.PLUGIN_MAX_UNZIPPED_BYTES:  # header may lie about size
                        raise PluginInstallerError("ZIP expands beyond the allowed size.")
                    dst.write(chunk)

    # ------------------------------------------------------------------ venv / registration

    def setup_isolated_venv(self, plugin_dir: Path) -> str:
        """Create an isolated virtual environment and install requirements.txt if present.

        Returns:
            The resolved python executable path for the plugin.
        """
        requirements_file = plugin_dir / "requirements.txt"
        if not requirements_file.is_file() or requirements_file.stat().st_size == 0:
            return sys.executable

        try:
            req_lines = [
                line.strip()
                for line in requirements_file.read_text(encoding="utf-8").splitlines()
                if line.strip() and not line.strip().startswith("#")
            ]
            if not req_lines:
                return sys.executable
        except (OSError, UnicodeDecodeError) as req_err:
            logger.debug("Requirements read exception: %s", req_err)
            return sys.executable

        venv_dir = plugin_dir / ".venv"
        is_windows = sys.platform.startswith("win")
        python_bin = venv_dir / "Scripts" / "python.exe" if is_windows else venv_dir / "bin" / "python"

        try:
            if not venv_dir.exists():
                logger.info("Creating isolated virtualenv at %s", venv_dir)
                venv.create(venv_dir, with_pip=True)

            logger.info("Installing requirements from %s into %s", requirements_file, venv_dir)
            cmd = [str(python_bin), "-m", "pip", "install", "-r", str(requirements_file), "--quiet"]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120, check=False)
            if proc.returncode != 0:
                logger.warning("pip install warning/failure in plugin venv: %s", proc.stderr)
        except Exception as exc:
            logger.warning("Could not set up isolated venv: %s. Falling back to host python.", exc)
            return sys.executable

        return str(python_bin) if python_bin.exists() else sys.executable

    def register_installed_plugin(
        self,
        manifest_file: Path,
        manifest: dict[str, Any],
        resolved_python_bin: str | None = None,
    ) -> PluginProfile:
        """Save plugin metadata in DB, adjust entrypoint, and ingest knowledge catalog."""
        plugin_id = manifest["id"].strip()
        plugin_dir = manifest_file.parent

        # Adjust entrypoint to absolute path or python bin if needed
        entrypoint = manifest["entrypoint"].strip()
        tokens = entrypoint.split()
        if resolved_python_bin and tokens and tokens[0].lower() in _PYTHON_NAMES and len(tokens) >= 2:
            # `python <script> [--flags]` -> "<venv python>" "<abs script>" [--flags]
            script_full_path = (plugin_dir / tokens[1]).resolve()
            extra = " ".join(tokens[2:])
            entrypoint = f'"{resolved_python_bin}" "{script_full_path}" {extra}'.strip()
        elif tokens and not os.path.isabs(tokens[0]):
            rest = " ".join(tokens[1:])
            if (plugin_dir / tokens[0]).exists():
                entrypoint = f'"{(plugin_dir / tokens[0]).resolve()!s}" {rest}'.strip()

        # Check existing or create new PluginProfile
        statement = select(PluginProfile).where(PluginProfile.id == plugin_id)
        profile = self.session.exec(statement).first()
        if not profile:
            profile = PluginProfile(
                id=plugin_id,
                name=manifest["name"],
                driver=manifest["driver"],
                entrypoint=entrypoint,
                dry_run_command=manifest.get("dry_run_command", "SET SHOWPLAN_XML ON"),
                abort_command=manifest.get("abort_command", "KILL {spid}"),
                config_json=json.dumps(manifest.get("config", {})),
                ui_schema_json=json.dumps(manifest.get("ui_schema", [])),
                custom_card_json=json.dumps(manifest.get("custom_card", {})),
                status="active",
                latency_ms=0.0,
                active_sessions_count=0,
                is_certified=False,
                created_at=utc_now(),
                updated_at=utc_now(),
            )
        else:
            profile.name = manifest["name"]
            profile.driver = manifest["driver"]
            profile.entrypoint = entrypoint
            profile.dry_run_command = manifest.get("dry_run_command", profile.dry_run_command)
            profile.abort_command = manifest.get("abort_command", profile.abort_command)
            profile.config_json = json.dumps(manifest.get("config", json.loads(profile.config_json or "{}")))
            profile.ui_schema_json = json.dumps(manifest.get("ui_schema", json.loads(profile.ui_schema_json or "[]")))
            profile.custom_card_json = json.dumps(
                manifest.get("custom_card", json.loads(profile.custom_card_json or "{}"))
            )
            profile.status = "active"
            profile.updated_at = utc_now()

        self.session.add(profile)
        self.session.commit()
        self.session.refresh(profile)

        # Ingest catalog if catalog metadata is provided in manifest
        catalog = manifest.get("catalog") or manifest.get("catalog_metadata")
        if catalog:
            try:
                store = KnowledgeStore(self.session)
                partitions = (
                    catalog
                    if isinstance(catalog, list)
                    else [{"partition_key": "Default", "title": f"{profile.name} Catalog", "catalog": catalog}]
                )
                store.ingest_plugin_catalog(
                    target_id=plugin_id,
                    catalog_partitions=partitions,
                )
            except Exception as exc:
                logger.warning("Failed to auto-ingest catalog for %s: %s", plugin_id, exc)

        return profile

    # ------------------------------------------------------------------ install pipeline

    def _swap_into_place(self, source_dir: Path, final_dir: Path, staging_dir: Path) -> Path | None:
        """Move the new plugin into plugins/<id>. An existing plugin is renamed to a backup, never deleted yet."""
        backup: Path | None = None
        if final_dir.exists():
            if not final_dir.is_dir() or not (
                (final_dir / "manifest.json").is_file() or (final_dir / "plugin_manifest.json").is_file()
            ):
                raise PluginInstallerError(
                    f"Refusing to overwrite '{final_dir.name}': it exists but is not a plugin directory."
                )
            backup = self.plugins_dir / f".replaced_{final_dir.name}_{uuid.uuid4().hex[:8]}"
            final_dir.rename(backup)

        try:
            shutil.move(str(source_dir), str(final_dir))
        except Exception:
            if backup is not None and not final_dir.exists():
                backup.rename(final_dir)
            raise
        if source_dir != staging_dir and staging_dir.exists():
            _rmtree(staging_dir)
        return backup

    async def _finalize_install(self, staging_dir: Path, plugin_id_override: str | None = None) -> PluginProfile:
        """Validate a staged plugin tree, move it into place, build its venv, register and certify it."""
        self._reject_symlinks(staging_dir)
        manifest_file, manifest = self._find_manifest(staging_dir)
        if plugin_id_override:
            manifest["id"] = plugin_id_override
        self._validate_manifest(manifest)

        plugin_id = manifest["id"].strip()
        source_dir = manifest_file.parent
        self._validate_entrypoint(manifest["entrypoint"], source_dir)
        self._validate_requirements(source_dir / "requirements.txt")
        final_dir = self._plugin_path(plugin_id)

        backup = self._swap_into_place(source_dir, final_dir, staging_dir)
        try:
            # pip / venv are blocking subprocess calls: keep them off the event loop
            resolved_python = await asyncio.to_thread(self.setup_isolated_venv, final_dir)
            profile = self.register_installed_plugin(
                manifest_file=final_dir / "manifest.json",
                manifest=manifest,
                resolved_python_bin=resolved_python,
            )
        except Exception:
            # Roll back: restore the previous plugin version if there was one
            if backup is not None:
                _rmtree(final_dir)
                backup.rename(final_dir)
            else:
                _rmtree(final_dir)
            raise
        if backup is not None:
            _rmtree(backup)

        # Run Certification Linter automatically
        try:
            linter = PluginLinter(self.session)
            await linter.verify_plugin(plugin_id)
            self.session.refresh(profile)
        except Exception as lint_exc:
            logger.warning("Sanity linter warning on install %s: %s", plugin_id, lint_exc)

        # Broadcast SSE notification
        try:
            await sse_broadcaster.broadcast(
                "plugin_installed",
                {
                    "id": profile.id,
                    "name": profile.name,
                    "driver": profile.driver,
                    "is_certified": profile.is_certified,
                },
            )
        except Exception as sse_err:
            logger.debug("SSE notification failed: %s", sse_err)

        return profile

    async def install_from_zip(self, zip_content: bytes, filename: str | None = None) -> PluginProfile:
        """Install a plugin from an uploaded ZIP archive."""
        if len(zip_content) > settings.PLUGIN_MAX_ZIP_BYTES:
            raise PluginInstallerError(
                f"ZIP is larger than the allowed {settings.PLUGIN_MAX_ZIP_BYTES // (1024 * 1024)} MB."
            )
        try:
            zip_file = zipfile.ZipFile(io.BytesIO(zip_content))
        except zipfile.BadZipFile as exc:
            raise PluginInstallerError("Uploaded file is not a valid ZIP archive.") from exc

        # Extract to a unique temporary staging folder inside plugins/
        staging_dir = self.plugins_dir / f".staged_{uuid.uuid4().hex}"
        staging_dir.mkdir(parents=True, exist_ok=True)

        try:
            self._safe_extract(zip_file, staging_dir)
            return await self._finalize_install(staging_dir)
        except Exception as exc:
            if staging_dir.exists():
                _rmtree(staging_dir)
            raise PluginInstallerError(f"Failed to install plugin from ZIP: {exc!s}") from exc

    async def install_from_git(
        self,
        git_url: str,
        branch: str | None = None,
        plugin_id_override: str | None = None,
    ) -> PluginProfile:
        """Clone and install a plugin from an allow-listed HTTPS Git repository."""
        try:
            url = self._validate_git_url(git_url)
            if branch is not None and (not _GIT_BRANCH.fullmatch(branch) or ".." in branch):
                raise PluginInstallerError("Invalid Git branch name.")
        except PluginInstallerError as exc:
            raise PluginInstallerError(f"Failed to install plugin from Git: {exc!s}") from exc

        staging_dir = self.plugins_dir / f".git_{uuid.uuid4().hex}"

        # `--` stops option parsing, protocol.allow limits transports, prompts are disabled.
        cmd = [
            "git",
            "-c",
            "protocol.allow=never",
            "-c",
            "protocol.https.allow=always",
            "-c",
            "core.symlinks=false",
            "clone",
            "--depth",
            "1",
            "--no-tags",
            "--single-branch",
        ]
        if branch:
            cmd.extend(["--branch", branch])
        cmd.extend(["--", url, str(staging_dir)])
        env = {**os.environ, "GIT_TERMINAL_PROMPT": "0", "GIT_ALLOW_PROTOCOL": "https"}

        try:
            logger.info("Cloning Git repository: %s", url)
            proc = await asyncio.to_thread(
                subprocess.run,
                cmd,
                capture_output=True,
                text=True,
                timeout=settings.PLUGIN_GIT_CLONE_TIMEOUT_SECONDS,
                check=False,
                env=env,
            )
            if proc.returncode != 0:
                raise PluginInstallerError(f"git clone failed: {proc.stderr.strip()[:500]}")

            git_meta = staging_dir / ".git"
            if git_meta.exists():
                _rmtree(git_meta)

            return await self._finalize_install(staging_dir, plugin_id_override=plugin_id_override)
        except Exception as exc:
            if staging_dir.exists():
                _rmtree(staging_dir)
            raise PluginInstallerError(f"Failed to install plugin from Git: {exc!s}") from exc
