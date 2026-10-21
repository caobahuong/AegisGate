"""Service layer encapsulating business logic between REST routes and Core Engines.

Adheres strictly to python_clean_code.md:
- Strict Separation of Concerns (no DB or business logic in routes)
- 100% Type Hints
- Clean custom exception handling
"""

import json
from typing import Any, Optional
from sqlmodel import Session
from core.database import ExecutionLog, PluginProfile, Rule
from core.engine.plugin_registry import PluginRegistry
from core.engine.state_machine import ExecutionStateMachine
from core.exceptions import PluginExecutionError, PluginNotFoundError
from core.gateway.schemas import (
    ApproveExecutionRequest,
    CreateRuleRequest,
    ExecutionResponse,
    KnowledgeChunkResponse,
    PluginProfileResponse,
    RegisterPluginRequest,
    RejectExecutionRequest,
    RuleResponse,
    SubmitExecutionRequest,
    UpdateDocsRequest,
    UpdateRuleRequest,
)
from core.storage.knowledge_store import KnowledgeStore
from core.storage.log_store import LogStore
from core.storage.rule_store import RuleStore
from core.storage.setting_store import SettingStore
from plugins.plugin_contract import SyncKnowledgeParams


def format_execution_response(log: ExecutionLog) -> ExecutionResponse:
    """Helper to convert ExecutionLog entity to ExecutionResponse schema."""
    plan_data = None
    if log.explain_plan_json:
        try:
            plan_data = json.loads(log.explain_plan_json)
        except Exception:
            plan_data = log.explain_plan_json

    violations_data: list[str] = []
    if log.violations_json:
        try:
            violations_data = json.loads(log.violations_json)
        except Exception:
            violations_data = []

    res_summary = None
    if log.result_summary:
        try:
            res_summary = json.loads(log.result_summary)
        except Exception:
            res_summary = log.result_summary

    return ExecutionResponse(
        id=log.id,
        target_id=log.target_id,
        query=log.query,
        query_type=log.query_type,
        reasoning=log.reasoning,
        status=log.status,
        explain_plan=plan_data,
        violations=violations_data,
        execution_time_ms=log.execution_time_ms,
        auto_approved=log.auto_approved,
        approved_by=log.approved_by,
        result_summary=res_summary,
        error_message=log.error_message,
        spid=log.spid,
        created_at=log.created_at.isoformat(),
        finished_at=log.finished_at.isoformat() if log.finished_at else None,
    )


class GatewayService:
    """Consolidated application service for REST endpoints."""

    def __init__(self, session: Session) -> None:
        self.session: Session = session
        self.state_machine: ExecutionStateMachine = ExecutionStateMachine(session)
        self.log_store: LogStore = LogStore(session)
        self.rule_store: RuleStore = RuleStore(session)
        self.knowledge_store: KnowledgeStore = KnowledgeStore(session)
        self.plugin_registry: PluginRegistry = PluginRegistry(session)
        self.setting_store: SettingStore = SettingStore(session)

    # --- Execution & Monitor Services ---

    async def submit_execution(self, req: SubmitExecutionRequest) -> ExecutionResponse:
        """Submit an AI query for Dry-Run and Execution lifecycle."""
        log = await self.state_machine.initiate_execution(
            target_id=req.target_id,
            query=req.query,
            reasoning=req.reasoning,
        )
        return format_execution_response(log)

    async def approve_execution(self, execution_id: str, req: ApproveExecutionRequest) -> ExecutionResponse:
        """Approve and resume a paused execution."""
        log = await self.state_machine.approve_and_resume(
            execution_id=execution_id,
            approved_by=req.approved_by,
        )
        return format_execution_response(log)

    async def reject_execution(self, execution_id: str, req: RejectExecutionRequest) -> ExecutionResponse:
        """Reject a paused execution."""
        log = await self.state_machine.reject(
            execution_id=execution_id,
            rejected_by=req.rejected_by,
            reason=req.reason,
        )
        return format_execution_response(log)

    async def abort_execution(self, execution_id: str) -> ExecutionResponse:
        """Abort/kill an in-flight or paused execution."""
        log = await self.state_machine.abort_execution(execution_id=execution_id)
        return format_execution_response(log)

    def get_execution(self, execution_id: str) -> Optional[ExecutionResponse]:
        """Get detail of a specific execution."""
        log = self.log_store.get_log(execution_id)
        return format_execution_response(log) if log else None

    def list_executions(
        self, limit: int = 50, target_id: Optional[str] = None, status: Optional[str] = None
    ) -> list[ExecutionResponse]:
        """List execution logs."""
        logs = self.log_store.list_logs(limit=limit, target_id=target_id, status=status)
        return [format_execution_response(log) for log in logs]

    # --- Plugin Management Services ---

    def list_plugins(self) -> list[PluginProfileResponse]:
        """List all registered plugins."""
        profiles = self.plugin_registry.list_profiles()
        res: list[PluginProfileResponse] = []
        for p in profiles:
            cfg = {}
            try:
                cfg = json.loads(p.config_json)
            except Exception:
                cfg = {}
            res.append(
                PluginProfileResponse(
                    id=p.id,
                    name=p.name,
                    driver=p.driver,
                    entrypoint=p.entrypoint,
                    dry_run_command=p.dry_run_command,
                    abort_command=p.abort_command,
                    config=cfg,
                    status=p.status,
                    latency_ms=p.latency_ms,
                    active_sessions_count=p.active_sessions_count,
                    created_at=p.created_at.isoformat(),
                    updated_at=p.updated_at.isoformat(),
                )
            )
        return res

    def register_plugin(self, req: RegisterPluginRequest) -> PluginProfileResponse:
        """Register or update a plugin profile."""
        profile = PluginProfile(
            id=req.id,
            name=req.name,
            driver=req.driver,
            entrypoint=req.entrypoint,
            dry_run_command=req.dry_run_command,
            abort_command=req.abort_command,
            config_json=json.dumps(req.config),
            status="active",
        )
        saved = self.plugin_registry.register_profile(profile)
        return PluginProfileResponse(
            id=saved.id,
            name=saved.name,
            driver=saved.driver,
            entrypoint=saved.entrypoint,
            dry_run_command=saved.dry_run_command,
            abort_command=saved.abort_command,
            config=req.config,
            status=saved.status,
            latency_ms=saved.latency_ms,
            active_sessions_count=saved.active_sessions_count,
            created_at=saved.created_at.isoformat(),
            updated_at=saved.updated_at.isoformat(),
        )

    async def sync_plugin_catalog(self, plugin_id: str) -> list[dict[str, Any]]:
        """Trigger sync_knowledge on the plugin subprocess and ingest into KnowledgeStore."""
        profile = self.plugin_registry.get_profile(plugin_id)
        client = self.plugin_registry.get_client(plugin_id)

        cfg: dict[str, Any] = {}
        try:
            cfg = json.loads(profile.config_json)
        except Exception:
            cfg = {}

        try:
            sync_res = await client.sync_knowledge(SyncKnowledgeParams(config=cfg))
            partitions_raw = [p.model_dump() for p in sync_res.partitions]
            chunks = self.knowledge_store.ingest_plugin_catalog(
                target_id=plugin_id,
                catalog_partitions=partitions_raw,
            )
            return [self.knowledge_store.get_chunk(c.id) or {} for c in chunks]
        except Exception as exc:
            raise PluginExecutionError(f"Failed to sync catalog for '{plugin_id}': {exc}") from exc

    # --- Knowledge & Rules Services ---

    def list_knowledge_chunks(self, target_id: Optional[str] = None) -> list[KnowledgeChunkResponse]:
        """List knowledge chunks."""
        chunks = self.knowledge_store.list_chunks(target_id=target_id)
        return [
            KnowledgeChunkResponse(
                id=c["id"],
                target_id=c["target_id"],
                partition_key=c["partition_key"],
                title=c["title"],
                catalog=c["catalog"],
                created_at=c["created_at"],
                updated_at=c["updated_at"],
            )
            for c in chunks
        ]

    def get_knowledge_chunk(self, chunk_id: str) -> Optional[KnowledgeChunkResponse]:
        """Get knowledge chunk with hydrated markdown docs."""
        data = self.knowledge_store.get_chunk(chunk_id)
        if not data:
            return None
        return KnowledgeChunkResponse(
            id=data["id"],
            target_id=data["target_id"],
            partition_key=data["partition_key"],
            title=data["title"],
            catalog=data["catalog"],
            doc_content=data["doc_content"],
            skills_content=data["skills_content"],
            created_at=data["created_at"],
            updated_at=data["updated_at"],
        )

    def update_knowledge_docs(self, chunk_id: str, req: UpdateDocsRequest) -> bool:
        """Update markdown documentation for a chunk."""
        return self.knowledge_store.update_docs(
            chunk_id=chunk_id,
            doc_content=req.doc_content,
            skills_content=req.skills_content,
        )

    def list_rules(self, target_id: Optional[str] = None) -> list[RuleResponse]:
        """List governance rules."""
        rules = self.rule_store.list_rules(target_id=target_id)
        return [
            RuleResponse(
                id=r.id,
                name=r.name,
                target_id=r.target_id,
                rule_type=r.rule_type,
                expression=r.expression,
                description=r.description,
                severity=r.severity,
                is_active=r.is_active,
                created_at=r.created_at.isoformat(),
            )
            for r in rules
        ]

    def create_rule(self, req: CreateRuleRequest) -> RuleResponse:
        """Create a new governance rule."""
        rule = Rule(
            id=req.id,
            name=req.name,
            target_id=req.target_id,
            rule_type=req.rule_type,
            expression=req.expression,
            description=req.description,
            severity=req.severity,
            is_active=req.is_active,
        )
        saved = self.rule_store.create_rule(rule)
        return RuleResponse(
            id=saved.id,
            name=saved.name,
            target_id=saved.target_id,
            rule_type=saved.rule_type,
            expression=saved.expression,
            description=saved.description,
            severity=saved.severity,
            is_active=saved.is_active,
            created_at=saved.created_at.isoformat(),
        )

    def update_rule(self, rule_id: str, req: UpdateRuleRequest) -> Optional[RuleResponse]:
        """Update an existing rule."""
        updates = {k: v for k, v in req.model_dump().items() if v is not None}
        updated = self.rule_store.update_rule(rule_id, updates)
        if not updated:
            return None
        return RuleResponse(
            id=updated.id,
            name=updated.name,
            target_id=updated.target_id,
            rule_type=updated.rule_type,
            expression=updated.expression,
            description=updated.description,
            severity=updated.severity,
            is_active=updated.is_active,
            created_at=updated.created_at.isoformat(),
        )

    def delete_rule(self, rule_id: str) -> bool:
        """Delete rule."""
        return self.rule_store.delete_rule(rule_id)

    # --- System Settings Services ---

    def is_auto_mode(self) -> bool:
        """Check auto mode status."""
        return self.setting_store.is_auto_approval_enabled()

    def set_auto_mode(self, enabled: bool) -> bool:
        """Set auto mode status."""
        return self.setting_store.set_auto_approval(enabled)

