"""AegisGate Plugin SDK - JSON-RPC 2.0 Stdio Server.

Listens to newline-delimited JSON-RPC requests on stdin, dispatches to
BasePlugin implementation, and writes responses to stdout.
"""

import json
import logging
import sys
from typing import Any, TextIO

from .base import BasePlugin
from .models import PluginException

logger = logging.getLogger("aegisgate_sdk.server")


class PluginServer:
    """Production-grade JSON-RPC 2.0 Stdio server for AegisGate database plugins."""

    def __init__(
        self,
        plugin: BasePlugin,
        stdin_stream: TextIO | None = None,
        stdout_stream: TextIO | None = None,
    ) -> None:
        self.plugin = plugin
        self.stdin = stdin_stream if stdin_stream is not None else sys.stdin
        self.stdout = stdout_stream if stdout_stream is not None else sys.stdout

    def handle_request(self, raw_line: str) -> str | None:
        """Parse a single JSON-RPC line, execute the method, and format response string."""
        line = raw_line.strip()
        if not line:
            return None

        req_id: Any | None = None
        try:
            req = json.loads(line)
        except json.JSONDecodeError as exc:
            return json.dumps(
                {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": f"Parse error: {exc!s}"}}
            )

        if not isinstance(req, dict) or req.get("jsonrpc") != "2.0" or "method" not in req:
            return json.dumps(
                {
                    "jsonrpc": "2.0",
                    "id": req.get("id") if isinstance(req, dict) else None,
                    "error": {"code": -32600, "message": "Invalid Request: must be JSON-RPC 2.0 object"},
                }
            )

        req_id = req.get("id")
        method = str(req.get("method") or "")
        params = req.get("params") or {}
        if not isinstance(params, dict):
            params = {}

        try:
            result = self._dispatch(method, params)
            response: dict[str, Any] = {"jsonrpc": "2.0", "id": req_id, "result": result}
        except PluginException as exc:
            response = {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "data": exc.data,
                },
            }
        except Exception as exc:
            logger.exception("Internal plugin error executing method '%s'", method)
            response = {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32603, "message": f"Internal plugin error: {exc!s}"},
            }

        return json.dumps(response)

    def _dispatch(self, method: str, params: dict[str, Any]) -> Any:
        """Route method to plugin implementation."""
        config = params.get("config", {})

        if method == "sync_knowledge":
            return self.plugin.sync_knowledge(config)
        elif method == "dry_run":
            query = params.get("query", "")
            return self.plugin.dry_run(query, config)
        elif method == "execute":
            query = params.get("query", "")
            return self.plugin.execute(query, config)
        elif method == "abort":
            spid = params.get("spid")
            return self.plugin.abort(spid, config)
        elif method == "ping":
            return self.plugin.ping(config)
        else:
            raise PluginException(message=f"Method '{method}' not found", code=-32601)

    def run(self) -> None:
        """Run the main Stdio loop reading from stdin until EOF."""
        try:
            for raw_line in self.stdin:
                response_str = self.handle_request(raw_line)
                if response_str is not None:
                    self.stdout.write(response_str + "\n")
                    self.stdout.flush()
        except KeyboardInterrupt:
            pass
