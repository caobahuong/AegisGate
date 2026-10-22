"""AegisGate Plugin Auto-Installer & Virtual Environment Service (Idea 2).

Handles 1-Click installation of external plugins from:
1. Uploaded ZIP archive
2. Remote Git repository URL
3. Local template folder

Features:
- Automated ZIP extraction and directory resolution
- Isolated virtualenv creation (`python -m venv .venv`) and pip installation
- Manifest syntax & schema validation
- Automatic database registration and Knowledge Store schema ingestion
- Real-time SSE broadcasting (`plugin_installed`)
"""

import asyncio
import io
import json
import logging
import os
import shutil
import subprocess
import sys
import venv
import zipfile
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from sqlmodel import Session, select
from core.config import settings
from core.database import PluginProfile, utc_now
from core.engine.plugin_linter import PluginLinter
from core.gateway.sse_broadcaster import sse_broadcaster
from core.storage.knowledge_store import KnowledgeStore

logger = logging.getLogger(__name__)


class PluginInstallerError(Exception):
    """Raised when plugin installation fails."""
    pass


class PluginInstaller:
    """Manages the lifecycle of installing, extracting, building, and registering plugins."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.plugins_dir: Path = settings.BASE_DIR / "plugins"
        self.plugins_dir.mkdir(parents=True, exist_ok=True)

    def _find_manifest(self, root_dir: Path) -> Tuple[Path, Dict[str, Any]]:
        """Locate manifest.json directly or in the single top-level directory of extracted archive."""
        direct_manifest = root_dir / "manifest.json"
        if direct_manifest.is_file():
            try:
                with open(direct_manifest, "r", encoding="utf-8") as f:
                    return direct_manifest, json.load(f)
            except Exception as exc:
                raise PluginInstallerError(f"Failed to read manifest.json: {str(exc)}") from exc

        # Check subdirectories
        subdirs = [p for p in root_dir.iterdir() if p.is_dir() and not p.name.startswith(".")]
        if len(subdirs) == 1:
            nested_manifest = subdirs[0] / "manifest.json"
            if nested_manifest.is_file():
                try:
                    with open(nested_manifest, "r", encoding="utf-8") as f:
                        return nested_manifest, json.load(f)
                except Exception as exc:
                    raise PluginInstallerError(f"Failed to read nested manifest.json: {str(exc)}") from exc

        raise PluginInstallerError(f"No valid manifest.json found in {root_dir}")

    def _validate_manifest(self, manifest: Dict[str, Any]) -> None:
        """Validate required manifest schema fields."""
        required_fields = ["id", "name", "driver", "entrypoint"]
        missing = [field for field in required_fields if field not in manifest or not str(manifest[field]).strip()]
        if missing:
            raise PluginInstallerError(f"Manifest missing required field(s): {', '.join(missing)}")

    def setup_isolated_venv(self, plugin_dir: Path) -> str:
        """Create an isolated virtual environment and install requirements.txt if present.

        Returns:
            The resolved python executable path for the plugin.
        """
        requirements_file = plugin_dir / "requirements.txt"
        if not requirements_file.is_file() or requirements_file.stat().st_size == 0:
            return sys.executable
        
        try:
            req_lines = [l.strip() for l in requirements_file.read_text(encoding="utf-8").splitlines() if l.strip() and not l.strip().startswith("#")]
            if not req_lines:
                return sys.executable
        except Exception:
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
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if proc.returncode != 0:
                logger.warning("pip install warning/failure in plugin venv: %s", proc.stderr)
        except Exception as exc:
            logger.warning("Could not set up isolated venv: %s. Falling back to host python.", exc)
            return sys.executable

        return str(python_bin) if python_bin.exists() else sys.executable

    def register_installed_plugin(
        self,
        manifest_file: Path,
        manifest: Dict[str, Any],
        resolved_python_bin: Optional[str] = None,
    ) -> PluginProfile:
        """Save plugin metadata in DB, adjust entrypoint, and ingest knowledge catalog."""
        plugin_id = manifest["id"].strip()
        plugin_dir = manifest_file.parent

        # Adjust entrypoint to absolute path or python bin if needed
        entrypoint = manifest["entrypoint"]
        if resolved_python_bin and entrypoint.startswith("python "):
            # Replace 'python ' with actual venv python path
            script_part = entrypoint[len("python "):].strip()
            script_full_path = (plugin_dir / script_part).resolve()
            entrypoint = f'"{resolved_python_bin}" "{script_full_path}"'
        elif not os.path.isabs(entrypoint.split()[0]):
            parts = entrypoint.split(maxsplit=1)
            first_cmd = parts[0]
            rest = parts[1] if len(parts) > 1 else ""
            if (plugin_dir / first_cmd).exists():
                entrypoint = f'"{str((plugin_dir / first_cmd).resolve())}" {rest}'.strip()

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
            profile.custom_card_json = json.dumps(manifest.get("custom_card", json.loads(profile.custom_card_json or "{}")))
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
                store.ingest_plugin_catalog(
                    target_id=plugin_id,
                    partition_key="Default",
                    title=f"{profile.name} Catalog",
                    catalog=catalog,
                )
            except Exception as exc:
                logger.warning("Failed to auto-ingest catalog for %s: %s", plugin_id, exc)

        return profile

    async def install_from_zip(self, zip_content: bytes, filename: Optional[str] = None) -> PluginProfile:
        """Install a plugin from an uploaded ZIP archive."""
        try:
            zip_file = zipfile.ZipFile(io.BytesIO(zip_content))
        except zipfile.BadZipFile as exc:
            raise PluginInstallerError("Uploaded file is not a valid ZIP archive.") from exc

        # Extract to temporary staging folder inside plugins/
        staging_id = f"staged_plugin_{int(utc_now().timestamp())}"
        staging_dir = self.plugins_dir / staging_id
        staging_dir.mkdir(parents=True, exist_ok=True)

        try:
            zip_file.extractall(staging_dir)
            manifest_file, manifest = self._find_manifest(staging_dir)
            self._validate_manifest(manifest)

            plugin_id = manifest["id"].strip()
            final_target_dir = self.plugins_dir / plugin_id

            # Move from staging to final directory
            source_dir = manifest_file.parent
            if final_target_dir.exists():
                shutil.rmtree(final_target_dir, ignore_errors=True)

            if source_dir != staging_dir:
                shutil.move(str(source_dir), str(final_target_dir))
                shutil.rmtree(staging_dir, ignore_errors=True)
            else:
                shutil.move(str(staging_dir), str(final_target_dir))

            final_manifest_file = final_target_dir / "manifest.json"

            # Setup isolated virtualenv if requirements exist
            resolved_python = self.setup_isolated_venv(final_target_dir)

            # Register in Database
            profile = self.register_installed_plugin(
                manifest_file=final_manifest_file,
                manifest=manifest,
                resolved_python_bin=resolved_python,
            )

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
            except Exception:
                pass

            return profile

        except Exception as exc:
            shutil.rmtree(staging_dir, ignore_errors=True)
            raise PluginInstallerError(f"Failed to install plugin from ZIP: {str(exc)}") from exc

    async def install_from_git(
        self,
        git_url: str,
        branch: Optional[str] = None,
        plugin_id_override: Optional[str] = None,
    ) -> PluginProfile:
        """Clone and install a plugin from a remote Git repository."""
        staging_id = f"git_plugin_{int(utc_now().timestamp())}"
        staging_dir = self.plugins_dir / staging_id

        # Execute git clone
        cmd = ["git", "clone", "--depth", "1"]
        if branch:
            cmd.extend(["--branch", branch])
        cmd.extend([git_url, str(staging_dir)])

        try:
            logger.info("Cloning Git repository: %s", " ".join(cmd))
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if proc.returncode != 0:
                raise PluginInstallerError(f"git clone failed: {proc.stderr}")

            manifest_file, manifest = self._find_manifest(staging_dir)
            if plugin_id_override:
                manifest["id"] = plugin_id_override

            self._validate_manifest(manifest)
            plugin_id = manifest["id"].strip()
            final_target_dir = self.plugins_dir / plugin_id

            source_dir = manifest_file.parent
            if final_target_dir.exists():
                shutil.rmtree(final_target_dir, ignore_errors=True)

            if source_dir != staging_dir:
                shutil.move(str(source_dir), str(final_target_dir))
                shutil.rmtree(staging_dir, ignore_errors=True)
            else:
                shutil.move(str(staging_dir), str(final_target_dir))

            final_manifest_file = final_target_dir / "manifest.json"

            # Setup isolated virtualenv if requirements exist
            resolved_python = self.setup_isolated_venv(final_target_dir)

            # Register in Database
            profile = self.register_installed_plugin(
                manifest_file=final_manifest_file,
                manifest=manifest,
                resolved_python_bin=resolved_python,
            )

            # Run Certification Linter automatically
            try:
                linter = PluginLinter(self.session)
                await linter.verify_plugin(plugin_id)
                self.session.refresh(profile)
            except Exception as lint_exc:
                logger.warning("Sanity linter warning on git install %s: %s", plugin_id, lint_exc)

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
            except Exception:
                pass

            return profile

        except Exception as exc:
            shutil.rmtree(staging_dir, ignore_errors=True)
            raise PluginInstallerError(f"Failed to install plugin from Git: {str(exc)}") from exc
