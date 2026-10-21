"""Execution State Machine implementing the Dry-Run -> Pause/Auto -> Execute -> Log lifecycle.

Strictly adheres to python_clean_code.md:
- Type annotations 100%
- Proper exception handling
- Separation of Engine from Router
"""

import json
import logging
from typing import Any, Optional
from sqlmodel import Session
from core.database import ExecutionLog, utc_now
from core.engine.governance import GovernanceEngine
from core.engine.plugin_registry import PluginRegistry
from core.engine.timeout_guard import TimeoutGuard
from core.exceptions import (
    ExecutionStateError,
    ExecutionTimeoutError,
    PluginExecutionError,
)
from core.gateway.sse_broadcaster import sse_broadcaster
from core.storage.log_store import LogStore
from core.storage.rule_store import RuleStore
from core.storage.setting_store import SettingStore
from plugins.plugin_contract import AbortParams, DryRunParams, ExecuteParams

logger = logging.getLogger(__name__)


class ExecutionStateMachine:
    """Manages the full lifecycle and state transitions of query execution."""

    def __init__(self, session: Session) -> None:
        self.session: Session = session
        self.log_store: LogStore = LogStore(session)
        self.rule_store: RuleStore = RuleStore(session)
        self.setting_store: SettingStore = SettingStore(session)
        self.registry: PluginRegistry = PluginRegistry(session)

    async def initiate_execution(
        self,
        target_id: str,
        query: str,
        reasoning: str = "",
        execution_id: Optional[str] = None,
    ) -> ExecutionLog:
        """Step 1 & 2: Ingest query, perform Dry-Run, evaluate Rules, transition to Pause or Execute."""
        if not execution_id:
            import uuid
            execution_id = f"exec_{uuid.uuid4().hex[:8]}"

        query_type = GovernanceEngine.determine_query_type(query)

        log = ExecutionLog(
            id=execution_id,
            target_id=target_id,
            query=query,
            query_type=query_type,
            reasoning=reasoning,
            status="DRY_RUN",
            created_at=utc_now(),
        )
        self.log_store.create_log(log)

        await sse_broadcaster.broadcast(
            "execution_created",
            {
                "execution_id": log.id,
                "target_id": log.target_id,
                "query": log.query,
                "query_type": log.query_type,
                "reasoning": log.reasoning,
                "status": log.status,
            },
        )

        # 1. Fetch active rules
        active_rules = self.rule_store.list_rules(target_id=target_id, is_active_only=True)
        rules_payload = [r.model_dump() for r in active_rules]

        # 2. Call Plugin Dry-Run via Subprocess Client
        client = self.registry.get_client(target_id)
        violations: list[str] = []
        explain_plan_dict: Any = {}
        try:
            dry_run_res = await client.dry_run(
                DryRunParams(query=query, rules=rules_payload)
            )
            explain_plan_dict = dry_run_res.explain_plan
            violations.extend(dry_run_res.violations)
            if dry_run_res.query_type:
                log.query_type = dry_run_res.query_type
        except Exception as exc:
            logger.warning("Plugin dry_run failed or fallback: %s", exc)
            explain_plan_dict = {"mode": "fallback_inspection", "target": target_id}

        # 3. Core Governance Engine validation
        core_violations = GovernanceEngine.inspect_query_and_plan(
            query=query,
            rules=active_rules,
            explain_plan=explain_plan_dict,
        )
        for v in core_violations:
            if v not in violations:
                violations.append(v)

        log.explain_plan_json = json.dumps(explain_plan_dict)
        log.violations_json = json.dumps(violations)

        # 4. If rules violated -> REJECT immediately
        if violations:
            log.status = "REJECTED"
            log.error_message = "; ".join(violations)
            log.finished_at = utc_now()
            self.log_store.update_log(
                log.id,
                {
                    "status": log.status,
                    "explain_plan_json": log.explain_plan_json,
                    "violations_json": log.violations_json,
                    "error_message": log.error_message,
                    "finished_at": log.finished_at,
                },
            )
            await sse_broadcaster.broadcast(
                "execution_rejected",
                {"execution_id": log.id, "violations": violations},
            )
            return log

        # 5. If valid -> check Auto Approval Mode
        is_auto_on = self.setting_store.is_auto_approval_enabled()
        if is_auto_on:
            log.auto_approved = True
            log.approved_by = "System (Auto Approval ON)"
            log.status = "EXECUTING"
            self.log_store.update_log(
                log.id,
                {
                    "auto_approved": True,
                    "approved_by": log.approved_by,
                    "status": log.status,
                    "explain_plan_json": log.explain_plan_json,
                    "violations_json": log.violations_json,
                },
            )
            await sse_broadcaster.broadcast(
                "execution_auto_approved",
                {"execution_id": log.id, "status": "EXECUTING"},
            )
            # Execute step asynchronously
            return await self._execute_step(log)
        else:
            # Pause for human review
            log.status = "PAUSED_FOR_REVIEW"
            self.log_store.update_log(
                log.id,
                {
                    "status": log.status,
                    "explain_plan_json": log.explain_plan_json,
                    "violations_json": log.violations_json,
                },
            )
            await sse_broadcaster.broadcast(
                "execution_paused",
                {
                    "execution_id": log.id,
                    "status": log.status,
                    "query": log.query,
                    "explain_plan": explain_plan_dict,
                },
            )
            return log

    async def approve_and_resume(
        self, execution_id: str, approved_by: str = "Admin"
    ) -> ExecutionLog:
        """User approves a PAUSED execution from Dashboard, resuming execution."""
        log = self.log_store.get_log(execution_id)
        if not log:
            raise ExecutionStateError(f"Execution '{execution_id}' does not exist.")

        if log.status != "PAUSED_FOR_REVIEW":
            raise ExecutionStateError(
                f"Cannot resume execution in status '{log.status}'. Expected 'PAUSED_FOR_REVIEW'."
            )

        log.status = "EXECUTING"
        log.approved_by = approved_by
        self.log_store.update_log(
            log.id,
            {"status": "EXECUTING", "approved_by": approved_by},
        )
        await sse_broadcaster.broadcast(
            "execution_resumed",
            {"execution_id": log.id, "approved_by": approved_by},
        )

        return await self._execute_step(log)

    async def reject(
        self, execution_id: str, rejected_by: str = "Admin", reason: str = "Rejected by user"
    ) -> ExecutionLog:
        """User rejects a PAUSED execution from Dashboard."""
        log = self.log_store.get_log(execution_id)
        if not log:
            raise ExecutionStateError(f"Execution '{execution_id}' does not exist.")

        if log.status not in ("PAUSED_FOR_REVIEW", "DRY_RUN"):
            raise ExecutionStateError(f"Cannot reject execution in status '{log.status}'.")

        log.status = "REJECTED"
        log.error_message = f"{reason} ({rejected_by})"
        log.finished_at = utc_now()
        self.log_store.update_log(
            log.id,
            {
                "status": "REJECTED",
                "error_message": log.error_message,
                "finished_at": log.finished_at,
            },
        )
        await sse_broadcaster.broadcast(
            "execution_rejected",
            {"execution_id": log.id, "reason": log.error_message},
        )
        return log

    async def abort_execution(self, execution_id: str) -> ExecutionLog:
        """User stops or kills an in-flight execution."""
        log = self.log_store.get_log(execution_id)
        if not log:
            raise ExecutionStateError(f"Execution '{execution_id}' does not exist.")

        # Urgently call plugin abort
        try:
            client = self.registry.get_client(log.target_id)
            await client.abort(AbortParams(execution_id=execution_id))
        except Exception as exc:
            logger.warning("Plugin abort warning: %s", exc)

        log.status = "ABORTED"
        log.error_message = "Execution manually aborted/killed by user."
        log.finished_at = utc_now()
        self.log_store.update_log(
            log.id,
            {
                "status": "ABORTED",
                "error_message": log.error_message,
                "finished_at": log.finished_at,
            },
        )
        await sse_broadcaster.broadcast(
            "execution_aborted",
            {"execution_id": log.id, "status": "ABORTED"},
        )
        return log

    async def _execute_step(self, log: ExecutionLog) -> ExecutionLog:
        """Internal execution under Timeout Guard (15s read / 30s write)."""
        timeout_seconds = TimeoutGuard.get_timeout_for_query(log.query_type)
        client = self.registry.get_client(log.target_id)

        async def _abort_hook() -> None:
            logger.warning("Timeout reached! Triggering emergency kill for %s", log.id)
            await client.abort(AbortParams(execution_id=log.id))

        try:
            execute_coro = client.execute(
                ExecuteParams(
                    execution_id=log.id,
                    query=log.query,
                    timeout_seconds=timeout_seconds,
                )
            )

            result = await TimeoutGuard.run_with_timeout(
                coro=execute_coro,
                timeout_seconds=timeout_seconds,
                on_timeout_abort=_abort_hook,
            )

            # Success
            log.status = "COMPLETED"
            log.execution_time_ms = result.execution_time_ms
            log.spid = result.spid
            log.result_summary = json.dumps(
                {"data": result.data, "rows_affected": result.rows_affected}
            )
            log.finished_at = utc_now()

            self.log_store.update_log(
                log.id,
                {
                    "status": "COMPLETED",
                    "execution_time_ms": result.execution_time_ms,
                    "spid": result.spid,
                    "result_summary": log.result_summary,
                    "finished_at": log.finished_at,
                },
            )

            # Update plugin latency metric
            self.registry.update_metrics(log.target_id, latency_ms=result.execution_time_ms)

            await sse_broadcaster.broadcast(
                "execution_completed",
                {
                    "execution_id": log.id,
                    "status": "COMPLETED",
                    "execution_time_ms": result.execution_time_ms,
                    "rows_affected": result.rows_affected,
                },
            )
            return log

        except ExecutionTimeoutError as exc:
            log.status = "TIMEOUT"
            log.error_message = str(exc)
            log.finished_at = utc_now()
            self.log_store.update_log(
                log.id,
                {
                    "status": "TIMEOUT",
                    "error_message": log.error_message,
                    "finished_at": log.finished_at,
                },
            )
            await sse_broadcaster.broadcast(
                "execution_timeout",
                {"execution_id": log.id, "error": str(exc)},
            )
            return log

        except Exception as exc:
            log.status = "REJECTED"
            log.error_message = f"Execution failed: {exc}"
            log.finished_at = utc_now()
            self.log_store.update_log(
                log.id,
                {
                    "status": "REJECTED",
                    "error_message": log.error_message,
                    "finished_at": log.finished_at,
                },
            )
            await sse_broadcaster.broadcast(
                "execution_failed",
                {"execution_id": log.id, "error": str(exc)},
            )
            return log

