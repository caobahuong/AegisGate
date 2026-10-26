"""Service layer encapsulating business logic between REST routes and Core Engines.

Adheres strictly to python_clean_code.md:
- Strict Separation of Concerns (no DB or business logic in routes)
- 100% Type Hints
- Clean custom exception handling
"""

import asyncio
import json
import logging
from typing import Any, cast

from sqlmodel import Session

from core.database import ExecutionLog, PluginProfile, Rule, utc_now
from core.engine.governance import GovernanceEngine, validate_rule_definition
from core.engine.plugin_client import terminate_all_subprocesses
from core.engine.plugin_installer import PluginInstaller
from core.engine.plugin_linter import PluginLinter
from core.engine.plugin_registry import PluginRegistry
from core.engine.state_machine import ExecutionStateMachine
from core.exceptions import PluginExecutionError
from core.gateway.schemas import (
    ApproveExecutionRequest,
    CreateRuleRequest,
    ExecutionResponse,
    ExecutionStatus,
    InstallGitPluginRequest,
    KnowledgeChunkResponse,
    McpConfigResponse,
    PluginCertificationResponse,
    PluginProfileResponse,
    PluginSchemaResponse,
    PluginStatus,
    QueryType,
    RegisterPluginRequest,
    RejectExecutionRequest,
    RuleResponse,
    RuleSeverity,
    RuleType,
    SubmitExecutionRequest,
    UpdateDocsRequest,
    UpdatePluginConfigRequest,
    UpdateRuleRequest,
)
from core.storage.knowledge_store import KnowledgeStore
from core.storage.log_store import LogStore
from core.storage.rule_store import RuleStore
from core.storage.setting_store import SettingStore
from plugins.plugin_contract import ReinitParams, SyncKnowledgeParams

logger = logging.getLogger(__name__)


def format_execution_response(log: ExecutionLog) -> ExecutionResponse:
    """Helper to convert ExecutionLog entity to ExecutionResponse schema."""
    plan_data = None
    if log.explain_plan_json:
        try:
            plan_data = json.loads(log.explain_plan_json)
        except (json.JSONDecodeError, TypeError):
            plan_data = log.explain_plan_json

    violations = []
    if log.violations_json:
        try:
            violations = json.loads(log.violations_json)
        except (json.JSONDecodeError, TypeError):
            violations = []

    res_summary = None
    if log.result_summary:
        try:
            res_summary = json.loads(log.result_summary)
        except (json.JSONDecodeError, TypeError):
            res_summary = log.result_summary

    return ExecutionResponse(
        id=log.id,
        target_id=log.target_id,
        query=log.query,
        query_type=cast(QueryType, log.query_type),
        reasoning=log.reasoning,
        status=cast(ExecutionStatus, log.status),
        explain_plan=plan_data,
        violations=violations,
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
    """Unified service orchestrating state machine, knowledge store, and plugins."""

    def __init__(self, session: Session) -> None:
        self.session: Session = session
        self.state_machine: ExecutionStateMachine = ExecutionStateMachine(session)
        self.log_store: LogStore = LogStore(session)
        self.rule_store: RuleStore = RuleStore(session)
        self.knowledge_store: KnowledgeStore = KnowledgeStore(session)
        self.plugin_registry: PluginRegistry = PluginRegistry(session)
        self.setting_store: SettingStore = SettingStore(session)

    # --- Execution & Monitor Services ---

    async def submit_execution(self, req: SubmitExecutionRequest, wait: bool = True) -> ExecutionResponse:
        """Submit an AI query for Dry-Run and Execution lifecycle."""
        if not wait:
            import uuid

            execution_id = f"exec_{uuid.uuid4().hex[:8]}"

            # Run pipeline in a background task
            async def _run_bg() -> None:
                from core.database import get_session

                with next(get_session()) as bg_session:
                    sm = ExecutionStateMachine(bg_session)
                    try:
                        await sm.initiate_execution(
                            target_id=req.target_id,
                            query=req.query,
                            reasoning=req.reasoning,
                            execution_id=execution_id,
                        )
                    except Exception as exc:
                        logger.warning("Background execution failed for %s: %s", execution_id, exc)

            query_type = GovernanceEngine.determine_query_type(req.query)
            init_log = ExecutionLog(
                id=execution_id,
                target_id=req.target_id,
                query=req.query,
                query_type=query_type,
                reasoning=req.reasoning,
                status="DRY_RUN",
                created_at=utc_now(),
            )
            self.log_store.create_log(init_log)
            asyncio.create_task(_run_bg())
            return format_execution_response(init_log)

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
        """Emergency stop and abort an execution."""
        log = await self.state_machine.abort_execution(execution_id=execution_id)
        return format_execution_response(log)

    async def stop_execution(self, execution_id: str) -> ExecutionResponse:
        """Alias for abort_execution."""
        return await self.abort_execution(execution_id)

    def get_execution(self, execution_id: str) -> ExecutionResponse | None:
        """Fetch execution state by ID."""
        log = self.log_store.get_log(execution_id)
        if not log:
            return None
        return format_execution_response(log)

    def list_executions(
        self,
        target_id: str | None = None,
        status: str | None = None,
        limit: int = 50,
    ) -> list[ExecutionResponse]:
        """List execution audit logs."""
        logs = self.log_store.list_logs(
            target_id=target_id,
            status=status,
            limit=limit,
        )
        return [format_execution_response(log) for log in logs]

    # --- Plugin Management Services ---

    def _format_plugin_profile_response(self, p: PluginProfile) -> PluginProfileResponse:
        """Helper to format PluginProfile SQLModel entity to PluginProfileResponse schema."""
        cfg = {}
        try:
            cfg = json.loads(p.config_json)
        except (json.JSONDecodeError, TypeError):
            cfg = {}

        ui_schema = []
        try:
            ui_schema = json.loads(p.ui_schema_json)
        except (json.JSONDecodeError, TypeError):
            ui_schema = []

        custom_card = None
        try:
            if p.custom_card_json and p.custom_card_json != "{}":
                custom_card = json.loads(p.custom_card_json)
        except (json.JSONDecodeError, TypeError):
            custom_card = None

        cert_report = None
        cert_json = getattr(p, "certification_report_json", None)
        if cert_json and isinstance(cert_json, str):
            try:
                cert_report = json.loads(cert_json)
            except (json.JSONDecodeError, TypeError):
                cert_report = None

        return PluginProfileResponse(
            id=p.id,
            name=p.name,
            driver=p.driver,
            entrypoint=p.entrypoint,
            dry_run_command=p.dry_run_command,
            abort_command=p.abort_command,
            config=cfg,
            ui_schema=ui_schema,
            custom_card=custom_card,
            status=cast(PluginStatus, p.status),
            latency_ms=p.latency_ms,
            active_sessions_count=p.active_sessions_count,
            is_certified=getattr(p, "is_certified", False),
            certification_report=cert_report,
            created_at=p.created_at.isoformat(),
            updated_at=p.updated_at.isoformat(),
        )

    def list_plugins(self, include_disabled: bool = False) -> list[PluginProfileResponse]:
        """List all registered plugins."""
        profiles = self.plugin_registry.list_profiles(include_disabled=include_disabled)
        return [self._format_plugin_profile_response(p) for p in profiles]

    def get_plugin_schema(self, plugin_id: str) -> PluginSchemaResponse:
        """Retrieve dynamic UI schema and current config for a plugin."""
        p = self.plugin_registry.get_profile(plugin_id)
        cfg = {}
        try:
            cfg = json.loads(p.config_json)
        except (json.JSONDecodeError, TypeError):
            cfg = {}

        ui_schema = []
        try:
            ui_schema = json.loads(p.ui_schema_json)
        except (json.JSONDecodeError, TypeError):
            ui_schema = []

        custom_card = None
        try:
            if p.custom_card_json and p.custom_card_json != "{}":
                custom_card = json.loads(p.custom_card_json)
        except (json.JSONDecodeError, TypeError):
            custom_card = None

        return PluginSchemaResponse(
            plugin_id=p.id,
            name=p.name,
            driver=p.driver,
            ui_schema=ui_schema,
            current_config=cfg,
            custom_card=custom_card,
        )

    def register_plugin(self, req: RegisterPluginRequest) -> PluginProfileResponse:
        """Register or update a plugin profile."""
        ui_schema_str = json.dumps(req.ui_schema or [])
        custom_card_str = json.dumps(req.custom_card or {})
        profile = PluginProfile(
            id=req.id,
            name=req.name,
            driver=req.driver,
            entrypoint=req.entrypoint,
            dry_run_command=req.dry_run_command,
            abort_command=req.abort_command,
            config_json=json.dumps(req.config),
            ui_schema_json=ui_schema_str,
            custom_card_json=custom_card_str,
            status="active",
        )
        saved = self.plugin_registry.register_profile(profile)
        return self._format_plugin_profile_response(saved)

    async def update_plugin_config(
        self,
        plugin_id: str,
        req: UpdatePluginConfigRequest,
    ) -> PluginProfileResponse:
        """Update plugin configuration in DB and trigger reinit down to subprocess."""
        p = self.plugin_registry.get_profile(plugin_id)
        p.config_json = json.dumps(req.config)
        if req.name:
            p.name = req.name
        if req.driver:
            p.driver = req.driver
        if req.entrypoint:
            p.entrypoint = req.entrypoint
        if req.dry_run_command:
            p.dry_run_command = req.dry_run_command
        if req.abort_command:
            p.abort_command = req.abort_command

        p.updated_at = utc_now()
        self.session.add(p)
        self.session.commit()
        self.session.refresh(p)

        try:
            client = self.plugin_registry.get_client(plugin_id)
            await client.reinit(ReinitParams(config=req.config))
        except Exception as exc:
            logger.warning("Plugin '%s' reinit command note: %s", plugin_id, exc)

        return self._format_plugin_profile_response(p)

    async def delete_plugin(self, plugin_id: str, hard_delete: bool = False) -> dict[str, Any]:
        """Uninstall or disable a plugin, disconnect active subprocesses, and abort running tasks."""
        # Check if profile exists (raises PluginNotFoundError if not found)
        self.plugin_registry.get_profile(plugin_id)

        # 1. Terminate any running plugin subprocesses
        await terminate_all_subprocesses()

        # 2. Abort any paused/in-flight executions for this plugin
        paused_logs = self.log_store.list_logs(target_id=plugin_id, status="PAUSED_FOR_REVIEW")
        for log in paused_logs:
            try:
                await self.state_machine.abort_execution(log.id)
            except Exception as exc:
                logger.warning("Could not abort pending log %s: %s", log.id, exc)

        # 3. Unregister or soft-disable profile
        self.plugin_registry.unregister_profile(plugin_id, hard_delete=hard_delete)

        mode_str = "hard_delete" if hard_delete else "soft_disabled"
        return {
            "success": True,
            "plugin_id": plugin_id,
            "mode": mode_str,
            "message": f"Plugin '{plugin_id}' successfully {'deleted from database' if hard_delete else 'disabled'}.",
        }

    async def sync_plugin_catalog(self, plugin_id: str) -> list[dict[str, Any]]:
        """Trigger sync_knowledge on the plugin subprocess and ingest into KnowledgeStore."""
        profile = self.plugin_registry.get_profile(plugin_id)
        client = self.plugin_registry.get_client(plugin_id)

        cfg: dict[str, Any] = {}
        try:
            cfg = json.loads(profile.config_json)
        except (json.JSONDecodeError, TypeError):
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

    def list_knowledge_chunks(self, target_id: str | None = None) -> list[KnowledgeChunkResponse]:
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

    def get_knowledge_chunk(self, chunk_id: str) -> KnowledgeChunkResponse | None:
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

    def list_rules(
        self,
        target_id: str | None = None,
        exact_target: bool = False,
    ) -> list[RuleResponse]:
        """List governance rules, optionally filtered by target plugin or global scope."""
        rules = self.rule_store.list_rules(target_id=target_id, exact_target=exact_target)
        return [
            RuleResponse(
                id=r.id,
                name=r.name,
                target_id=r.target_id,
                rule_type=cast(RuleType, r.rule_type),
                expression=r.expression,
                description=r.description,
                severity=cast(RuleSeverity, r.severity),
                is_active=r.is_active,
                created_at=r.created_at.isoformat(),
            )
            for r in rules
        ]

    def list_skills(self, target_id: str | None = None) -> list[dict[str, Any]]:
        """List query skills and templates, optionally filtered by target plugin."""
        chunks = self.list_knowledge_chunks(target_id=target_id)
        skills: list[dict[str, Any]] = []
        for c in chunks:
            skills.append(
                {
                    "id": f"{c.id}_skills",
                    "chunk_id": c.id,
                    "target_id": c.target_id,
                    "partition_key": c.partition_key,
                    "title": f"{c.title} Skills",
                    "skills_file": f"{c.id}_skills.md",
                    "skills_content": c.skills_content,
                }
            )
        return skills

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
            rule_type=cast(RuleType, saved.rule_type),
            expression=saved.expression,
            description=saved.description,
            severity=cast(RuleSeverity, saved.severity),
            is_active=saved.is_active,
            created_at=saved.created_at.isoformat(),
        )

    def update_rule(self, rule_id: str, req: UpdateRuleRequest) -> RuleResponse | None:
        """Update an existing rule."""
        raw_dump = req.model_dump(exclude_unset=True)
        updates = {}
        for k, v in raw_dump.items():
            if k == "target_id":
                # Convert empty string or "global" to None for global scoping
                updates[k] = None if v in (None, "", "global") else v
            elif v is not None:
                updates[k] = v

        existing = self.rule_store.get_rule(rule_id)
        if not existing:
            return None
        problem = validate_rule_definition(
            str(updates.get("rule_type", existing.rule_type)),
            str(updates.get("expression", existing.expression)),
        )
        if problem:
            raise ValueError(problem)

        updated = self.rule_store.update_rule(rule_id, updates)
        if not updated:
            return None
        return RuleResponse(
            id=updated.id,
            name=updated.name,
            target_id=updated.target_id,
            rule_type=cast(RuleType, updated.rule_type),
            expression=updated.expression,
            description=updated.description,
            severity=cast(RuleSeverity, updated.severity),
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

    # --- MCP Configuration Services ---

    def get_global_mcp_config(self) -> McpConfigResponse:
        """Generate MCP client connection snippet for AegisGate Core and all active targets."""
        server_key = "aegisgate"
        args = ["-m", "core.gateway.mcp_server"]
        env = {
            "AEGISGATE_API_URL": "http://localhost:8000",
        }
        servers: dict[str, Any] = {
            server_key: {
                "command": "python",
                "args": args,
                "env": env,
            }
        }

        # Include active plugins as individual servers if needed
        for p in self.plugin_registry.list_profiles():
            servers[f"aegisgate-{p.id}"] = {
                "command": "python",
                "args": ["-m", "core.gateway.mcp_server", "--plugin", p.id],
                "env": env,
            }

        return McpConfigResponse(
            server_name=server_key,
            command="python",
            args=args,
            env=env,
            mcpServers=servers,
            client_configs={
                "claude": {"mcpServers": servers},
                "cursor": {"mcpServers": servers},
                "cline": {"mcpServers": servers},
            },
        )

    async def install_plugin_zip(self, file_content: bytes, filename: str | None = None) -> PluginProfileResponse:
        """Install, build, and certify an external plugin from an uploaded ZIP archive."""
        installer = PluginInstaller(self.session)
        profile = await installer.install_from_zip(file_content, filename=filename)
        return self._format_plugin_profile_response(profile)

    async def install_plugin_git(self, req: InstallGitPluginRequest) -> PluginProfileResponse:
        """Clone, build, and certify an external plugin from a remote Git repository."""
        installer = PluginInstaller(self.session)
        profile = await installer.install_from_git(
            git_url=req.git_url,
            branch=req.branch,
            plugin_id_override=req.plugin_id,
        )
        return self._format_plugin_profile_response(profile)

    async def verify_plugin(self, plugin_id: str) -> PluginCertificationResponse:
        """Execute 4-stage sanity checks and generate certification badge."""
        linter = PluginLinter(self.session)
        report = await linter.verify_plugin(plugin_id)
        return PluginCertificationResponse(
            plugin_id=report["plugin_id"],
            certified=report["certified"],
            badge=report["badge"],
            checks=report["checks"],
            verified_at=report["verified_at"],
            error=report.get("error"),
        )

    def get_plugin_mcp_config(self, plugin_id: str) -> McpConfigResponse:
        """Generate MCP client connection snippet for a specific target plugin."""
        profile = self.plugin_registry.get_profile(plugin_id)
        server_key = f"aegisgate-{profile.id}"
        args = ["-m", "core.gateway.mcp_server", "--plugin", profile.id]
        env = {
            "AEGISGATE_API_URL": "http://localhost:8000",
        }
        servers = {
            server_key: {
                "command": "python",
                "args": args,
                "env": env,
            }
        }

        return McpConfigResponse(
            server_name=server_key,
            plugin_id=profile.id,
            command="python",
            args=args,
            env=env,
            mcpServers=servers,
            client_configs={
                "claude": {"mcpServers": servers},
                "cursor": {"mcpServers": servers},
                "cline": {"mcpServers": servers},
            },
        )
