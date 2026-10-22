"""SQLite Database configuration and SQLModel entities for AegisGate Core.

Strictly adheres to python_clean_code.md:
- Full type hinting
- Clear separation of models
- Database session dependency injection
"""

from collections.abc import Generator
from datetime import datetime, timezone
import logging

logger = logging.getLogger("AegisGate.Database")

from sqlalchemy import text
from sqlmodel import Field, Session, SQLModel, create_engine, select

from core.config import settings


def utc_now() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(timezone.utc)


class PluginProfile(SQLModel, table=True):
    """Registered Plugin metadata and operational state."""

    __tablename__ = "plugin_profiles"

    id: str = Field(primary_key=True, index=True, description="Unique plugin key")
    name: str = Field(description="Display name of the target plugin")
    driver: str = Field(description="Driver or engine identifier (e.g. pyodbc / mssql)")
    entrypoint: str = Field(description="CLI command to invoke the plugin subprocess")
    dry_run_command: str = Field(default="SET SHOWPLAN_XML ON", description="Target dry run inspection directive")
    abort_command: str = Field(default="KILL {spid}", description="Emergency abort/kill command")
    config_json: str = Field(default="{}", description="Connection profile parameters in JSON format")
    ui_schema_json: str = Field(default="[]", description="Dynamic UI form schema in JSON format")
    custom_card_json: str = Field(default="{}", description="Plugin-specific custom card in JSON format")
    status: str = Field(default="active", description="Status: active | inactive | error")
    latency_ms: float = Field(default=0.0, description="Average response latency in ms")
    active_sessions_count: int = Field(default=0, description="Current number of active sessions/SPIDs")
    is_certified: bool = Field(default=False, description="Whether plugin passed 4-stage sanity linter")
    certification_report_json: str | None = Field(default=None, description="Detailed 4-stage sanity check report in JSON")
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class KnowledgeChunk(SQLModel, table=True):
    """Partitioned knowledge chunk holding structural metadata and references to docs."""

    __tablename__ = "knowledge_chunks"

    id: str = Field(primary_key=True, index=True, description="Unique chunk identifier")
    target_id: str = Field(index=True, description="ID of the plugin/target this chunk belongs to")
    partition_key: str = Field(index=True, description="Partition name, e.g. Sales, Accounting")
    title: str = Field(description="Human readable partition title")
    catalog_json: str = Field(default="{}", description="JSON containing tables, columns, types, indexes")
    doc_file: str | None = Field(default=None, description="Filename in knowledge_docs storing doc.md")
    skills_file: str | None = Field(default=None, description="Filename in knowledge_docs storing skills.md")
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class Rule(SQLModel, table=True):
    """Governance rules enforced on AI queries during dry-run."""

    __tablename__ = "governance_rules"

    id: str = Field(primary_key=True, index=True, description="Rule key (e.g. rule_no_orders_audit_join)")
    name: str = Field(description="Human-readable rule name")
    target_id: str | None = Field(default=None, index=True, description="Target plugin ID or null for global")
    rule_type: str = Field(description="Rule type: FORBID_JOIN | FORBID_TABLE_SCAN | MAX_EXECUTION_TIME | CUSTOM")
    expression: str = Field(description="Rule parameter (e.g. 'Orders,AuditLogs' or '15')")
    description: str = Field(default="", description="Explanation of why this rule exists")
    severity: str = Field(default="HIGH", description="Severity: CRITICAL | HIGH | MEDIUM | LOW")
    is_active: bool = Field(default=True, description="Whether rule is actively enforced")
    created_at: datetime = Field(default_factory=utc_now)


class ExecutionLog(SQLModel, table=True):
    """Audit log and state tracking for every query lifecycle."""

    __tablename__ = "execution_logs"

    id: str = Field(primary_key=True, index=True, description="Unique execution ID e.g. exec_88192")
    target_id: str = Field(index=True, description="Target plugin ID")
    query: str = Field(description="SQL or command statement requested by AI")
    query_type: str = Field(default="READ", description="READ or WRITE")
    reasoning: str = Field(default="", description="AI intent and reasoning for this query")
    status: str = Field(
        default="DRY_RUN",
        index=True,
        description="DRY_RUN | PAUSED_FOR_REVIEW | EXECUTING | COMPLETED | REJECTED | TIMEOUT | ABORTED",
    )
    explain_plan_json: str | None = Field(default=None, description="Dry-run explain plan result")
    violations_json: str | None = Field(default="[]", description="JSON list of rule violations detected")
    execution_time_ms: float | None = Field(default=None, description="Actual execution duration in ms")
    auto_approved: bool = Field(default=False, description="Whether auto-approved without manual review")
    approved_by: str | None = Field(default=None, description="User or system entity that approved")
    result_summary: str | None = Field(default=None, description="Serialized sample data or affected rows")
    error_message: str | None = Field(default=None, description="Error message if failed or rejected")
    spid: int | None = Field(default=None, description="Database SPID assigned during execution")
    created_at: datetime = Field(default_factory=utc_now)
    finished_at: datetime | None = Field(default=None)


class SystemSetting(SQLModel, table=True):
    """System-wide configuration settings stored in DB."""

    __tablename__ = "system_settings"

    key: str = Field(primary_key=True, index=True)
    value: str
    description: str | None = None
    updated_at: datetime = Field(default_factory=utc_now)


engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    connect_args={"check_same_thread": False},
)


def init_db() -> None:
    """Initialize database tables and create required storage directories."""
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    settings.KNOWLEDGE_DOCS_DIR.mkdir(parents=True, exist_ok=True)
    SQLModel.metadata.create_all(engine)

    # Ensure schema migrations for dynamic ui columns in existing sqlite database
    with engine.connect() as conn:
        for col_name, col_type, col_default in [
            ("ui_schema_json", "TEXT", "'[]'"),
            ("custom_card_json", "TEXT", "'{}'"),
            ("is_certified", "BOOLEAN", "0"),
            ("certification_report_json", "TEXT", "NULL"),
        ]:
            try:
                conn.execute(text(f"ALTER TABLE plugin_profiles ADD COLUMN {col_name} {col_type} DEFAULT {col_default}"))
                conn.commit()
            except Exception as mig_err:
                # Column already exists in SQLite schema
                logger.debug("Column %s migration note: %s", col_name, mig_err)

    with Session(engine) as session:
        # 1. Initialize default auto_approval_mode setting if not present
        statement = select(SystemSetting).where(SystemSetting.key == "auto_approval_mode")
        setting = session.exec(statement).first()
        if not setting:
            default_val = "true" if settings.AUTO_APPROVAL_DEFAULT else "false"
            session.add(
                SystemSetting(
                    key="auto_approval_mode",
                    value=default_val,
                    description="When enabled, queries that pass Dry-Run execute automatically without manual pause.",
                    updated_at=utc_now(),
                )
            )

        # 2. Seed default Governance Rules
        default_rules = [
            Rule(
                id="rule_no_join_orders_auditlogs",
                name="Forbid Orders & AuditLogs Join",
                target_id="sqlserver_prod",
                rule_type="FORBID_JOIN",
                expression="Orders,AuditLogs",
                description="Joining high-volume Orders with unindexed AuditLogs is strictly forbidden for security and performance.",
                severity="CRITICAL",
                is_active=True,
            ),
            Rule(
                id="rule_forbid_table_scan",
                name="Forbid Full Table Scans",
                target_id=None,
                rule_type="FORBID_TABLE_SCAN",
                expression="",
                description="Queries without WHERE filter triggering table scans are disallowed.",
                severity="HIGH",
                is_active=True,
            ),
            Rule(
                id="rule_max_exec_time",
                name="Max Execution Time Limit",
                target_id=None,
                rule_type="MAX_EXECUTION_TIME",
                expression="15",
                description="Enforces strict 15s timeout limit on all queries.",
                severity="HIGH",
                is_active=True,
            ),
        ]
        for r in default_rules:
            if not session.exec(select(Rule).where(Rule.id == r.id)).first():
                session.add(r)

        session.commit()

        # 3. Automatically register plugin manifests
        from core.engine.plugin_registry import PluginRegistry
        registry = PluginRegistry(session)
        registry.scan_and_load_manifests()


def get_session() -> Generator[Session, None, None]:
    """Dependency injection generator for FastAPI endpoints."""
    with Session(engine) as session:
        yield session
