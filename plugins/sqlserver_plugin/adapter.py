"""SQL Server Plugin Adapter implementing the AegisGate Plugin Contract.

Communicates via JSON-RPC 2.0 over Stdio in two modes:

* ``--serve``  (production): ONE long-lived process. Requests are handled on worker threads,
  so an ``abort`` can run while an ``execute`` is still blocked inside the database driver.
  Connections / SPIDs live in this process, which is what makes Stop/Kill real.
* no flag (legacy one-shot): read one request from stdin, answer, exit. Kept for the SDK/tests.

Backends (selected by the plugin configuration):

* real        - pyodbc against SQL Server: SET SHOWPLAN_XML ON dry-run, catalog from sys.* views,
                SQLCancel + KILL <spid> on abort, query timeout, row cap, optional read-only login.
* simulation  - ``use_simulation = true``: deterministic demo data, no database needed.

In ``--serve`` mode nothing runs until the Core pushed a configuration (``reinit``); a plugin
can therefore never silently fall back to fake data.
"""

import contextlib
import json
import math
import os
import re
import sys
import threading
import time
import uuid

try:
    from defusedxml.ElementTree import fromstring as safe_xml_fromstring
except ImportError:
    from xml.etree.ElementTree import fromstring as safe_xml_fromstring  # type: ignore[no-redef]  # nosec B314
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from datetime import time as dt_time
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal

# Ensure project root is in sys.path when executed as standalone subprocess
_root_dir = str(Path(__file__).resolve().parent.parent.parent)
if _root_dir not in sys.path:
    sys.path.insert(0, _root_dir)

from plugins.plugin_contract import (
    AbortParams,
    AbortResult,
    ColumnSchema,
    DryRunParams,
    DryRunResult,
    ExecuteParams,
    ExecuteResult,
    IndexSchema,
    IPluginAdapter,
    JsonRpcErrorPayload,
    JsonRpcRequest,
    JsonRpcResponse,
    PartitionSchema,
    ReinitParams,
    ReinitResult,
    SyncKnowledgeParams,
    SyncKnowledgeResult,
    TableSchema,
)
from plugins.sql_inspector import classify_query, is_unbounded_scan, joins_tables, statement_count

DEFAULT_DRIVER = "ODBC Driver 18 for SQL Server"
DEFAULT_MAX_ROWS = 1000
DEFAULT_MAX_CELL_CHARS = 10_000
TABLES_PER_PARTITION = 40
SHOWPLAN_NS = "{http://schemas.microsoft.com/sqlserver/2004/07/showplan}"
_SAFE_CONN_VALUE = re.compile(r"^[^;{}=\r\n]+$")
_SAFE_DRIVER = re.compile(r"^[A-Za-z0-9 ._()-]+$")


class PluginError(Exception):
    """Expected, user-presentable plugin failure (bad config, query error, aborted...)."""


class MethodNotFoundError(Exception):
    """Unknown JSON-RPC method."""


def _truthy(value: Any) -> bool:
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def _int_cfg(cfg: Any, key: str, default: int, low: int, high: int) -> int:
    try:
        return max(low, min(high, int(cfg.get(key, default))))
    except (TypeError, ValueError):
        return default


def _odbc_braced(value: str) -> str:
    """Brace-escape a connection-string value so ``;`` ``{`` ``}`` ``=`` cannot inject attributes."""
    return "{" + value.replace("}", "}}") + "}"


def _jsonable(value: Any, max_chars: int = DEFAULT_MAX_CELL_CHARS) -> Any:
    """Convert a pyodbc cell into something json.dumps accepts."""
    if value is None or isinstance(value, bool | int | float):
        return value
    if isinstance(value, str):
        return value if len(value) <= max_chars else value[:max_chars] + "...[truncated]"
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime | date | dt_time):
        return value.isoformat()
    if isinstance(value, bytes | bytearray):
        head = bytes(value[:64]).hex()
        return f"0x{head}" + ("..." if len(value) > 64 else "")
    if isinstance(value, uuid.UUID):
        return str(value)
    return str(value)


@dataclass
class _ActiveExecution:
    """Bookkeeping for one in-flight execution (shared between execute and abort threads)."""

    execution_id: str
    cancel_event: threading.Event = field(default_factory=threading.Event)
    cancelled: bool = False
    conn: Any = None
    cursor: Any = None
    spid: int | None = None
    login_time: str | None = None


class SqlServerAdapter(IPluginAdapter):
    """Adapter for Microsoft SQL Server implementing the AegisGate ports."""

    def __init__(self, require_config: bool = False) -> None:
        # require_config=True (serve mode): refuse to work until the Core pushed a configuration.
        self._config: dict[str, Any] | None = None if require_config else {}
        self._lock = threading.Lock()
        self._active: dict[str, _ActiveExecution] = {}
        self._spid_counter: int = 50

    # ------------------------------------------------------------------ configuration

    def _cfg(self, override: dict[str, Any] | None = None) -> dict[str, Any]:
        if self._config is None and not override:
            raise PluginError("Plugin is not configured yet (no configuration received from the Core).")
        cfg: dict[str, Any] = dict(self._config or {})
        if override:
            cfg.update(override)
        return cfg

    @staticmethod
    def _is_simulation(cfg: dict[str, Any]) -> bool:
        if "use_simulation" in cfg:
            return _truthy(cfg["use_simulation"])
        return not cfg.get("server")  # legacy one-shot without any configuration -> demo data

    # ------------------------------------------------------------------ real backend plumbing

    @staticmethod
    def _pyodbc() -> Any:
        try:
            import pyodbc  # noqa: PLC0415 (lazy: simulation mode must work without the driver)
        except ImportError as exc:
            raise PluginError("pyodbc is not installed in the plugin environment (pip install pyodbc).") from exc
        return pyodbc

    def _conn_str(self, cfg: dict[str, Any], read_only: bool) -> str:
        server = str(cfg.get("server") or "").strip()
        database = str(cfg.get("database") or "").strip()
        driver = str(cfg.get("driver") or DEFAULT_DRIVER).strip()
        if not server or not database:
            raise PluginError("Configuration needs 'server' and 'database'.")
        for label, val in (("server", server), ("database", database)):
            if not _SAFE_CONN_VALUE.match(val):
                raise PluginError(f"Invalid characters in '{label}'.")
        if not _SAFE_DRIVER.match(driver):
            raise PluginError("Invalid ODBC driver name.")

        port = str(cfg.get("port") or "").strip()
        host = f"{server},{port}" if port.isdigit() else server
        parts = [f"DRIVER={{{driver}}}", f"SERVER={host}", f"DATABASE={database}", "APP=AegisGate"]

        if "windows" in str(cfg.get("auth_mode", "")).lower():
            parts.append("Trusted_Connection=yes")
        else:
            use_ro = read_only and bool(cfg.get("readonly_username"))
            user = str(cfg.get("readonly_username" if use_ro else "username") or "")
            pwd = str(cfg.get("readonly_password" if use_ro else "password") or "")
            if not user:
                raise PluginError("Configuration needs 'username' (or Windows authentication).")
            parts += [f"UID={_odbc_braced(user)}", f"PWD={_odbc_braced(pwd)}"]

        parts.append(f"Encrypt={'yes' if _truthy(cfg.get('encrypt', True)) else 'no'}")
        parts.append(f"TrustServerCertificate={'yes' if _truthy(cfg.get('trust_server_certificate', False)) else 'no'}")
        return ";".join(parts)

    def _connect(self, cfg: dict[str, Any], read_only: bool = False, autocommit: bool = False) -> Any:
        pyodbc = self._pyodbc()
        timeout = _int_cfg(cfg, "login_timeout", 10, 1, 60)
        try:
            return pyodbc.connect(self._conn_str(cfg, read_only), autocommit=autocommit, timeout=timeout)
        except pyodbc.Error as exc:
            raise PluginError(f"Cannot connect to SQL Server: {self._short_error(exc)}") from exc

    @staticmethod
    def _short_error(exc: BaseException) -> str:
        text = " ".join(str(a) for a in exc.args[1:]) if len(exc.args) > 1 else str(exc)
        return re.sub(r"\s+", " ", text).strip()[:400]

    # ------------------------------------------------------------------ Port 1: sync_knowledge

    def sync_knowledge(self, params: SyncKnowledgeParams) -> SyncKnowledgeResult:
        """Port 1: Extract structural metadata, partition it into chunks, and return catalog."""
        cfg = self._cfg(params.config or None)
        if self._is_simulation(cfg):
            return self._sim_sync_knowledge()

        conn = self._connect(cfg, read_only=True, autocommit=True)
        try:
            partitions = self._read_catalog(conn, cfg)
        except Exception as exc:
            if isinstance(exc, PluginError):
                raise
            raise PluginError(f"Catalog extraction failed: {self._short_error(exc)}") from exc
        finally:
            conn.close()

        return SyncKnowledgeResult(
            partitions=partitions,
            target_id=str(cfg.get("target_id") or "sqlserver_prod"),
            timestamp=datetime.now(UTC).isoformat(),
        )

    @staticmethod
    def _fmt_type(name: str, max_length: int, precision: int, scale: int) -> str:
        n = name.lower()
        upper = name.upper()
        if n in ("varchar", "char", "varbinary", "binary"):
            return f"{upper}({'MAX' if max_length == -1 else max_length})"
        if n in ("nvarchar", "nchar"):
            return f"{upper}({'MAX' if max_length == -1 else max_length // 2})"
        if n in ("decimal", "numeric"):
            return f"{upper}({precision},{scale})"
        if n in ("datetime2", "time", "datetimeoffset"):
            return f"{upper}({scale})"
        return upper

    def _read_catalog(self, conn: Any, cfg: dict[str, Any]) -> list[PartitionSchema]:
        cur = conn.cursor()
        max_tables = _int_cfg(cfg, "max_tables", 500, 1, 5000)

        cur.execute(
            "SELECT TOP (?) t.object_id, s.name, t.name FROM sys.tables t "
            "JOIN sys.schemas s ON s.schema_id = t.schema_id WHERE t.is_ms_shipped = 0 "
            "ORDER BY s.name, t.name",
            max_tables,
        )
        tables: dict[int, TableSchema] = {}
        for object_id, schema_name, table_name in cur.fetchall():
            tables[object_id] = TableSchema(name=table_name, schema_name=schema_name)

        cur.execute(
            "SELECT c.object_id, c.name, ty.name, c.max_length, c.precision, c.scale, c.is_nullable "
            "FROM sys.columns c JOIN sys.types ty ON ty.user_type_id = c.user_type_id "
            "JOIN sys.tables t ON t.object_id = c.object_id WHERE t.is_ms_shipped = 0 "
            "ORDER BY c.object_id, c.column_id"
        )
        columns: dict[tuple[int, str], ColumnSchema] = {}
        for object_id, col, type_name, max_len, prec, scale, nullable in cur.fetchall():
            table = tables.get(object_id)
            if table is None:
                continue
            column = ColumnSchema(
                name=col,
                data_type=self._fmt_type(type_name, max_len, prec, scale),
                is_nullable=bool(nullable),
            )
            columns[(object_id, col)] = column
            table.columns.append(column)

        cur.execute(
            "SELECT i.object_id, i.name, i.is_unique, i.is_primary_key, c.name "
            "FROM sys.indexes i "
            "JOIN sys.index_columns ic ON ic.object_id = i.object_id AND ic.index_id = i.index_id "
            "JOIN sys.columns c ON c.object_id = ic.object_id AND c.column_id = ic.column_id "
            "JOIN sys.tables t ON t.object_id = i.object_id "
            "WHERE i.type > 0 AND i.is_hypothetical = 0 AND ic.is_included_column = 0 AND t.is_ms_shipped = 0 "
            "ORDER BY i.object_id, i.index_id, ic.key_ordinal"
        )
        index_cols: dict[tuple[int, str], IndexSchema] = {}
        for object_id, idx_name, is_unique, is_pk, col in cur.fetchall():
            table = tables.get(object_id)
            if table is None or idx_name is None:
                continue
            key = (object_id, idx_name)
            if key not in index_cols:
                index_cols[key] = IndexSchema(name=idx_name, columns=[], is_unique=bool(is_unique))
                table.indexes.append(index_cols[key])
            index_cols[key].columns.append(col)
            if is_pk and (object_id, col) in columns:
                columns[(object_id, col)].is_primary_key = True

        # Optional enrichments: need extra permissions on some servers, never fatal.
        try:
            cur.execute(
                "SELECT object_id, SUM(row_count) FROM sys.dm_db_partition_stats "
                "WHERE index_id IN (0, 1) GROUP BY object_id"
            )
            for object_id, rows in cur.fetchall():
                if object_id in tables:
                    tables[object_id].row_count_estimate = int(rows)
        except Exception:
            pass
        try:
            cur.execute(
                "SELECT major_id, minor_id, CAST(value AS NVARCHAR(500)) FROM sys.extended_properties "
                "WHERE class = 1 AND name = 'MS_Description'"
            )
            for major_id, minor_id, text in cur.fetchall():
                if major_id in tables and minor_id == 0:
                    tables[major_id].description = text
        except Exception:
            pass

        by_schema: dict[str, list[TableSchema]] = {}
        for table in tables.values():
            by_schema.setdefault(table.schema_name, []).append(table)

        database = str(cfg.get("database"))
        partitions: list[PartitionSchema] = []
        for schema_name, items in by_schema.items():
            chunks = [items[i : i + TABLES_PER_PARTITION] for i in range(0, len(items), TABLES_PER_PARTITION)]
            for n, chunk in enumerate(chunks, start=1):
                suffix = "" if len(chunks) == 1 else f" (part {n})"
                partitions.append(
                    PartitionSchema(
                        partition_key=schema_name if n == 1 else f"{schema_name}_{n}",
                        title=f"{database}.{schema_name} schema{suffix}",
                        tables=chunk,
                    )
                )
        return partitions

    # ------------------------------------------------------------------ Port 2: dry_run

    @staticmethod
    def _rule_violations(query: str, rules: list[dict[str, Any]]) -> list[str]:
        violations: list[str] = []
        if statement_count(query) > 1:
            violations.append("Plugin Rule Violation: Multiple SQL statements in one submission are not allowed.")
        for rule in rules:
            rtype = rule.get("rule_type")
            if rtype == "FORBID_JOIN":
                tables = [t.strip().upper() for t in str(rule.get("expression", "")).split(",") if t.strip()]
                if len(tables) >= 2 and joins_tables(query, tables):
                    violations.append(
                        f"Plugin Rule Violation: Forbidden JOIN between {', '.join(tables)}. Detected in SQL query."
                    )
            elif rtype == "FORBID_TABLE_SCAN" and is_unbounded_scan(query):
                violations.append(
                    "Plugin Rule Violation: Query lacks a meaningful WHERE clause and will trigger a full Table Scan on SQL Server."
                )
        return violations

    def dry_run(self, params: DryRunParams) -> DryRunResult:
        """Port 2: Inspect plan (SET SHOWPLAN_XML ON, nothing is executed) and check rules."""
        cfg = self._cfg()
        query = params.query
        query_type = classify_query(query)
        violations = self._rule_violations(query, params.rules)

        if self._is_simulation(cfg):
            return self._sim_dry_run(query, query_type, violations)

        plan = self._showplan(cfg, query)
        limit = cfg.get("max_estimated_cost")
        try:
            limit_value = float(limit) if limit not in (None, "") else 0.0
        except (TypeError, ValueError):
            limit_value = 0.0
        if limit_value > 0 and plan.get("EstimatedTotalSubtreeCost", 0.0) > limit_value:
            violations.append(
                f"Plugin Rule Violation: Estimated plan cost {plan['EstimatedTotalSubtreeCost']:.2f} exceeds the limit {limit_value:.2f}."
            )

        return DryRunResult(
            is_valid=not violations,
            violations=violations,
            explain_plan=plan,
            estimated_time_ms=0.0,
            query_type=query_type,
        )

    def _showplan(self, cfg: dict[str, Any], query: str) -> dict[str, Any]:
        conn = self._connect(cfg, read_only=True, autocommit=True)
        docs: list[str] = []
        try:
            conn.timeout = 15
            cur = conn.cursor()
            cur.execute("SET SHOWPLAN_XML ON")  # must be alone in its batch
            try:
                cur.execute(query)  # compiled only: the statement is NOT executed
                while True:
                    if cur.description:
                        docs.extend(str(r[0]) for r in cur.fetchall())
                    if not cur.nextset():
                        break
            finally:
                with contextlib.suppress(Exception):
                    cur.execute("SET SHOWPLAN_XML OFF")
        except Exception as exc:
            if isinstance(exc, PluginError):
                raise
            raise PluginError(
                f"Dry-run (SHOWPLAN) failed: {self._short_error(exc)}. "
                "The login needs the SHOWPLAN permission and the statement must compile."
            ) from exc
        finally:
            conn.close()
        return self._summarize_showplan(docs)

    @staticmethod
    def _summarize_showplan(docs: list[str]) -> dict[str, Any]:
        total_cost = 0.0
        est_rows: float | None = None
        stmt_type = "UNKNOWN"
        ops: list[dict[str, Any]] = []
        warnings: set[str] = set()
        missing_indexes = 0
        for doc in docs:
            try:
                root = safe_xml_fromstring(doc)  # nosec B314
            except Exception:
                continue
            for stmt in root.iter(f"{SHOWPLAN_NS}StmtSimple"):
                if stmt_type == "UNKNOWN":
                    stmt_type = stmt.get("StatementType", "UNKNOWN")
                try:
                    total_cost += float(stmt.get("StatementSubTreeCost", 0) or 0)
                    if est_rows is None:
                        est_rows = float(stmt.get("StatementEstRows", 0) or 0)
                except ValueError:
                    pass
            for relop in root.iter(f"{SHOWPLAN_NS}RelOp"):
                if len(ops) >= 50:
                    break
                entry: dict[str, Any] = {
                    "PhysicalOp": relop.get("PhysicalOp"),
                    "LogicalOp": relop.get("LogicalOp"),
                    "EstimateRows": relop.get("EstimateRows"),
                }
                obj = next(relop.iter(f"{SHOWPLAN_NS}Object"), None)
                if obj is not None:
                    entry["Object"] = ".".join(x for x in (obj.get("Schema"), obj.get("Table"), obj.get("Index")) if x)
                ops.append(entry)
            for w in root.iter(f"{SHOWPLAN_NS}Warnings"):
                warnings.update(child.tag.replace(SHOWPLAN_NS, "") for child in w)
            missing_indexes += sum(1 for _ in root.iter(f"{SHOWPLAN_NS}MissingIndex"))

        raw = "\n".join(docs)
        return {
            "Source": "SET SHOWPLAN_XML ON",
            "StatementType": stmt_type,
            "EstimatedTotalSubtreeCost": round(total_cost, 6),
            "EstimatedRows": est_rows,
            "QueryPlan": {"RelOp": ops, "Warnings": sorted(warnings) or None, "MissingIndexes": missing_indexes},
            "ShowplanXML": raw if len(raw) <= 20_000 else raw[:20_000] + "...[truncated]",
        }

    # ------------------------------------------------------------------ Port 3: execute

    def execute(self, params: ExecuteParams) -> ExecuteResult:
        """Port 3: Execute query under strict timeout guard, track SPID and return results."""
        cfg = self._cfg()
        rec = _ActiveExecution(execution_id=params.execution_id)
        with self._lock:
            if params.execution_id in self._active:
                raise PluginError(f"Execution '{params.execution_id}' is already running.")
            self._active[params.execution_id] = rec
        try:
            if self._is_simulation(cfg):
                return self._sim_execute(params, rec)
            return self._real_execute(cfg, params, rec)
        finally:
            with self._lock:
                self._active.pop(params.execution_id, None)

    def _real_execute(self, cfg: dict[str, Any], params: ExecuteParams, rec: _ActiveExecution) -> ExecuteResult:
        pyodbc = self._pyodbc()
        started = time.perf_counter()
        max_rows = _int_cfg(cfg, "max_rows", DEFAULT_MAX_ROWS, 1, 100_000)
        max_chars = _int_cfg(cfg, "max_cell_chars", DEFAULT_MAX_CELL_CHARS, 20, 1_000_000)
        conn = None
        try:
            conn = self._connect(cfg, read_only=params.read_only, autocommit=False)
            rec.conn = conn
            self._raise_if_cancelled(rec)
            # Server-side query timeout is only a backstop (e.g. the Core died): it is deliberately a
            # little longer than the Core's guard so the Core's abort path is the one that normally fires.
            conn.timeout = max(1, math.ceil(params.timeout_seconds)) + 2

            cur = conn.cursor()
            rec.cursor = cur
            cur.execute(
                "SELECT @@SPID, CONVERT(varchar(33), "
                "(SELECT login_time FROM sys.dm_exec_sessions WHERE session_id = @@SPID), 126)"
            )
            row = cur.fetchone()
            rec.spid = int(row[0])
            rec.login_time = row[1]
            cur.fetchall()
            self._raise_if_cancelled(rec)

            cur.execute(params.query)
            data, truncated, affected = self._read_results(cur, max_rows, max_chars)

            if params.read_only:
                conn.rollback()  # READ queries never persist anything, whatever they contained
            else:
                conn.commit()

            return ExecuteResult(
                data=data,
                rows_affected=len(data) if data else affected,
                execution_time_ms=round((time.perf_counter() - started) * 1000, 2),
                spid=rec.spid,
                truncated=truncated,
            )
        except PluginError:
            self._safe_rollback(conn)
            raise
        except pyodbc.Error as exc:
            self._safe_rollback(conn)
            if rec.cancelled:
                raise PluginError(f"Execution '{params.execution_id}' was aborted.") from exc
            if exc.args and str(exc.args[0]) == "HYT00":
                raise PluginError(f"Query exceeded the {params.timeout_seconds:g}s timeout and was cancelled.") from exc
            raise PluginError(f"SQL Server error: {self._short_error(exc)}") from exc
        finally:
            for closer in (rec.cursor, conn):
                try:
                    if closer is not None:
                        closer.close()
                except Exception:
                    pass

    @staticmethod
    def _safe_rollback(conn: Any) -> None:
        try:
            if conn is not None:
                conn.rollback()
        except Exception:
            pass

    @staticmethod
    def _raise_if_cancelled(rec: _ActiveExecution) -> None:
        if rec.cancelled:
            raise PluginError(f"Execution '{rec.execution_id}' was aborted.")

    @staticmethod
    def _read_results(cur: Any, max_rows: int, max_chars: int) -> tuple[list[dict[str, Any]], bool, int]:
        """First result set (row-capped) + the largest rowcount of non-SELECT statements."""
        data: list[dict[str, Any]] = []
        truncated = False
        affected = 0
        have_rows = False
        while True:
            if cur.description:
                if not have_rows:
                    have_rows = True
                    names: list[str] = []
                    for col in cur.description:
                        name, n = col[0] or "column", 2
                        while name in names:
                            name, n = f"{col[0]}_{n}", n + 1
                        names.append(name)
                    fetched = cur.fetchmany(max_rows + 1)
                    if len(fetched) > max_rows:
                        truncated = True
                        fetched = fetched[:max_rows]
                    data = [{n: _jsonable(v, max_chars) for n, v in zip(names, r)} for r in fetched]
                    if truncated:
                        break
            elif cur.rowcount is not None and cur.rowcount > affected:
                affected = cur.rowcount
            if not cur.nextset():
                break
        return data, truncated, affected

    # ------------------------------------------------------------------ Port 4: abort

    def abort(self, params: AbortParams) -> AbortResult:
        """Port 4: stop a running execution - SQLCancel first, then KILL <spid> on a second connection."""
        with self._lock:
            rec = self._active.get(params.execution_id)
        if rec is None:
            return AbortResult(
                success=True,
                message=f"Session for {params.execution_id} already released or not found.",
            )

        rec.cancelled = True
        rec.cancel_event.set()  # wakes simulated waits
        cfg = self._cfg()
        if self._is_simulation(cfg):
            return AbortResult(
                success=True,
                message=f"Executed: KILL {rec.spid} (simulation); session for {params.execution_id} was terminated.",
            )

        actions: list[str] = []
        ok = False
        cursor = rec.cursor
        if cursor is not None:
            try:
                cursor.cancel()
                actions.append("ODBC cancel sent")
                ok = True
            except Exception as exc:
                actions.append(f"ODBC cancel failed ({self._short_error(exc)})")

        if rec.spid is not None and _truthy(cfg.get("kill_on_abort", True)):
            try:
                actions.append(self._kill_session(cfg, rec))
                ok = True
            except Exception as exc:
                actions.append(f"KILL {rec.spid} failed ({exc})")
        elif rec.spid is None:
            actions.append("query had not started yet; it will not run")
            ok = True

        return AbortResult(success=ok, message=f"{params.execution_id}: " + "; ".join(actions))

    def _kill_session(self, cfg: dict[str, Any], rec: _ActiveExecution) -> str:
        """KILL our own session only: verify spid + login_time first so a recycled SPID is never hit."""
        conn = self._connect(cfg, read_only=False, autocommit=True)
        try:
            cur = conn.cursor()
            cur.execute(
                "SELECT 1 FROM sys.dm_exec_sessions WHERE session_id = ? AND CONVERT(varchar(33), login_time, 126) = ?",
                rec.spid,
                rec.login_time,
            )
            if rec.spid is None:
                return "no session spid recorded"
            if cur.fetchone() is None:
                return f"session {rec.spid} already gone"
            cur.execute(f"KILL {int(rec.spid)}")  # int() - never interpolate anything else
            return f"KILL {int(rec.spid)} issued"
        finally:
            conn.close()

    # ------------------------------------------------------------------ Port 5 / health

    def reinit(self, params: ReinitParams) -> ReinitResult:
        """Port 5: store the new configuration and verify connectivity."""
        self._config = dict(params.config)
        cfg = self._config
        if self._is_simulation(cfg):
            return ReinitResult(
                success=True, message="Simulation mode active (no database connection).", status="active"
            )
        try:
            info = self._probe(cfg)
        except PluginError as exc:
            return ReinitResult(success=False, message=str(exc), status="error")
        return ReinitResult(
            success=True,
            message=f"Connected to {cfg.get('server')}/{cfg.get('database')} as {info['login']}",
            status="active",
        )

    def _probe(self, cfg: dict[str, Any]) -> dict[str, Any]:
        conn = self._connect(cfg, read_only=False, autocommit=True)
        try:
            cur = conn.cursor()
            cur.execute("SELECT @@VERSION, DB_NAME(), SUSER_SNAME()")
            version, db, login = cur.fetchone()
            return {"server_version": str(version).splitlines()[0], "database": db, "login": login}
        except Exception as exc:
            raise PluginError(f"Connected but test query failed: {self._short_error(exc)}") from exc
        finally:
            conn.close()

    def ping(self, config: dict[str, Any] | None = None) -> dict[str, Any]:
        cfg = self._cfg(config or None)
        if self._is_simulation(cfg):
            return {"status": "ok", "mode": "simulation"}
        return {"status": "ok", "mode": "sqlserver", **self._probe(cfg)}

    def shutdown(self) -> None:
        """Cancel everything still running (the Core closed our stdin)."""
        with self._lock:
            records = list(self._active.values())
        for rec in records:
            rec.cancelled = True
            rec.cancel_event.set()
            try:
                if rec.cursor is not None:
                    rec.cursor.cancel()
            except Exception:
                pass

    # ------------------------------------------------------------------ simulation backend

    def _sim_sync_knowledge(self) -> SyncKnowledgeResult:
        orders_table = TableSchema(
            name="Orders",
            schema_name="dbo",
            columns=[
                ColumnSchema(name="OrderID", data_type="BIGINT", is_nullable=False, is_primary_key=True),
                ColumnSchema(name="CustomerID", data_type="INT", is_nullable=False),
                ColumnSchema(name="OrderDate", data_type="DATETIME2", is_nullable=False),
                ColumnSchema(name="TotalAmount", data_type="DECIMAL(18,2)", is_nullable=False),
                ColumnSchema(name="Status", data_type="VARCHAR(20)", is_nullable=False),
            ],
            indexes=[
                IndexSchema(name="PK_Orders", columns=["OrderID"], is_unique=True),
                IndexSchema(name="IX_Orders_OrderDate", columns=["OrderDate"], is_unique=False),
                IndexSchema(name="IX_Orders_Customer", columns=["CustomerID"], is_unique=False),
            ],
            row_count_estimate=1250000,
            description="Core customer order transactions",
        )
        order_items_table = TableSchema(
            name="OrderItems",
            schema_name="dbo",
            columns=[
                ColumnSchema(name="OrderItemID", data_type="BIGINT", is_nullable=False, is_primary_key=True),
                ColumnSchema(name="OrderID", data_type="BIGINT", is_nullable=False),
                ColumnSchema(name="ProductID", data_type="INT", is_nullable=False),
                ColumnSchema(name="Quantity", data_type="INT", is_nullable=False),
                ColumnSchema(name="UnitPrice", data_type="DECIMAL(18,2)", is_nullable=False),
            ],
            indexes=[
                IndexSchema(name="PK_OrderItems", columns=["OrderItemID"], is_unique=True),
                IndexSchema(name="IX_OrderItems_OrderID", columns=["OrderID"], is_unique=False),
            ],
            row_count_estimate=4500000,
            description="Order line items breakdown",
        )
        products_table = TableSchema(
            name="Products",
            schema_name="dbo",
            columns=[
                ColumnSchema(name="ProductID", data_type="INT", is_nullable=False, is_primary_key=True),
                ColumnSchema(name="SKU", data_type="VARCHAR(50)", is_nullable=False),
                ColumnSchema(name="Name", data_type="NVARCHAR(200)", is_nullable=False),
                ColumnSchema(name="Price", data_type="DECIMAL(18,2)", is_nullable=False),
                ColumnSchema(name="CurrentStock", data_type="INT", is_nullable=False),
            ],
            indexes=[
                IndexSchema(name="PK_Products", columns=["ProductID"], is_unique=True),
                IndexSchema(name="UX_Products_SKU", columns=["SKU"], is_unique=True),
            ],
            row_count_estimate=25000,
            description="Catalog products inventory",
        )
        audit_table = TableSchema(
            name="AuditLogs",
            schema_name="dbo",
            columns=[
                ColumnSchema(name="LogID", data_type="BIGINT", is_nullable=False, is_primary_key=True),
                ColumnSchema(name="EventTime", data_type="DATETIME2", is_nullable=False),
                ColumnSchema(name="Action", data_type="VARCHAR(50)", is_nullable=False),
                ColumnSchema(name="RawPayload", data_type="NVARCHAR(MAX)", is_nullable=True),
            ],
            indexes=[
                IndexSchema(name="PK_AuditLogs", columns=["LogID"], is_unique=True),
                IndexSchema(name="IX_AuditLogs_EventTime", columns=["EventTime"], is_unique=False),
            ],
            row_count_estimate=50000000,
            description="Heavy audit trail partition - DO NOT JOIN WITHOUT PARTITION PRUNING",
        )
        return SyncKnowledgeResult(
            partitions=[
                PartitionSchema(
                    partition_key="Sales", title="Sales & Orders Subsystem", tables=[orders_table, order_items_table]
                ),
                PartitionSchema(
                    partition_key="Inventory", title="Warehouse & Inventory Subsystem", tables=[products_table]
                ),
                PartitionSchema(partition_key="Finance", title="Finance & Audit Logs Subsystem", tables=[audit_table]),
            ],
            target_id="sqlserver_prod",
            timestamp=datetime.now(UTC).isoformat(),
        )

    def _sim_dry_run(self, query: str, query_type: Literal["READ", "WRITE"], violations: list[str]) -> DryRunResult:
        normalized = query.upper()
        is_safe = len(violations) == 0
        operators: list[dict[str, Any]] = []
        if "JOIN" in normalized:
            operators.append({"PhysicalOp": "Hash Match", "LogicalOp": "Inner Join", "EstimateRows": 15000})

        target_obj = "[dbo].[Orders].[PK_Orders]"
        if "PRODUCT" in normalized:
            target_obj = "[dbo].[Products].[PK_Products]"
        elif "AUDIT" in normalized:
            target_obj = "[dbo].[AuditLogs].[PK_AuditLogs]"

        if not is_unbounded_scan(query):
            operators.append({"PhysicalOp": "Clustered Index Seek", "Object": target_obj})
        else:
            operators.append({"PhysicalOp": "Clustered Index Scan", "Object": target_obj})

        explain_plan = {
            "Source": "SIMULATION (no database connected)",
            "StatementText": query,
            "StatementType": query_type,
            "OptimizationLevel": "FULL",
            "EstimatedTotalSubtreeCost": 0.084 if is_safe else 14.52,
            "EstimatedRows": 150 if is_safe else 500000,
            "QueryPlan": {"RelOp": operators, "Warnings": violations if violations else None},
        }
        return DryRunResult(
            is_valid=is_safe,
            violations=violations,
            explain_plan=explain_plan,
            estimated_time_ms=15.0 if is_safe else 1500.0,
            query_type=query_type,
        )

    def _sim_execute(self, params: ExecuteParams, rec: _ActiveExecution) -> ExecuteResult:
        start_time = time.perf_counter()
        with self._lock:
            self._spid_counter += 1
            rec.spid = self._spid_counter

        norm_q = params.query.upper()
        if ("WAITFOR DELAY" in norm_q or "SIMULATE_TIMEOUT" in norm_q) and rec.cancel_event.wait(
            params.timeout_seconds + 1.0
        ):
            raise PluginError(f"Execution '{params.execution_id}' was aborted.")

        if rec.cancel_event.wait(0.05):  # simulated 50ms database roundtrip
            raise PluginError(f"Execution '{params.execution_id}' was aborted.")
        duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

        if "PRODUCT" in norm_q:
            sample_rows = [
                {
                    "ProductID": 101,
                    "SKU": "SRV-42U-PRO",
                    "Name": "Enterprise Server Rack 42U",
                    "Price": 1299.99,
                    "CurrentStock": 18,
                },
                {
                    "ProductID": 102,
                    "SKU": "SW-48G-L3",
                    "Name": "Managed Gigabit Switch 48-Port",
                    "Price": 549.50,
                    "CurrentStock": 45,
                },
                {
                    "ProductID": 103,
                    "SKU": "CBL-CAT6A-2M",
                    "Name": "Cat6A Shielded Patch Cable 2m",
                    "Price": 14.99,
                    "CurrentStock": 350,
                },
                {
                    "ProductID": 104,
                    "SKU": "SFP-10G-SR",
                    "Name": "10GBASE-SR SFP+ Optical Transceiver",
                    "Price": 79.00,
                    "CurrentStock": 120,
                },
            ]
        elif "AUDIT" in norm_q:
            sample_rows = [
                {
                    "LogID": 9001,
                    "EventTime": "2026-10-22T08:00:15",
                    "Action": "LOGIN_SUCCESS",
                    "RawPayload": "User sa logged in from 10.0.1.5",
                },
                {
                    "LogID": 9002,
                    "EventTime": "2026-10-22T08:15:22",
                    "Action": "SCHEMA_AUDIT",
                    "RawPayload": "Table dbo.Products read by AI Agent",
                },
            ]
        else:
            sample_rows = [
                {
                    "OrderID": 1001,
                    "CustomerID": 42,
                    "OrderDate": "2026-10-21T09:30:00",
                    "TotalAmount": 450.00,
                    "Status": "Completed",
                },
                {
                    "OrderID": 1002,
                    "CustomerID": 88,
                    "OrderDate": "2026-10-21T10:15:00",
                    "TotalAmount": 1280.50,
                    "Status": "Completed",
                },
                {
                    "OrderID": 1003,
                    "CustomerID": 15,
                    "OrderDate": "2026-10-21T11:00:00",
                    "TotalAmount": 89.99,
                    "Status": "Pending",
                },
            ]

        return ExecuteResult(
            data=sample_rows,
            rows_affected=len(sample_rows),
            execution_time_ms=duration_ms,
            spid=rec.spid,
        )


# ---------------------------------------------------------------------- JSON-RPC plumbing


def _dispatch(adapter: SqlServerAdapter, method: str, params: dict[str, Any]) -> Any:
    if method == "sync_knowledge":
        return adapter.sync_knowledge(SyncKnowledgeParams.model_validate(params)).model_dump()
    if method == "dry_run":
        return adapter.dry_run(DryRunParams.model_validate(params)).model_dump()
    if method == "execute":
        return adapter.execute(ExecuteParams.model_validate(params)).model_dump()
    if method == "abort":
        return adapter.abort(AbortParams.model_validate(params)).model_dump()
    if method == "reinit":
        return adapter.reinit(ReinitParams.model_validate(params)).model_dump()
    if method == "ping":
        return adapter.ping(params.get("config") or None)
    raise MethodNotFoundError(method)


def _error_response(req_id: Any, exc: Exception) -> JsonRpcResponse:
    if isinstance(exc, MethodNotFoundError):
        return JsonRpcResponse(id=req_id, error=JsonRpcErrorPayload(code=-32601, message=f"Method '{exc}' not found"))
    return JsonRpcResponse(id=req_id, error=JsonRpcErrorPayload(code=-32000, message=str(exc)))


def handle_stdio_jsonrpc() -> None:
    """Legacy one-shot mode: read one JSON-RPC request from stdin, answer, exit."""
    adapter = SqlServerAdapter()
    raw_input = sys.stdin.read().strip()
    if not raw_input:
        return

    req_id: Any | None = None
    try:
        req = JsonRpcRequest.model_validate(json.loads(raw_input))
        req_id = req.id
        resp = JsonRpcResponse(result=_dispatch(adapter, req.method, req.params), id=req_id)
    except Exception as exc:
        resp = _error_response(req_id, exc)
    print(resp.model_dump_json())
    sys.stdout.flush()


def serve_forever() -> None:
    """Persistent mode: newline-delimited JSON-RPC, concurrent handling, runs until stdin closes."""
    adapter = SqlServerAdapter(require_config=True)
    out = sys.stdout
    sys.stdout = sys.stderr  # stray prints from libraries must never corrupt the RPC channel
    write_lock = threading.Lock()
    pool = ThreadPoolExecutor(
        max_workers=_int_cfg(os.environ, "AEGISGATE_PLUGIN_THREADS", 16, 2, 128), thread_name_prefix="rpc"
    )

    def respond(resp: JsonRpcResponse) -> None:
        with write_lock:
            out.write(resp.model_dump_json() + "\n")
            out.flush()

    def handle(line: str) -> None:
        req_id: Any | None = None
        try:
            req = JsonRpcRequest.model_validate(json.loads(line))
            req_id = req.id
            respond(JsonRpcResponse(result=_dispatch(adapter, req.method, req.params), id=req_id))
        except Exception as exc:
            respond(_error_response(req_id, exc))

    try:
        for raw in sys.stdin:
            line = raw.strip()
            if not line:
                continue
            try:
                is_abort = json.loads(line).get("method") == "abort"
            except (json.JSONDecodeError, AttributeError):
                is_abort = False
            if is_abort:
                # Never queue an abort behind busy workers: it gets its own thread.
                threading.Thread(target=handle, args=(line,), name="abort", daemon=True).start()
            else:
                pool.submit(handle, line)
    except KeyboardInterrupt:
        pass
    finally:
        adapter.shutdown()
        pool.shutdown(wait=False, cancel_futures=True)


if __name__ == "__main__":
    if "--serve" in sys.argv[1:]:
        serve_forever()
    else:
        handle_stdio_jsonrpc()
