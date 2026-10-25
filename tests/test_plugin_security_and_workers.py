"""Installer hardening (Zip Slip, path/rmtree, git URL, entrypoint, requirements) and
persistent plugin workers (reuse, restart, abort while a call is in flight). No database needed."""

import asyncio
import io
import json
import stat
import time
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlmodel import Session, SQLModel, create_engine

from core.config import settings
from core.database import PluginProfile
from core.engine import plugin_client
from core.engine.plugin_client import PluginSubprocessClient, terminate_all_subprocesses
from core.engine.plugin_installer import PluginInstaller, PluginInstallerError
from core.engine.state_machine import ExecutionStateMachine
from core.exceptions import JsonRpcProtocolError, PluginProcessError
from plugins.plugin_contract import AbortParams, ExecuteParams

SIM_ENTRY = "python plugins/sqlserver_plugin/adapter.py --serve"
SIM_CFG = {"use_simulation": "true"}


@pytest.fixture(name="env")
def fixture_env(tmp_path: Path, monkeypatch):
    """Installer sandbox: BASE_DIR points to tmp, so nothing touches the real plugins/ folder."""
    monkeypatch.setattr(settings, "BASE_DIR", tmp_path)
    engine = create_engine(f"sqlite:///{tmp_path / 'sec.db'}", connect_args={"check_same_thread": False})
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield PluginInstaller(session), tmp_path


def _manifest(plugin_id: str = "good_plugin", entrypoint: str = "python adapter.py") -> dict:
    return {"id": plugin_id, "name": "T", "driver": "x", "entrypoint": entrypoint, "config": {}}


def _zip(files: dict[str, str | bytes], extra: list[zipfile.ZipInfo] | None = None) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in files.items():
            zf.writestr(name, content)
        for info in extra or []:
            zf.writestr(info, "x")
    return buf.getvalue()


def _good_files(**override) -> dict[str, str]:
    files = {"manifest.json": json.dumps(_manifest()), "adapter.py": "print('hi')\n"}
    files.update(override)
    return files


class TestZipHardening:
    @pytest.mark.parametrize("name", ["../evil.txt", "a/../../evil.txt", "/abs/evil.txt", "C:/evil.txt", "..\\evil.txt", "ok.txt:stream"])
    async def test_unsafe_zip_paths_rejected(self, env, name: str) -> None:
        installer, base = env
        data = _zip(_good_files(), extra=[zipfile.ZipInfo(name)])
        with pytest.raises(PluginInstallerError):
            await installer.install_from_zip(data)
        assert not (base / "evil.txt").exists() and not (base.parent / "evil.txt").exists()
        assert not list((base / "plugins").glob("*good_plugin*"))

    async def test_symlink_in_zip_rejected(self, env) -> None:
        installer, _ = env
        link = zipfile.ZipInfo("link")
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        with pytest.raises(PluginInstallerError, match="Symbolic"):
            await installer.install_from_zip(_zip(_good_files(), extra=[link]))

    async def test_zip_bomb_limits(self, env, monkeypatch) -> None:
        installer, _ = env
        monkeypatch.setattr(settings, "PLUGIN_MAX_UNZIPPED_BYTES", 100)
        with pytest.raises(PluginInstallerError, match="allowed size"):
            await installer.install_from_zip(_zip(_good_files(**{"big.bin": "A" * 5000})))
        monkeypatch.setattr(settings, "PLUGIN_MAX_ZIP_BYTES", 10)
        with pytest.raises(PluginInstallerError, match="larger"):
            await installer.install_from_zip(_zip(_good_files()))

    async def test_staging_is_cleaned_after_failure(self, env) -> None:
        installer, base = env
        with pytest.raises(PluginInstallerError):
            await installer.install_from_zip(_zip({"readme.txt": "no manifest"}))
        assert not [p for p in (base / "plugins").iterdir() if p.name.startswith(".")]


class TestPluginIdAndOverwrite:
    @pytest.mark.parametrize("bad_id", ["../victim", "..", "a/b", "A_Upper", "x" * 80, "", "templates", "c:\\x", "a b"])
    async def test_malicious_plugin_id_never_touches_other_dirs(self, env, bad_id: str) -> None:
        installer, base = env
        victim = base / "victim"
        victim.mkdir()
        (victim / "precious.txt").write_text("keep")
        data = _zip({"manifest.json": json.dumps(_manifest(bad_id)), "adapter.py": "x=1\n"})
        with pytest.raises(PluginInstallerError):
            await installer.install_from_zip(data)
        assert (victim / "precious.txt").read_text() == "keep"

    async def test_refuses_to_replace_a_non_plugin_directory(self, env) -> None:
        installer, base = env
        target = base / "plugins" / "good_plugin"
        target.mkdir(parents=True)
        (target / "user_data.txt").write_text("mine")
        with pytest.raises(PluginInstallerError, match="not a plugin directory"):
            await installer.install_from_zip(_zip(_good_files()))
        assert (target / "user_data.txt").read_text() == "mine"

    async def test_failed_replace_restores_previous_version(self, env) -> None:
        installer, base = env
        await installer.install_from_zip(_zip(_good_files(**{"adapter.py": "VERSION = 1\n"})))
        assert "VERSION = 1" in (base / "plugins" / "good_plugin" / "adapter.py").read_text()

        with patch.object(installer, "register_installed_plugin", side_effect=RuntimeError("db down")):
            with pytest.raises(PluginInstallerError):
                await installer.install_from_zip(_zip(_good_files(**{"adapter.py": "VERSION = 2\n"})))
        assert "VERSION = 1" in (base / "plugins" / "good_plugin" / "adapter.py").read_text()
        assert not [p for p in (base / "plugins").iterdir() if p.name.startswith(".replaced_")]

    async def test_successful_replace_removes_backup(self, env) -> None:
        installer, base = env
        await installer.install_from_zip(_zip(_good_files(**{"adapter.py": "VERSION = 1\n"})))
        await installer.install_from_zip(_zip(_good_files(**{"adapter.py": "VERSION = 2\n"})))
        assert "VERSION = 2" in (base / "plugins" / "good_plugin" / "adapter.py").read_text()
        assert not [p for p in (base / "plugins").iterdir() if p.name.startswith(".")]


class TestEntrypointAndRequirements:
    @pytest.mark.parametrize(
        "entry",
        [
            "python adapter.py & calc",
            "python adapter.py | more",
            "python adapter.py; rm -rf /",
            "python adapter.py > out.txt",
            "python -c print(1)",
            "python -m http.server",
            "python ../outside.py",
            "python /etc/passwd.py",
            "python C:/x.py",
            "cmd /c adapter.py",
            "python adapter.py $(id)",
            "python adapter.py --flag=`id`",
            "python missing.py",
            "python adapter.txt",
            "adapter.py",
            "python",
        ],
    )
    async def test_dangerous_entrypoints_rejected(self, env, entry: str) -> None:
        installer, _ = env
        data = _zip(_good_files(**{"manifest.json": json.dumps(_manifest(entrypoint=entry)), "adapter.txt": "x"}))
        with pytest.raises(PluginInstallerError):
            await installer.install_from_zip(data)

    async def test_serve_flag_is_kept_and_script_made_absolute(self, env) -> None:
        installer, base = env
        files = _good_files(**{"manifest.json": json.dumps(_manifest(entrypoint="python adapter.py --serve"))})
        profile = await installer.install_from_zip(_zip(files))
        assert profile.entrypoint.endswith("--serve")
        assert str((base / "plugins" / "good_plugin" / "adapter.py").resolve()) in profile.entrypoint

    @pytest.mark.parametrize(
        "req",
        ["--index-url http://evil/simple\nrequests", "-r other.txt", "pkg @ https://evil/x.whl", "git+https://x/y.git", "./local_dir", "https://evil/x.tar.gz", "pkg --install-option=x"],
    )
    async def test_dangerous_requirements_rejected(self, env, req: str) -> None:
        installer, _ = env
        with pytest.raises(PluginInstallerError, match="requirements"):
            await installer.install_from_zip(_zip(_good_files(**{"requirements.txt": req})))

    def test_plain_requirements_accepted(self, tmp_path: Path) -> None:
        f = tmp_path / "requirements.txt"
        f.write_text("# comment\nrequests>=2.0,<3\npydantic[email]==2.5.0\nfoo ; python_version < '3.12'\n\n")
        PluginInstaller._validate_requirements(f)


class TestGitHardening:
    @pytest.mark.parametrize(
        "url",
        [
            "--upload-pack=calc",
            "-c core.sshCommand=calc",
            "ext::sh -c id",
            "http://github.com/o/r",
            "git://github.com/o/r",
            "ssh://git@github.com/o/r",
            "file:///etc",
            "/local/path",
            "https://evil.example/o/r",
            "https://user:pw@github.com/o/r",
            "https://github.com:8443/o/r",
            "https://github.com/o/r evil",
            "",
        ],
    )
    async def test_bad_git_urls_rejected_before_any_process_runs(self, env, url: str) -> None:
        installer, _ = env
        with patch("core.engine.plugin_installer.subprocess.run") as run:
            with pytest.raises(PluginInstallerError):
                await installer.install_from_git(url)
            run.assert_not_called()

    @pytest.mark.parametrize("branch", ["--evil", "-x", "a..b", "bad branch", "a;b"])
    async def test_bad_branch_rejected(self, env, branch: str) -> None:
        installer, _ = env
        with patch("core.engine.plugin_installer.subprocess.run") as run:
            with pytest.raises(PluginInstallerError):
                await installer.install_from_git("https://github.com/o/r", branch=branch)
            run.assert_not_called()

    async def test_clone_command_is_locked_down(self, env) -> None:
        installer, _ = env
        captured: dict = {}

        def fake_run(cmd, **kwargs):
            captured["cmd"], captured["env"] = cmd, kwargs["env"]
            return type("P", (), {"returncode": 1, "stderr": "boom", "stdout": ""})()

        with patch("core.engine.plugin_installer.subprocess.run", side_effect=fake_run):
            with pytest.raises(PluginInstallerError, match="git clone failed"):
                await installer.install_from_git("https://github.com/o/r", branch="main")
        cmd = captured["cmd"]
        assert "--" in cmd and cmd.index("--") < cmd.index("https://github.com/o/r")
        assert "protocol.allow=never" in cmd and "protocol.https.allow=always" in cmd
        assert captured["env"]["GIT_TERMINAL_PROMPT"] == "0"

    async def test_allowed_hosts_are_configurable(self, env, monkeypatch) -> None:
        installer, _ = env
        monkeypatch.setattr(settings, "PLUGIN_GIT_ALLOWED_HOSTS", ["git.mycorp.local"])
        assert installer._validate_git_url("https://git.mycorp.local/team/plugin.git")
        with pytest.raises(PluginInstallerError):
            installer._validate_git_url("https://github.com/o/r")


# ---------------------------------------------------------------- persistent workers


@pytest.fixture(name="workers")
async def fixture_workers():
    yield
    await terminate_all_subprocesses()


def _sim_client(plugin_id: str, config: dict | None = None) -> PluginSubprocessClient:
    return PluginSubprocessClient(SIM_ENTRY, plugin_id=plugin_id, config=SIM_CFG if config is None else config)


class TestPersistentWorker:
    async def test_one_process_is_reused_across_calls(self, workers) -> None:
        c = _sim_client("w_reuse")
        await c.send_rpc_command("ping", {})
        pid1 = plugin_client._workers["w_reuse"].proc.pid
        await c.execute(ExecuteParams(execution_id="r1", query="SELECT 1 FROM Orders WHERE OrderID = 1"))
        await c.send_rpc_command("ping", {})
        assert plugin_client._workers["w_reuse"].proc.pid == pid1

    async def test_unconfigured_worker_refuses_instead_of_faking(self, workers) -> None:
        c = PluginSubprocessClient(SIM_ENTRY, plugin_id="w_bare")
        with pytest.raises(JsonRpcProtocolError, match="not configured"):
            await c.send_rpc_command("ping", {})

    async def test_worker_restarts_after_crash_and_gets_config_again(self, workers) -> None:
        c = _sim_client("w_crash")
        await c.send_rpc_command("ping", {})
        old = plugin_client._workers["w_crash"].proc
        old.kill()
        await old.wait()
        res = await c.send_rpc_command("ping", {})  # would raise "not configured" if config were not re-pushed
        assert res["status"] == "ok" and plugin_client._workers["w_crash"].proc.pid != old.pid

    async def test_config_change_is_pushed_to_running_worker(self, workers) -> None:
        c = _sim_client("w_cfg")
        assert (await c.send_rpc_command("ping", {}))["mode"] == "simulation"
        c2 = _sim_client("w_cfg", {"use_simulation": "false", "server": "", "database": "x"})
        with pytest.raises(JsonRpcProtocolError):  # now "real" mode: no server -> clear config error, not fake data
            await c2.send_rpc_command("ping", {})

    async def test_concurrent_executions_do_not_block_each_other(self, workers) -> None:
        c = _sim_client("w_conc")
        started = time.monotonic()
        results = await asyncio.gather(
            *[c.execute(ExecuteParams(execution_id=f"c{i}", query="SELECT 1 FROM Orders WHERE OrderID = 1")) for i in range(5)]
        )
        assert len(results) == 5 and time.monotonic() - started < 5

    async def test_abort_interrupts_a_call_that_is_still_running(self, workers) -> None:
        c = _sim_client("w_abort")
        running = asyncio.create_task(
            c.execute(ExecuteParams(execution_id="slow1", query="WAITFOR DELAY '00:00:30'", timeout_seconds=20))
        )
        await asyncio.sleep(0.6)
        started = time.monotonic()
        res = await c.abort(AbortParams(execution_id="slow1"))
        assert res.success and "KILL" in res.message
        with pytest.raises(JsonRpcProtocolError, match="aborted"):
            await running
        assert time.monotonic() - started < 3

    async def test_client_side_timeout_keeps_the_worker_alive_so_abort_still_works(self, workers) -> None:
        c = _sim_client("w_keep")
        with pytest.raises(PluginProcessError, match="timed out"):
            await c.execute(ExecuteParams(execution_id="slow2", query="WAITFOR DELAY '00:00:30'", timeout_seconds=20), timeout=0.4)
        res = await c.abort(AbortParams(execution_id="slow2"))
        assert res.success and "KILL" in res.message  # session was still found in the live worker


class TestStateMachineWithWorkers:
    @pytest.fixture(name="sm")
    async def fixture_sm(self, tmp_path: Path):
        engine = create_engine(f"sqlite:///{tmp_path / 'sm.db'}", connect_args={"check_same_thread": False})
        SQLModel.metadata.create_all(engine)
        with Session(engine) as s:
            s.add(PluginProfile(id="sim_t", name="S", driver="x", entrypoint=SIM_ENTRY, config_json=json.dumps(SIM_CFG), status="active"))
            s.commit()
            sm = ExecutionStateMachine(s)
            sm.setting_store.set_auto_approval(True)
            yield sm
        await terminate_all_subprocesses()

    async def test_manual_stop_wins_over_the_late_error(self, sm) -> None:
        run = asyncio.create_task(sm.initiate_execution("sim_t", "WAITFOR DELAY '00:00:30'", execution_id="stop1"))
        await asyncio.sleep(1.0)
        stopped = await sm.abort_execution("stop1")
        assert stopped.status == "ABORTED"
        final = await asyncio.wait_for(run, timeout=5)
        assert final.status == "ABORTED"

    async def test_timeout_guard_aborts_and_reports_timeout(self, sm, monkeypatch) -> None:
        monkeypatch.setattr(settings, "READ_TIMEOUT_SECONDS", 1.0)
        started = time.monotonic()
        log = await sm.initiate_execution("sim_t", "WAITFOR DELAY '00:00:30'", execution_id="to1")
        assert log.status == "TIMEOUT" and time.monotonic() - started < 6
        assert "abort FAILED" not in (log.error_message or "")

    async def test_cannot_abort_a_finished_execution(self, sm) -> None:
        log = await sm.initiate_execution("sim_t", "SELECT 1 FROM Orders WHERE OrderID = 1", execution_id="done1")
        assert log.status == "COMPLETED"
        from core.exceptions import ExecutionStateError

        with pytest.raises(ExecutionStateError, match="already finished"):
            await sm.abort_execution("done1")
