"""JSON-RPC over Stdio Subprocess Client for AegisGate Plugins.

Adheres strictly to python_clean_code.md:
- Subprocess wrapped in try...finally to prevent orphan processes
- Full async/await and asyncio subprocess management
- Custom exception handling
- 100% Type Hints
"""

import asyncio
import contextlib
import json
import logging
import os
import shlex
import sys
from typing import Any

from core.config import settings
from core.exceptions import JsonRpcProtocolError, PluginProcessError
from plugins.plugin_contract import (
    AbortParams,
    AbortResult,
    DryRunParams,
    DryRunResult,
    ExecuteParams,
    ExecuteResult,
    JsonRpcRequest,
    JsonRpcResponse,
    ReinitParams,
    ReinitResult,
    SyncKnowledgeParams,
    SyncKnowledgeResult,
)

logger = logging.getLogger(__name__)

# Active background subprocess tracker across all plugin client executions
_active_processes: set[asyncio.subprocess.Process] = set()


def _split_command(cmd: str) -> list[str]:
    """Split an entrypoint into argv (quotes removed) so it can run without a shell."""
    is_windows = sys.platform.startswith("win")
    parts = shlex.split(cmd, posix=not is_windows)
    return [p[1:-1] if len(p) >= 2 and p[0] == p[-1] and p[0] in ("'", '"') else p for p in parts]


class _PersistentWorker:
    """One long-lived plugin process shared by every call for a plugin.

    Newline-delimited JSON-RPC over stdio, multiplexed by request id, so a slow ``execute``
    and a concurrent ``abort`` travel through the *same* live process. That is what lets the
    plugin keep connections / SPIDs in memory and actually kill a running query.
    """

    def __init__(self, cmd: str, working_dir: str) -> None:
        self.cmd = cmd
        self.working_dir = working_dir
        self.config: dict[str, Any] | None = None
        self.loop: asyncio.AbstractEventLoop = asyncio.get_running_loop()
        self.proc: asyncio.subprocess.Process | None = None
        self._pending: dict[int, asyncio.Future[dict[str, Any]]] = {}
        self._next_id = 0
        self._start_lock = asyncio.Lock()
        self._tasks: list[asyncio.Task[None]] = []

    @property
    def alive(self) -> bool:
        return self.proc is not None and self.proc.returncode is None

    async def _spawn(self) -> None:
        sub_env = os.environ.copy()
        sub_env["PYTHONPATH"] = str(settings.BASE_DIR)
        sub_env["PYTHONUNBUFFERED"] = "1"
        kwargs: dict[str, Any] = {
            "stdin": asyncio.subprocess.PIPE,
            "stdout": asyncio.subprocess.PIPE,
            "stderr": asyncio.subprocess.PIPE,
            "cwd": self.working_dir,
            "env": sub_env,
            "limit": settings.PLUGIN_MAX_MESSAGE_BYTES,
        }
        try:
            argv = _split_command(self.cmd)
            self.proc = await asyncio.create_subprocess_exec(*argv, **kwargs)
        except (ValueError, OSError):
            logger.debug("Falling back to shell launch for %s", self.cmd)
            self.proc = await asyncio.create_subprocess_shell(self.cmd, **kwargs)
        _active_processes.add(self.proc)
        self._tasks = [
            asyncio.create_task(self._read_loop(self.proc)),
            asyncio.create_task(self._drain_stderr(self.proc)),
        ]
        logger.info("Started persistent plugin worker pid=%s: %s", self.proc.pid, self.cmd)

    async def _read_loop(self, proc: asyncio.subprocess.Process) -> None:
        assert proc.stdout is not None
        try:
            while True:
                line = await proc.stdout.readline()
                if not line:
                    break
                text = line.decode("utf-8", errors="replace").strip()
                if not text.startswith("{"):
                    logger.debug("plugin stdout noise: %s", text[:200])
                    continue
                try:
                    data = json.loads(text)
                except json.JSONDecodeError:
                    continue
                fut = self._pending.get(data.get("id"))
                if fut is not None and not fut.done():
                    fut.set_result(data)
        except ValueError as exc:  # message exceeded the stream limit; the stream is unusable
            logger.error("Plugin message too large, killing worker: %s", exc)
            proc.kill()
        finally:
            self._fail_pending(PluginProcessError("Plugin worker process exited"))

    async def _drain_stderr(self, proc: asyncio.subprocess.Process) -> None:
        assert proc.stderr is not None
        try:
            while True:
                line = await proc.stderr.readline()
                if not line:
                    break
                logger.debug("plugin stderr: %s", line.decode("utf-8", errors="replace").rstrip()[:500])
        except ValueError:
            pass

    def _fail_pending(self, exc: Exception) -> None:
        for fut in list(self._pending.values()):
            if not fut.done():
                fut.set_exception(exc)

    async def _raw_call(self, method: str, params: dict[str, Any], timeout: float | None) -> dict[str, Any]:
        assert self.proc is not None and self.proc.stdin is not None
        self._next_id += 1
        rid = self._next_id
        fut: asyncio.Future[dict[str, Any]] = self.loop.create_future()
        self._pending[rid] = fut
        payload = json.dumps({"jsonrpc": "2.0", "method": method, "params": params, "id": rid}, default=str) + "\n"
        try:
            self.proc.stdin.write(payload.encode("utf-8"))
            await self.proc.stdin.drain()
            return await (asyncio.wait_for(fut, timeout) if timeout else fut)
        except (BrokenPipeError, ConnectionResetError) as exc:
            raise PluginProcessError("Plugin worker pipe is closed") from exc
        except TimeoutError as exc:
            # The worker is deliberately NOT killed: a slow call must stay abortable.
            raise PluginProcessError(f"Plugin call '{method}' timed out after {timeout}s") from exc
        finally:
            self._pending.pop(rid, None)

    async def ensure_ready(self, config: dict[str, Any] | None) -> None:
        """Start the process if needed and make sure it holds the current configuration."""
        async with self._start_lock:
            if not self.alive:
                self.config = None
                await self._spawn()
            if config is not None and config != self.config:
                resp = await self._raw_call("reinit", {"config": config}, timeout=20.0)
                if resp.get("error"):
                    logger.warning("Plugin reinit reported: %s", resp["error"])
                self.config = config

    async def call(self, method: str, params: dict[str, Any], timeout: float | None) -> dict[str, Any]:
        return await self._raw_call(method, params, timeout)

    async def close(self) -> bool:
        """Ask the worker to stop (EOF on stdin), then kill it. Returns True if it was running."""
        proc = self.proc
        was_running = proc is not None and proc.returncode is None
        if proc is not None and proc.returncode is None:
            try:
                if proc.stdin is not None:
                    proc.stdin.close()
                await asyncio.wait_for(proc.wait(), timeout=2.0)
            except Exception:
                try:
                    proc.kill()
                    await asyncio.wait_for(proc.wait(), timeout=2.0)
                except Exception as exc:
                    logger.warning("Error killing plugin worker: %s", exc)
        if proc is not None:
            _active_processes.discard(proc)
        for task in self._tasks:
            task.cancel()
        self._fail_pending(PluginProcessError("Plugin worker closed"))
        return was_running


# Live persistent workers keyed by plugin id (or entrypoint when no id is given)
_workers: dict[str, _PersistentWorker] = {}


async def _get_worker(key: str, cmd: str, working_dir: str) -> _PersistentWorker:
    worker = _workers.get(key)
    loop = asyncio.get_running_loop()
    if worker is not None and (worker.loop is not loop or worker.cmd != cmd):
        # Different event loop (tests) or the entrypoint changed: retire the old process.
        if worker.loop is loop:
            await worker.close()
        elif worker.proc is not None and worker.proc.returncode is None:
            with contextlib.suppress(ProcessLookupError):
                worker.proc.kill()
        worker = None
    if worker is None:
        worker = _PersistentWorker(cmd, working_dir)
        _workers[key] = worker
    return worker


async def terminate_all_subprocesses() -> int:
    """Forcefully terminate and wait for any active plugin child processes."""
    killed_count = 0
    for key, worker in list(_workers.items()):
        try:
            if worker.loop is asyncio.get_running_loop():
                killed_count += 1 if await worker.close() else 0
            elif worker.proc is not None and worker.proc.returncode is None:
                worker.proc.kill()
                killed_count += 1
        except Exception as exc:
            logger.warning("Error closing plugin worker %s: %s", key, exc)
        finally:
            _workers.pop(key, None)

    for proc in list(_active_processes):
        if proc.returncode is None:
            try:
                proc.kill()
                await asyncio.wait_for(proc.wait(), timeout=1.0)
                killed_count += 1
            except Exception as exc:
                logger.warning("Error killing plugin subprocess: %s", exc)
            finally:
                _active_processes.discard(proc)
    return killed_count


class PluginSubprocessClient:
    """Communicates with an isolated plugin child process using JSON-RPC over stdin/stdout."""

    def __init__(
        self,
        entrypoint_cmd: str,
        working_dir: str | None = None,
        plugin_id: str | None = None,
        config: dict[str, Any] | None = None,
    ) -> None:
        self.entrypoint_cmd: str = entrypoint_cmd
        self.working_dir: str | None = working_dir
        self.plugin_id: str | None = plugin_id
        self.config: dict[str, Any] | None = config
        self._request_counter: int = 0

    @property
    def persistent(self) -> bool:
        """Entrypoints containing ``--serve`` run as one long-lived worker (abortable, keeps state)."""
        return "--serve" in self.entrypoint_cmd.split()

    async def _send_persistent(self, method: str, params: dict[str, Any], timeout: float | None) -> Any:
        worker = await _get_worker(
            self.plugin_id or self.entrypoint_cmd,
            self.entrypoint_cmd,
            self.working_dir or str(settings.BASE_DIR),
        )
        if method == "reinit":
            # Configuration is pushed explicitly; remember it so a restarted worker gets it again.
            await worker.ensure_ready(None)
            data = await worker.call("reinit", params, timeout)
            self.config = params.get("config", self.config)
            worker.config = self.config
        else:
            await worker.ensure_ready(self.config)
            data = await worker.call(method, params, timeout)

        try:
            rpc_resp = JsonRpcResponse.model_validate(data)
        except Exception as parse_err:
            raise JsonRpcProtocolError(f"Invalid JSON-RPC format: {parse_err}") from parse_err
        if rpc_resp.error:
            raise JsonRpcProtocolError(
                f"Plugin RPC Error [{rpc_resp.error.code}]: {rpc_resp.error.message}",
                details={"data": rpc_resp.error.data},
            )
        return rpc_resp.result

    def _next_id(self) -> int:
        self._request_counter += 1
        return self._request_counter

    async def send_rpc_command(
        self,
        method: str,
        params: dict[str, Any],
        timeout: float | None = None,
    ) -> Any:
        """Execute a single JSON-RPC roundtrip with the plugin process.

        Guarantees process termination via try...finally to eliminate orphan processes.
        """
        if self.persistent:
            return await self._send_persistent(method, params, timeout)

        request_id = self._next_id()
        rpc_req = JsonRpcRequest(method=method, params=params, id=request_id)
        payload = rpc_req.model_dump_json() + "\n"

        proc: asyncio.subprocess.Process | None = None
        try:
            logger.debug("Launching plugin subprocess: %s", self.entrypoint_cmd)
            sub_env = os.environ.copy()
            sub_env["PYTHONPATH"] = str(settings.BASE_DIR)

            proc = await asyncio.create_subprocess_shell(
                self.entrypoint_cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.working_dir or str(settings.BASE_DIR),
                env=sub_env,
            )
            _active_processes.add(proc)

            # Write request to stdin
            if proc.stdin is None or proc.stdout is None:
                raise PluginProcessError("Failed to open stdin/stdout pipes to plugin")

            proc.stdin.write(payload.encode("utf-8"))
            await proc.stdin.drain()
            proc.stdin.close()
            await proc.stdin.wait_closed()

            # Read response with optional timeout
            async def _read_response() -> str:
                stdout_data, stderr_data = await proc.communicate()
                if proc.returncode != 0 and not stdout_data:
                    err_msg = stderr_data.decode("utf-8", errors="replace").strip()
                    raise PluginProcessError(f"Plugin exited with code {proc.returncode}: {err_msg}")
                return stdout_data.decode("utf-8", errors="replace").strip()

            if timeout:
                raw_response = await asyncio.wait_for(_read_response(), timeout=timeout)
            else:
                raw_response = await _read_response()

            if not raw_response:
                raise PluginProcessError("Plugin returned empty response over stdout")

            # Parse JSON-RPC line (take the last valid JSON line in case of debug logs)
            json_line: str | None = None
            for line in reversed(raw_response.splitlines()):
                line = line.strip()
                if line.startswith("{") and line.endswith("}"):
                    json_line = line
                    break

            if not json_line:
                raise JsonRpcProtocolError(f"No valid JSON found in plugin output: {raw_response[:200]}")

            try:
                data = json.loads(json_line)
                rpc_resp = JsonRpcResponse.model_validate(data)
            except Exception as parse_err:
                raise JsonRpcProtocolError(f"Invalid JSON-RPC format: {parse_err}") from parse_err

            if rpc_resp.error:
                raise JsonRpcProtocolError(
                    f"Plugin RPC Error [{rpc_resp.error.code}]: {rpc_resp.error.message}",
                    details={"data": rpc_resp.error.data},
                )

            return rpc_resp.result

        except TimeoutError as exc:
            raise PluginProcessError(f"Plugin execution timed out after {timeout}s") from exc

        finally:
            if proc is not None:
                _active_processes.discard(proc)
            # Guarantee child process cleanup
            if proc is not None and proc.returncode is None:
                try:
                    proc.kill()
                    await proc.wait()
                    logger.debug("Successfully terminated plugin subprocess")
                except ProcessLookupError:
                    pass
                except Exception as cleanup_err:
                    logger.warning("Error terminating plugin process: %s", cleanup_err)

    async def sync_knowledge(self, params: SyncKnowledgeParams) -> SyncKnowledgeResult:
        """Call plugin sync_knowledge method."""
        raw = await self.send_rpc_command("sync_knowledge", params.model_dump(mode="json"), timeout=30.0)
        return SyncKnowledgeResult.model_validate(raw)

    async def dry_run(self, params: DryRunParams) -> DryRunResult:
        """Call plugin dry_run method."""
        raw = await self.send_rpc_command("dry_run", params.model_dump(mode="json"), timeout=15.0)
        return DryRunResult.model_validate(raw)

    async def execute(self, params: ExecuteParams, timeout: float | None = None) -> ExecuteResult:
        """Call plugin execute method."""
        call_timeout = timeout or params.timeout_seconds + 5.0
        raw = await self.send_rpc_command("execute", params.model_dump(mode="json"), timeout=call_timeout)
        return ExecuteResult.model_validate(raw)

    async def abort(self, params: AbortParams) -> AbortResult:
        """Call plugin abort method."""
        raw = await self.send_rpc_command("abort", params.model_dump(mode="json"), timeout=10.0)
        return AbortResult.model_validate(raw)

    async def reinit(self, params: ReinitParams, timeout: float | None = None) -> ReinitResult:
        """Call plugin reinit method with updated configuration."""
        raw = await self.send_rpc_command("reinit", params.model_dump(), timeout=timeout or 10.0)
        return ReinitResult.model_validate(raw)
