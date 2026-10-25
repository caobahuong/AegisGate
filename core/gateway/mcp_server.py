"""Model Context Protocol (MCP) Server for AegisGate.

Provides 4 standard MCP tools for AI Agents per plan.md & tech.md:
1. get_catalog: Zero-touch structural schema exploration from local cache
2. get_knowledge: Retrieve business docs (doc.md), query skills, and rules
3. submit_execution: Submit queries for Dry-Run -> Governance -> Execution lifecycle
4. check_execution_status: Poll execution state, results, or rejection reasons
"""

import json
import os
import sys
from typing import Any

import httpx

try:
    from mcp.server.fastmcp import FastMCP
except Exception:
    from mcp.server.mcpserver import MCPServer as FastMCP  # type: ignore[no-redef, import-not-found]
from sqlmodel import Session

from core.database import engine
from core.storage.knowledge_store import KnowledgeStore
from core.storage.log_store import LogStore
from core.storage.rule_store import RuleStore

API_BASE_URL: str = os.environ.get("AEGISGATE_API_URL", "http://127.0.0.1:8000").rstrip("/")
SUBMIT_TIMEOUT_SECONDS: float = 90.0  # covers dry-run + a 30s write + review pause

# Parse optional --plugin from command line
DEFAULT_TARGET_ID: str | None = None
for idx, arg in enumerate(sys.argv):
    if arg == "--plugin" and idx + 1 < len(sys.argv):
        DEFAULT_TARGET_ID = sys.argv[idx + 1]
        break

server_name = f"AegisGate-MCP-{DEFAULT_TARGET_ID}" if DEFAULT_TARGET_ID else "AegisGate-MCP-Server"
mcp_app = FastMCP(name=server_name)


@mcp_app.tool()
def get_catalog(target_id: str | None = None, partition_key: str | None = None) -> str:
    """Retrieve database schema and structural catalog without touching the target system.

    Returns table definitions, columns, data types, and indexes cached in AegisGate.
    Args:
        target_id: Identifier of the target plugin (e.g. 'sqlserver_prod'). Defaults to server's bound target if configured.
        partition_key: Optional partition name (e.g. 'Sales', 'Finance')
    """
    effective_target = target_id or DEFAULT_TARGET_ID
    if not effective_target:
        return json.dumps(
            {"error": "target_id must be provided when server is not bound to a specific plugin."},
            indent=2,
        )

    with Session(engine) as session:
        store = KnowledgeStore(session)
        chunks = store.list_chunks(target_id=effective_target)
        if partition_key:
            chunks = [c for c in chunks if c["partition_key"].lower() == partition_key.lower()]

        if not chunks:
            return json.dumps(
                {
                    "target_id": effective_target,
                    "message": f"No catalog partitions found for target '{effective_target}'. Please sync first.",
                    "partitions": [],
                },
                indent=2,
            )

        output = [
            {
                "partition_key": c["partition_key"],
                "title": c["title"],
                "catalog": c["catalog"],
            }
            for c in chunks
        ]
        return json.dumps(output, indent=2)


@mcp_app.tool()
def get_knowledge(target_id: str | None = None, partition_key: str | None = None) -> str:
    """Retrieve business documentation (doc.md), query skills, and active rules for a target.

    Args:
        target_id: Identifier of the target plugin (e.g. 'sqlserver_prod'). Defaults to server's bound target if configured.
        partition_key: Optional partition name
    """
    effective_target = target_id or DEFAULT_TARGET_ID
    if not effective_target:
        return json.dumps(
            {"error": "target_id must be provided when server is not bound to a specific plugin."},
            indent=2,
        )

    with Session(engine) as session:
        k_store = KnowledgeStore(session)
        r_store = RuleStore(session)

        chunks = k_store.list_chunks(target_id=effective_target)
        if partition_key:
            chunks = [c for c in chunks if c["partition_key"].lower() == partition_key.lower()]

        hydrated_chunks = []
        for c in chunks:
            full = k_store.get_chunk(c["id"])
            if full:
                hydrated_chunks.append(
                    {
                        "partition_key": full["partition_key"],
                        "title": full["title"],
                        "documentation": full["doc_content"],
                        "skills": full["skills_content"],
                    }
                )

        active_rules = r_store.list_rules(target_id=effective_target, is_active_only=True)
        rules_output = [
            {
                "id": r.id,
                "name": r.name,
                "rule_type": r.rule_type,
                "expression": r.expression,
                "description": r.description,
                "severity": r.severity,
            }
            for r in active_rules
        ]

        return json.dumps(
            {
                "target_id": effective_target,
                "knowledge_chunks": hydrated_chunks,
                "active_rules": rules_output,
            },
            indent=2,
        )


@mcp_app.tool()
async def submit_execution(query: str, target_id: str | None = None, reasoning: str = "") -> str:
    """Submit a SQL query or command to AegisGate for Dry-Run and Execution control.

    If Auto Approval is ON, AegisGate executes automatically if valid.
    If Auto Approval is OFF, query transitions to PAUSED_FOR_REVIEW for human approval.
    Args:
        query: Raw SQL query statement to execute
        target_id: Identifier of the target plugin (e.g. 'sqlserver_prod'). Defaults to server's bound target if configured.
        reasoning: Explanation of AI intent and purpose for this query
    """
    effective_target = target_id or DEFAULT_TARGET_ID
    if not effective_target:
        return json.dumps(
            {"error": "target_id must be provided when server is not bound to a specific plugin."},
            indent=2,
        )

    # The execution runs inside the AegisGate API process (not in this MCP process) so that
    # its SSE events reach the dashboard in real time. This process is a thin gateway.
    url = f"{API_BASE_URL}/api/monitor/executions"
    payload = {"target_id": effective_target, "query": query, "reasoning": reasoning}
    try:
        async with httpx.AsyncClient(timeout=SUBMIT_TIMEOUT_SECONDS) as client:
            resp = await client.post(url, json=payload)
    except httpx.ConnectError:
        return json.dumps(
            {
                "error": f"AegisGate API is not reachable at {API_BASE_URL}. "
                "Start it (python -m uvicorn core.main:app) or set AEGISGATE_API_URL."
            },
            indent=2,
        )
    except httpx.TimeoutException:
        return json.dumps(
            {"error": "AegisGate API timed out. The query may still be running; use check_execution_status."},
            indent=2,
        )

    if resp.status_code >= 400:
        try:
            detail = resp.json().get("detail", resp.text)
        except ValueError:
            detail = resp.text
        return json.dumps({"error": f"AegisGate rejected the request ({resp.status_code}): {detail}"}, indent=2)

    ex = resp.json()
    response_dict: dict[str, Any] = {
        "execution_id": ex["id"],
        "target_id": ex["target_id"],
        "query": ex["query"],
        "query_type": ex["query_type"],
        "status": ex["status"],
        "auto_approved": ex.get("auto_approved", False),
    }
    if ex.get("violations"):
        response_dict["violations"] = ex["violations"]
    if ex.get("explain_plan") is not None:
        response_dict["explain_plan"] = ex["explain_plan"]
    if ex["status"] == "COMPLETED" and ex.get("result_summary") is not None:
        response_dict["result"] = ex["result_summary"]
        response_dict["execution_time_ms"] = ex.get("execution_time_ms")
    if ex["status"] in ("REJECTED", "TIMEOUT", "ABORTED"):
        response_dict["error_message"] = ex.get("error_message")
    return json.dumps(response_dict, indent=2)


@mcp_app.tool()
def check_execution_status(execution_id: str) -> str:
    """Check the current status and results of a pending or finished execution.

    Args:
        execution_id: The execution ID returned from submit_execution
    """
    with Session(engine) as session:
        log_store = LogStore(session)
        log = log_store.get_log(execution_id)
        if not log:
            return json.dumps(
                {"error": f"Execution with ID '{execution_id}' was not found."},
                indent=2,
            )

        resp: dict[str, Any] = {
            "execution_id": log.id,
            "target_id": log.target_id,
            "status": log.status,
            "query": log.query,
            "query_type": log.query_type,
            "auto_approved": log.auto_approved,
            "created_at": log.created_at.isoformat(),
        }

        if log.execution_time_ms is not None:
            resp["execution_time_ms"] = log.execution_time_ms

        if log.result_summary:
            try:
                resp["result"] = json.loads(log.result_summary)
            except Exception:
                resp["result"] = log.result_summary

        if log.error_message:
            resp["error_message"] = log.error_message

        return json.dumps(resp, indent=2)


if __name__ == "__main__":
    # Remove --plugin <target> from sys.argv so MCPServer stdio runner is clean
    cleaned_argv = [sys.argv[0]]
    skip = False
    for _i, a in enumerate(sys.argv[1:], start=1):
        if skip:
            skip = False
            continue
        if a == "--plugin":
            skip = True
            continue
        cleaned_argv.append(a)
    sys.argv = cleaned_argv
    mcp_app.run()
