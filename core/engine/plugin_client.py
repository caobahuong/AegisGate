"""JSON-RPC over Stdio Subprocess Client for AegisGate Plugins.

Adheres strictly to python_clean_code.md:
- Subprocess wrapped in try...finally to prevent orphan processes
- Full async/await and asyncio subprocess management
- Custom exception handling
- 100% Type Hints
"""

import asyncio
import json
import logging
import os
from typing import Any, Optional
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


async def terminate_all_subprocesses() -> int:
    """Forcefully terminate and wait for any active plugin child processes."""
    killed_count = 0
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

    def __init__(self, entrypoint_cmd: str, working_dir: Optional[str] = None) -> None:
        self.entrypoint_cmd: str = entrypoint_cmd
        self.working_dir: Optional[str] = working_dir
        self._request_counter: int = 0

    def _next_id(self) -> int:
        self._request_counter += 1
        return self._request_counter

    async def send_rpc_command(
        self,
        method: str,
        params: dict[str, Any],
        timeout: Optional[float] = None,
    ) -> Any:
        """Execute a single JSON-RPC roundtrip with the plugin process.
        
        Guarantees process termination via try...finally to eliminate orphan processes.
        """
        request_id = self._next_id()
        rpc_req = JsonRpcRequest(method=method, params=params, id=request_id)
        payload = rpc_req.model_dump_json() + "\n"

        proc: Optional[asyncio.subprocess.Process] = None
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
                    raise PluginProcessError(
                        f"Plugin exited with code {proc.returncode}: {err_msg}"
                    )
                return stdout_data.decode("utf-8", errors="replace").strip()

            if timeout:
                raw_response = await asyncio.wait_for(_read_response(), timeout=timeout)
            else:
                raw_response = await _read_response()

            if not raw_response:
                raise PluginProcessError("Plugin returned empty response over stdout")

            # Parse JSON-RPC line (take the last valid JSON line in case of debug logs)
            json_line: Optional[str] = None
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

        except asyncio.TimeoutError as exc:
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
        raw = await self.send_rpc_command("sync_knowledge", params.model_dump(), timeout=30.0)
        return SyncKnowledgeResult.model_validate(raw)

    async def dry_run(self, params: DryRunParams) -> DryRunResult:
        """Call plugin dry_run method."""
        raw = await self.send_rpc_command("dry_run", params.model_dump(), timeout=15.0)
        return DryRunResult.model_validate(raw)

    async def execute(self, params: ExecuteParams, timeout: Optional[float] = None) -> ExecuteResult:
        """Call plugin execute method."""
        call_timeout = timeout or params.timeout_seconds + 5.0
        raw = await self.send_rpc_command("execute", params.model_dump(), timeout=call_timeout)
        return ExecuteResult.model_validate(raw)

    async def abort(self, params: AbortParams) -> AbortResult:
        """Call plugin abort method."""
        raw = await self.send_rpc_command("abort", params.model_dump(), timeout=10.0)
        return AbortResult.model_validate(raw)

    async def reinit(self, params: ReinitParams, timeout: Optional[float] = None) -> ReinitResult:
        """Call plugin reinit method with updated configuration."""
        raw = await self.send_rpc_command("reinit", params.model_dump(), timeout=timeout or 10.0)
        return ReinitResult.model_validate(raw)
