"""Model Context Protocol (MCP) Server for AegisGate.

Provides 4 standard MCP tools for AI Agents per plan.md & tech.md:
1. get_catalog: Zero-touch structural schema exploration from local cache
2. get_knowledge: Retrieve business docs (doc.md), query skills, and rules
3. submit_execution: Submit queries for Dry-Run -> Governance -> Execution lifecycle
4. check_execution_status: Poll execution state, results, or rejection reasons
"""

import json
from typing import Any, Optional
from mcp.server.fastmcp import FastMCP
from sqlmodel import Session
from core.database import engine
from core.engine.state_machine import ExecutionStateMachine
from core.storage.knowledge_store import KnowledgeStore
from core.storage.log_store import LogStore
from core.storage.rule_store import RuleStore

mcp_app = FastMCP(name="AegisGate-MCP-Server")


@mcp_app.tool()
def get_catalog(target_id: str, partition_key: Optional[str] = None) -> str:
    """Retrieve database schema and structural catalog without touching the target system.
    
    Returns table definitions, columns, data types, and indexes cached in AegisGate.
    Args:
        target_id: Identifier of the target plugin (e.g. 'sqlserver_prod')
        partition_key: Optional partition name (e.g. 'Sales', 'Finance')
    """
    with Session(engine) as session:
        store = KnowledgeStore(session)
        chunks = store.list_chunks(target_id=target_id)
        if partition_key:
            chunks = [c for c in chunks if c["partition_key"].lower() == partition_key.lower()]

        if not chunks:
            return json.dumps(
                {
                    "target_id": target_id,
                    "message": f"No catalog partitions found for target '{target_id}'. Please sync first.",
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
def get_knowledge(target_id: str, partition_key: Optional[str] = None) -> str:
    """Retrieve business documentation (doc.md), query skills, and active rules for a target.
    
    Args:
        target_id: Identifier of the target plugin (e.g. 'sqlserver_prod')
        partition_key: Optional partition name
    """
    with Session(engine) as session:
        k_store = KnowledgeStore(session)
        r_store = RuleStore(session)

        chunks = k_store.list_chunks(target_id=target_id)
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

        active_rules = r_store.list_rules(target_id=target_id, is_active_only=True)
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
                "target_id": target_id,
                "knowledge_chunks": hydrated_chunks,
                "active_rules": rules_output,
            },
            indent=2,
        )


@mcp_app.tool()
async def submit_execution(target_id: str, query: str, reasoning: str = "") -> str:
    """Submit a SQL query or command to AegisGate for Dry-Run and Execution control.
    
    If Auto Approval is ON, AegisGate executes automatically if valid.
    If Auto Approval is OFF, query transitions to PAUSED_FOR_REVIEW for human approval.
    Args:
        target_id: Identifier of the target plugin (e.g. 'sqlserver_prod')
        query: Raw SQL query statement to execute
        reasoning: Explanation of AI intent and purpose for this query
    """
    with Session(engine) as session:
        state_machine = ExecutionStateMachine(session)
        log = await state_machine.initiate_execution(
            target_id=target_id,
            query=query,
            reasoning=reasoning,
        )

        response_dict: dict[str, Any] = {
            "execution_id": log.id,
            "target_id": log.target_id,
            "query": log.query,
            "query_type": log.query_type,
            "status": log.status,
            "auto_approved": log.auto_approved,
        }

        if log.violations_json:
            try:
                response_dict["violations"] = json.loads(log.violations_json)
            except Exception:
                response_dict["violations"] = []

        if log.explain_plan_json:
            try:
                response_dict["explain_plan"] = json.loads(log.explain_plan_json)
            except Exception:
                response_dict["explain_plan"] = log.explain_plan_json

        if log.status == "COMPLETED" and log.result_summary:
            try:
                response_dict["result"] = json.loads(log.result_summary)
            except Exception:
                response_dict["result"] = log.result_summary
            response_dict["execution_time_ms"] = log.execution_time_ms

        if log.status in ("REJECTED", "TIMEOUT", "ABORTED"):
            response_dict["error_message"] = log.error_message

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

