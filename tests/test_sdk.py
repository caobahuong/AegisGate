"""Comprehensive unit tests for AegisGate Plugin SDK."""

import io
import json
import pytest
from sdk.aegisgate_sdk.base import BasePlugin
from sdk.aegisgate_sdk.models import PluginExecutionError
from sdk.aegisgate_sdk.server import PluginServer


class DummyValidPlugin(BasePlugin):
    """Concrete mock plugin implementing all 4 required methods."""

    def sync_knowledge(self, config):
        return {"schemas": ["public"], "tables": [{"name": "mock_table"}]}

    def dry_run(self, query, config):
        if "FAIL_DRY_RUN" in query:
            raise PluginExecutionError("Dry run simulation failure", data={"line": 1})
        return {"explain_plan": {"type": "MockScan"}, "risk_score": 10}

    def execute(self, query, config):
        if "CRASH" in query:
            raise RuntimeError("Database connection lost")
        return {"rows_affected": 5, "data": [{"id": 1, "val": "test"}], "spid": 88}

    def abort(self, spid, config):
        return spid == 88


def test_base_plugin_abstract_enforcement():
    """Verify that BasePlugin cannot be instantiated without implementing all methods."""
    class IncompletePlugin(BasePlugin):
        def sync_knowledge(self, config):
            return {}

    with pytest.raises(TypeError):
        IncompletePlugin()  # type: ignore


def test_plugin_server_ping():
    """Verify built-in ping handshake."""
    plugin = DummyValidPlugin()
    server = PluginServer(plugin)

    req = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"})
    res_str = server.handle_request(req)
    assert res_str is not None
    res = json.loads(res_str)

    assert res["jsonrpc"] == "2.0"
    assert res["id"] == 1
    assert res["result"]["status"] == "pong"
    assert "sdk" in res["result"]


def test_plugin_server_sync_knowledge():
    """Verify sync_knowledge dispatch."""
    plugin = DummyValidPlugin()
    server = PluginServer(plugin)

    req = json.dumps({"jsonrpc": "2.0", "id": 2, "method": "sync_knowledge", "params": {"config": {}}})
    res = json.loads(server.handle_request(req))

    assert res["id"] == 2
    assert "result" in res
    assert res["result"]["schemas"] == ["public"]


def test_plugin_server_dry_run():
    """Verify dry_run dispatch."""
    plugin = DummyValidPlugin()
    server = PluginServer(plugin)

    req = json.dumps({
        "jsonrpc": "2.0",
        "id": 3,
        "method": "dry_run",
        "params": {"query": "SELECT * FROM mock_table;", "config": {}}
    })
    res = json.loads(server.handle_request(req))

    assert res["id"] == 3
    assert res["result"]["risk_score"] == 10
    assert res["result"]["explain_plan"]["type"] == "MockScan"


def test_plugin_server_execute():
    """Verify execute dispatch."""
    plugin = DummyValidPlugin()
    server = PluginServer(plugin)

    req = json.dumps({
        "jsonrpc": "2.0",
        "id": 4,
        "method": "execute",
        "params": {"query": "SELECT * FROM mock_table;", "config": {}}
    })
    res = json.loads(server.handle_request(req))

    assert res["id"] == 4
    assert res["result"]["rows_affected"] == 5
    assert res["result"]["spid"] == 88


def test_plugin_server_abort():
    """Verify abort dispatch."""
    plugin = DummyValidPlugin()
    server = PluginServer(plugin)

    req_kill_ok = json.dumps({
        "jsonrpc": "2.0",
        "id": 5,
        "method": "abort",
        "params": {"spid": 88, "config": {}}
    })
    res_ok = json.loads(server.handle_request(req_kill_ok))
    assert res_ok["result"] is True

    req_kill_fail = json.dumps({
        "jsonrpc": "2.0",
        "id": 6,
        "method": "abort",
        "params": {"spid": 999, "config": {}}
    })
    res_fail = json.loads(server.handle_request(req_kill_fail))
    assert res_fail["result"] is False


def test_plugin_server_unknown_method():
    """Verify -32601 error for unknown methods."""
    plugin = DummyValidPlugin()
    server = PluginServer(plugin)

    req = json.dumps({"jsonrpc": "2.0", "id": 7, "method": "non_existent_func"})
    res = json.loads(server.handle_request(req))

    assert "error" in res
    assert res["error"]["code"] == -32601
    assert "Method 'non_existent_func' not found" in res["error"]["message"]


def test_plugin_server_invalid_json():
    """Verify -32700 error for malformed JSON."""
    plugin = DummyValidPlugin()
    server = PluginServer(plugin)

    res = json.loads(server.handle_request("NOT_A_JSON"))
    assert res["error"]["code"] == -32700


def test_plugin_server_invalid_jsonrpc_spec():
    """Verify -32600 error for objects not following JSON-RPC 2.0."""
    plugin = DummyValidPlugin()
    server = PluginServer(plugin)

    # Missing jsonrpc field
    res1 = json.loads(server.handle_request(json.dumps({"id": 10, "method": "ping"})))
    assert res1["error"]["code"] == -32600

    # Missing method field
    res2 = json.loads(server.handle_request(json.dumps({"jsonrpc": "2.0", "id": 11})))
    assert res2["error"]["code"] == -32600


def test_plugin_server_custom_plugin_exception():
    """Verify PluginException serializes custom code and data payload."""
    plugin = DummyValidPlugin()
    server = PluginServer(plugin)

    req = json.dumps({
        "jsonrpc": "2.0",
        "id": 12,
        "method": "dry_run",
        "params": {"query": "FAIL_DRY_RUN", "config": {}}
    })
    res = json.loads(server.handle_request(req))

    assert "error" in res
    assert res["error"]["code"] == -32000
    assert "Dry run simulation failure" in res["error"]["message"]
    assert res["error"]["data"] == {"line": 1}


def test_plugin_server_unhandled_exception():
    """Verify unhandled general exceptions are caught as code -32603."""
    plugin = DummyValidPlugin()
    server = PluginServer(plugin)

    req = json.dumps({
        "jsonrpc": "2.0",
        "id": 13,
        "method": "execute",
        "params": {"query": "CRASH", "config": {}}
    })
    res = json.loads(server.handle_request(req))

    assert "error" in res
    assert res["error"]["code"] == -32603
    assert "Database connection lost" in res["error"]["message"]


def test_plugin_server_stream_run():
    """Verify PluginServer.run loops through stdin lines and produces stdout lines."""
    plugin = DummyValidPlugin()
    input_stream = io.StringIO(
        json.dumps({"jsonrpc": "2.0", "id": 100, "method": "ping"}) + "\n" +
        json.dumps({"jsonrpc": "2.0", "id": 101, "method": "abort", "params": {"spid": 88}}) + "\n"
    )
    output_stream = io.StringIO()

    server = PluginServer(plugin, stdin_stream=input_stream, stdout_stream=output_stream)
    server.run()

    output_lines = [line.strip() for line in output_stream.getvalue().strip().split("\n") if line.strip()]
    assert len(output_lines) == 2

    res1 = json.loads(output_lines[0])
    res2 = json.loads(output_lines[1])

    assert res1["id"] == 100
    assert res1["result"]["status"] == "pong"
    assert res2["id"] == 101
    assert res2["result"] is True

