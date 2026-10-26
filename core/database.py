"""Database configuration, SQLModel entities, and Alembic migrations for AegisGate Core.

Strictly adheres to python_clean_code.md:
- Full type hinting
- Clear separation of models
- Database session dependency injection
- Alembic programmatic migrations with automatic stamping of existing databases
"""

import logging
import sqlite3
from collections.abc import Generator
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Index, event, inspect, text
from sqlmodel import Field, Session, SQLModel, create_engine, select

from alembic import command
from alembic.config import Config
from core.config import settings

logger = logging.getLogger("AegisGate.Database")


def utc_now() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(UTC)


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
    certification_report_json: str | None = Field(
        default=None, description="Detailed 4-stage sanity check report in JSON"
    )
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
    __table_args__ = (
        Index("ix_execution_logs_target_created", "target_id", "created_at"),
        Index("ix_execution_logs_status_created", "status", "created_at"),
    )

    id: str = Field(primary_key=True, index=True, description="Unique execution ID e.g. exec_88192")
    target_id: str = Field(index=True, description="Target plugin ID")
    query: str = Field(description="SQL or command statement requested by AI")
    query_type: str = Field(default="READ", description="READ or WRITE")
    reasoning: str = Field(default="", description="AI intent and reasoning for this query")
    status: str = Field(
        default="DRY_RUN",
        index=True,
        description="DRY_RUN | QUEUED | PAUSED_FOR_REVIEW | EXECUTING | COMPLETED | REJECTED | TIMEOUT | ABORTED | FAILED",
    )
    explain_plan_json: str | None = Field(default=None, description="Dry-run explain plan result")
    violations_json: str | None = Field(default="[]", description="JSON list of rule violations detected")
    execution_time_ms: float | None = Field(default=None, description="Actual execution duration in ms")
    auto_approved: bool = Field(default=False, description="Whether auto-approved without manual review")
    approved_by: str | None = Field(default=None, description="User or system entity that approved")
    result_summary: str | None = Field(default=None, description="Serialized sample data or affected rows")
    error_message: str | None = Field(default=None, description="Error message if failed or rejected")
    spid: int | None = Field(default=None, description="Database SPID assigned during execution")
    owner_id: str | None = Field(default=None, index=True, description="UUID of the process that runs it")
    started_at: datetime | None = Field(default=None, description="Timestamp execution actually started")
    created_at: datetime = Field(default_factory=utc_now, index=True)
    finished_at: datetime | None = Field(default=None)


class SystemSetting(SQLModel, table=True):
    """System-wide configuration settings stored in DB."""

    __tablename__ = "system_settings"

    key: str = Field(primary_key=True, index=True)
    value: str
    description: str | None = None
    updated_at: datetime = Field(default_factory=utc_now)


class EventOutbox(SQLModel, table=True):
    """Monotonic event outbox for cross-process SSE event bus tailing."""

    __tablename__ = "event_outbox"

    id: int | None = Field(default=None, primary_key=True, description="Monotonic event ID")
    event_type: str = Field(description="Event classification, e.g. execution_created, execution_completed")
    payload_json: str = Field(description="JSON serialized event payload")
    created_at: datetime = Field(default_factory=utc_now, index=True)


class ProcessHeartbeat(SQLModel, table=True):
    """Liveness heartbeat for cluster process instances."""

    __tablename__ = "process_heartbeat"

    owner_id: str = Field(primary_key=True, description="Unique process worker UUID")
    pid: int = Field(description="Operating system process ID")
    host: str = Field(default="localhost", description="Hostname or node address")
    last_seen: datetime = Field(default_factory=utc_now, description="Heartbeat timestamp")


class ExecutionControl(SQLModel, table=True):
    """Cross-process command queue for asynchronous execution control (e.g. ABORT)."""

    __tablename__ = "execution_control"

    id: int | None = Field(default=None, primary_key=True, description="Monotonic control request ID")
    execution_id: str = Field(index=True, description="Target execution session ID")
    command: str = Field(description="Command directive: ABORT")
    requested_at: datetime = Field(default_factory=utc_now)
    handled_at: datetime | None = Field(default=None)


class DistributedLock(SQLModel, table=True):
    """Single-runner distributed lock for cron-like tasks (janitor, pruner)."""

    __tablename__ = "distributed_lock"

    name: str = Field(primary_key=True, description="Lock resource name")
    owner_id: str = Field(description="Current lock owner process ID")
    acquired_at: datetime = Field(default_factory=utc_now)
    expires_at: datetime = Field(description="Lock lease expiration time")


# Database engine configuration with SQLite WAL & high-concurrency pooling
connect_args: dict[str, Any] = {}
pool_kwargs: dict[str, Any] = {}

if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False
    connect_args["timeout"] = 15.0
    pool_kwargs["pool_size"] = 20
    pool_kwargs["max_overflow"] = 30
    pool_kwargs["pool_timeout"] = 30.0

engine = create_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    connect_args=connect_args,
    **pool_kwargs,
)

if settings.DATABASE_URL.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection: Any, connection_record: Any) -> None:
        if isinstance(dbapi_connection, sqlite3.Connection):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA busy_timeout=15000")
            cursor.close()


def init_db(target_engine: Any = None) -> None:
    """Initialize database tables and run Alembic migrations safely."""
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    settings.KNOWLEDGE_DOCS_DIR.mkdir(parents=True, exist_ok=True)
    settings.ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    active_engine = target_engine or engine

    # Inspect existing tables to detect unmigrated pre-Alembic databases
    inspector = inspect(active_engine)
    existing_tables = set(inspector.get_table_names())

    alembic_ini_path = settings.BASE_DIR / "alembic.ini"
    alembic_cfg = Config(str(alembic_ini_path))
    alembic_cfg.set_main_option("script_location", str(settings.BASE_DIR / "alembic"))
    # Alembic ConfigParser uses '%' for interpolation syntax; escape percent-encoded URLs as '%%'
    db_url_str = str(active_engine.url).replace("%", "%%")
    alembic_cfg.set_main_option("sqlalchemy.url", db_url_str)

    has_alembic_version = False
    if "alembic_version" in existing_tables:
        with active_engine.connect() as conn:
            try:
                row = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
                if row is not None:
                    has_alembic_version = True
            except Exception:
                has_alembic_version = False

    if not has_alembic_version:
        if "execution_logs" in existing_tables:
            # Existing database from Phases 1-3: stamp to baseline '001'
            logger.info("Existing database schema detected without valid alembic_version; stamping baseline 001...")
            with active_engine.begin() as conn:
                alembic_cfg.attributes["connection"] = conn
                command.stamp(alembic_cfg, "001")
        else:
            # Completely empty database: create baseline tables via migration
            logger.info("Fresh database detected; running full migrations from head...")

    # Upgrade to latest revision (head)
    with active_engine.begin() as conn:
        alembic_cfg.attributes["connection"] = conn
        command.upgrade(alembic_cfg, "head")

    with Session(active_engine) as session:
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
                target_id=None,
                rule_type="FORBID_JOIN",
                expression="Orders,AuditLogs",
                description="Strict enterprise compliance: Never allow direct joins between transactional Orders and unindexed AuditLogs.",
                severity="CRITICAL",
                is_active=True,
                created_at=utc_now(),
            ),
            Rule(
                id="rule_forbid_payroll_unbounded_scan",
                name="Forbid Unbounded Table Scan on Payroll",
                target_id=None,
                rule_type="FORBID_TABLE_SCAN",
                expression="Finance.Payroll",
                description="Performance rule: Full table scans on Payroll table are forbidden. Queries must include an indexed predicate.",
                severity="HIGH",
                is_active=True,
                created_at=utc_now(),
            ),
            Rule(
                id="rule_max_query_time",
                name="Maximum Execution Time Guard (15s)",
                target_id=None,
                rule_type="MAX_EXECUTION_TIME",
                expression="15",
                description="Prevent runaway lock escalation and transaction blocking by terminating queries exceeding 15 seconds.",
                severity="HIGH",
                is_active=True,
                created_at=utc_now(),
            ),
        ]

        for rule in default_rules:
            existing_rule = session.exec(select(Rule).where(Rule.id == rule.id)).first()
            if not existing_rule:
                session.add(rule)

        session.commit()


def get_session() -> Generator[Session, None, None]:
    """Dependency injection provider for database sessions."""
    with Session(engine) as session:
        yield session
