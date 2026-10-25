"""Test model factories for AegisGate.

Provides builder functions with sensible defaults for database models:
- make_plugin_profile
- make_rule
- make_execution_log
"""

import json
import uuid
from typing import Any

from core.database import ExecutionLog, PluginProfile, Rule, utc_now


def make_plugin_profile(
    *,
    id: str | None = None,
    name: str = "Test SQL Server Plugin",
    driver: str = "sqlserver",
    entrypoint: str = "python plugins/sqlserver_plugin/adapter.py --serve",
    status: str = "active",
    config: dict[str, Any] | None = None,
    ui_schema: list[dict[str, Any]] | None = None,
    custom_card: dict[str, Any] | None = None,
    dry_run_command: str = "SET SHOWPLAN_XML ON",
    abort_command: str = "KILL {spid}",
    **kwargs: Any,
) -> PluginProfile:
    """Build a PluginProfile instance with sensible defaults."""
    uid = id or f"plugin_{uuid.uuid4().hex[:8]}"
    return PluginProfile(
        id=uid,
        name=name,
        driver=driver,
        entrypoint=entrypoint,
        status=status,
        config_json=json.dumps(config or {"use_simulation": "true"}),
        ui_schema_json=json.dumps(ui_schema or []),
        custom_card_json=json.dumps(custom_card or {}),
        dry_run_command=dry_run_command,
        abort_command=abort_command,
        updated_at=utc_now(),
        **kwargs,
    )


def make_rule(
    *,
    id: str | None = None,
    name: str = "Forbid Orders Join",
    rule_type: str = "FORBID_JOIN",
    pattern: str = "Orders,AuditLogs",
    target_id: str | None = None,
    is_active: bool = True,
    severity: str = "HIGH",
    description: str = "Block join on sensitive tables",
    **kwargs: Any,
) -> Rule:
    """Build a Rule instance with sensible defaults."""
    uid = id or f"rule_{uuid.uuid4().hex[:8]}"
    return Rule(
        id=uid,
        name=name,
        rule_type=rule_type,
        pattern=pattern,
        target_id=target_id,
        is_active=is_active,
        severity=severity,
        description=description,
        created_at=utc_now(),
        **kwargs,
    )


def make_execution_log(
    *,
    id: str | None = None,
    target_id: str = "sqlserver_prod",
    query_text: str = "SELECT 1;",
    query_type: str = "READ",
    status: str = "COMPLETED",
    client_ip: str = "127.0.0.1",
    client_principal: str = "developer@company.local",
    reason: str = "Routine status check",
    **kwargs: Any,
) -> ExecutionLog:
    """Build an ExecutionLog instance with sensible defaults."""
    uid = id or f"exec_{uuid.uuid4().hex[:8]}"
    return ExecutionLog(
        id=uid,
        target_id=target_id,
        query_text=query_text,
        query_type=query_type,
        status=status,
        client_ip=client_ip,
        client_principal=client_principal,
        reason=reason,
        created_at=utc_now(),
        **kwargs,
    )
