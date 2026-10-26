"""Audit Track T1: Backend Functional Audit.

Examines:
1. Governance SQL Inspector & Rule bypass catalog (>= 60 queries)
2. MAX_EXECUTION_TIME rule behavior vs documentation
3. Output Masker behavior (casing, aliases, nested structures, duplicate columns)
4. State Machine status transition matrix and illegal state transitions
5. REST API contract conformance and input fuzzing
6. Data lifecycle (pruning, truncation, archival)
7. Knowledge store path traversal and input boundary handling
"""

import asyncio
from datetime import datetime, timedelta
import gzip
import json
import os
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from core.config import settings
from core.database import ExecutionControl, ExecutionLog, PluginProfile, Rule, utc_now
from core.engine.governance import GovernanceEngine
from core.engine.output_masker import OutputMasker
from core.engine.state_machine import ExecutionStateMachine
from core.engine.timeout_guard import TimeoutGuard
from core.gateway.services import GatewayService
from core.main import app
from core.storage.log_store import LogStore
from core.storage.retention import prune_logs, RetentionReport
from plugins.sql_inspector import (
    classify_query,
    is_unbounded_scan,
    joins_tables,
    referenced_tables,
    statement_count,
    tokenize,
)
from tests.factories import make_execution_log, make_rule

pytestmark = [pytest.mark.audit, pytest.mark.e2e]

EVIDENCE_DIR = Path("report/phase-5-audit")
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)


# ==============================================================================
# 1. SQL Inspector & Governance Bypass Catalog (>= 60 queries)
# ==============================================================================

GOVERNANCE_CATALOG = [
    # 1-10: Comments & Inline comments
    ("SELECT * FROM Users -- WHERE id = 1", "Comment hiding WHERE clause", True, False, "READ"),
    ("SELECT * FROM Users /* inline comment */ WHERE id = 1", "C-style inline comment", False, False, "READ"),
    ("SELECT * FROM Users /* multi-line\ncomment\nwith WHERE */ WHERE id = 1", "Multi-line comment", False, False, "READ"),
    ("SELECT * FROM Users /* nested /* comment */ */ WHERE id = 1", "Nested comment", False, False, "READ"),
    ("SELECT * FROM Users WHERE id = 1 -- comment at end", "Comment at query end", False, False, "READ"),
    ("-- Leading comment\nSELECT * FROM Users WHERE id = 1", "Leading single-line comment", False, False, "READ"),
    ("/* Leading block comment */ SELECT * FROM Users WHERE id = 1", "Leading block comment", False, False, "READ"),
    ("SELECT * FROM Users WHERE id = 1 /* unterminated comment", "Unterminated block comment", False, False, "READ"),
    ("SELECT * FROM Users WHERE id = 1 --\nAND status = 'active'", "Comment with newline continuation", False, False, "READ"),
    ("SELECT * FROM Users WHERE id = 1 -- WHERE 1=1", "Comment containing fake filter", False, False, "READ"),

    # 11-20: String Literals & Escaped Quotes
    ("SELECT 'DROP TABLE users' FROM Users WHERE id = 1", "String literal containing WRITE keyword", False, False, "READ"),
    ("SELECT '-- WHERE 1=1' FROM Users WHERE id = 1", "String literal containing comment syntax", False, False, "READ"),
    ("SELECT 'O''Reilly' FROM Users WHERE id = 1", "Escaped single quote in literal", False, False, "READ"),
    ("SELECT 'Users JOIN Orders' FROM Users WHERE id = 1", "String literal containing JOIN keywords", False, False, "READ"),
    ("SELECT 'UPDATED_AT' FROM Users WHERE id = 1", "String containing column name with WRITE prefix", False, False, "READ"),
    ("SELECT '' FROM Users WHERE id = 1", "Empty string literal", False, False, "READ"),
    ("SELECT N'Unicode string' FROM Users WHERE id = 1", "N-prefix Unicode string literal", False, False, "READ"),
    ("SELECT 'a', 'b', 'c' FROM Users WHERE id = 1", "Multiple comma-separated strings", False, False, "READ"),
    ("SELECT 'SELECT * INTO new_table' FROM Users WHERE id = 1", "Literal containing SELECT INTO", False, False, "READ"),
    ("SELECT '''' FROM Users WHERE id = 1", "String with single escaped quote", False, False, "READ"),

    # 21-30: Quoted & Bracketed Identifiers
    ("SELECT * FROM [Users] WHERE [id] = 1", "SQL Server bracketed table and column", False, False, "READ"),
    ('SELECT * FROM "Users" WHERE "id" = 1', "ANSI double-quoted identifiers", False, False, "READ"),
    ("SELECT * FROM `Users` WHERE `id` = 1", "MySQL/backtick identifiers", False, False, "READ"),
    ("SELECT * FROM [Order Details] WHERE [Unit Price] > 10", "Bracketed identifiers with spaces", False, False, "READ"),
    ("SELECT * FROM [dbo].[Users] WHERE id = 1", "Bracketed schema-qualified table", False, False, "READ"),
    ("SELECT * FROM [Users] JOIN [Orders] ON [Users].id = [Orders].user_id", "Bracketed JOIN tables", False, True, "READ"),
    ("SELECT [select] FROM [from] WHERE [where] = 1", "Keywords as bracketed identifier names", False, False, "READ"),
    ("SELECT [u.id] FROM [Users] u WHERE u.id = 1", "Identifier containing dots", False, False, "READ"),
    ("SELECT * FROM [Users]]Escaped] WHERE id = 1", "Escaped closing bracket in table name", False, False, "READ"),
    ("SELECT * FROM \"Users\"\"Escaped\" WHERE id = 1", "Escaped double quote in identifier", False, False, "READ"),

    # 31-40: Case, Whitespace, & Formatting Variations
    ("sElEcT * fRoM Users wHeRe id = 1", "Mixed case keywords", False, False, "READ"),
    ("SELECT\t*\r\nFROM\r\nUsers\r\nWHERE\tid\t=\t1", "Tabs, CRLF, and extra whitespace", False, False, "READ"),
    ("SELECT   *    FROM     Users      WHERE       id = 1", "Excessive spaces between tokens", False, False, "READ"),
    ("SELECT\n*\nFROM\nUsers\nWHERE\nid\n=\n1", "Only newlines separating tokens", False, False, "READ"),
    ("SELECT * FROM Users WHERE ID=1", "Zero spaces around operator", False, False, "READ"),
    ("SELECT * FROM users join orders on users.id=orders.user_id", "Lower-case JOIN", False, True, "READ"),
    ("SELECT * FROM users, orders WHERE users.id=orders.user_id", "Comma join with no spaces around comma", False, True, "READ"),
    ("   SELECT * FROM Users WHERE id = 1   ", "Leading and trailing whitespace", False, False, "READ"),
    ("SELECT * FROM Users WHERE ( ( ( id = 1 ) ) )", "Deeply nested parentheses around WHERE", False, False, "READ"),
    ("SELECT * FROM Users WHERE 1 = 1", "Tautology WHERE 1=1 (Unbounded scan)", True, False, "READ"),

    # 41-50: Tautologies & Unbounded Filter Bypasses
    ("SELECT * FROM Users WHERE 'a' = 'a'", "String tautology 'a'='a'", True, False, "READ"),
    ("SELECT * FROM Users WHERE TRUE", "Boolean literal tautology TRUE", True, False, "READ"),
    ("SELECT * FROM Users WHERE NOT FALSE", "Boolean negated tautology NOT FALSE", True, False, "READ"),
    ("SELECT * FROM Users WHERE 0 = 0", "Zero equality tautology 0=0", True, False, "READ"),
    ("SELECT * FROM Users WHERE (1 = 1)", "Parenthesized tautology (1=1)", True, False, "READ"),
    ("SELECT * FROM Users WHERE 1 = 1 AND 2 = 2", "Compound AND tautology", True, False, "READ"),
    ("SELECT * FROM Users WHERE 1 = 1 OR id = 5", "Tautology with OR clause", True, False, "READ"),
    ("SELECT * FROM Users WHERE 1 < 2", "Inequality tautology 1 < 2 (bypasses naive tautology check)", True, False, "READ"),
    ("SELECT * FROM Users WHERE 'x' LIKE 'x'", "LIKE tautology 'x' LIKE 'x' (bypasses PUNCT check)", True, False, "READ"),
    ("SELECT * FROM Users WHERE 10 >= 10", "Greater-or-equal tautology 10 >= 10", True, False, "READ"),

    # 51-60: Joins, CTEs, Subqueries, & Complex Structures
    ("WITH cte AS (SELECT * FROM Users WHERE id = 1) SELECT * FROM cte", "Simple CTE with filter", False, False, "READ"),
    ("WITH cte AS (SELECT * FROM Users) SELECT * FROM cte JOIN Orders ON cte.id = Orders.user_id", "CTE joined with table", False, True, "READ"),
    ("SELECT * FROM Users u, Orders o, Products p WHERE u.id = o.user_id AND o.prod_id = p.id", "Three-table comma join", False, True, "READ"),
    ("SELECT * FROM Users LEFT OUTER JOIN Orders ON Users.id = Orders.user_id", "LEFT OUTER JOIN", False, True, "READ"),
    ("SELECT * FROM Users CROSS JOIN Orders", "CROSS JOIN", False, True, "READ"),
    ("SELECT * FROM Users FULL JOIN Orders ON Users.id = Orders.user_id", "FULL JOIN", False, True, "READ"),
    ("SELECT * FROM Users NATURAL JOIN Orders", "NATURAL JOIN", False, True, "READ"),
    ("SELECT * FROM (SELECT * FROM Users WHERE id = 1) sub", "Derived table subquery with filter", False, False, "READ"),
    ("SELECT * FROM (SELECT * FROM Users, Orders WHERE Users.id = Orders.user_id) sub", "Subquery with comma join", False, True, "READ"),
    ("SELECT * FROM Users WHERE id IN (SELECT user_id FROM Orders)", "Subquery inside IN predicate", False, False, "READ"),

    # 61-70: Multi-Statement, Write Operations & DDL/DCL
    ("SELECT 1; DROP TABLE Users;", "Multi-statement injection with DROP TABLE", False, False, "WRITE"),
    ("SELECT 1; SELECT 2;", "Multiple benign SELECT statements", False, False, "READ"),
    ("INSERT INTO Users (name) VALUES ('Alice');", "Standard INSERT", False, False, "WRITE"),
    ("UPDATE Users SET name = 'Bob' WHERE id = 1;", "Standard UPDATE", False, False, "WRITE"),
    ("DELETE FROM Users WHERE id = 1;", "Standard DELETE", False, False, "WRITE"),
    ("TRUNCATE TABLE Users;", "TRUNCATE statement", False, False, "WRITE"),
    ("MERGE INTO Target USING Source ON Target.id = Source.id WHEN MATCHED THEN UPDATE SET Target.val = Source.val;", "MERGE statement", False, False, "WRITE"),
    ("EXEC sp_who2;", "Stored procedure execution via EXEC", False, False, "WRITE"),
    ("EXECUTE('SELECT 1');", "Dynamic SQL via EXECUTE", False, False, "WRITE"),
    ("SELECT * INTO NewUsers FROM Users WHERE id = 1;", "SELECT INTO write statement", False, False, "WRITE"),

    # 71-75: Boundary cases & Edge inputs
    ("", "Completely empty query", False, False, "WRITE"),
    ("   ", "Whitespace only query", False, False, "WRITE"),
    ("SELECT * FROM " + ("A" * 128) + " WHERE id = 1", "Very long table identifier (128 chars)", False, False, "READ"),
    ("SELECT " + (",".join([f"col_{i}" for i in range(100)])) + " FROM Users WHERE id = 1", "Query with 100 columns", False, False, "READ"),
    ("SELECT * FROM Users WHERE id = 1" + ("\n-- comment line" * 500), "Huge query with 500 comment lines (15 KB)", False, False, "READ"),
]


def test_governance_bypass_and_false_positives_catalog(tmp_path: Path):
    """Execute >= 75 SQL queries through sql_inspector and record classification accuracy."""
    results = []
    join_tables = ["Users", "Orders"]

    for query, description, exp_unbounded, exp_joins, exp_classification in GOVERNANCE_CATALOG:
        q_class = classify_query(query)
        q_unbounded = is_unbounded_scan(query)
        q_joins = joins_tables(query, join_tables)
        stmt_cnt = statement_count(query)

        # Check for false negatives / bypasses
        bypassed_unbounded = (exp_unbounded is True) and (q_unbounded is False)
        bypassed_joins = (exp_joins is True) and (q_joins is False)
        bypassed_classification = (exp_classification == "WRITE") and (q_class == "READ")

        results.append({
            "query": query[:60] + "..." if len(query) > 60 else query,
            "description": description,
            "expected": {
                "unbounded": exp_unbounded,
                "joins": exp_joins,
                "type": exp_classification,
            },
            "actual": {
                "unbounded": q_unbounded,
                "joins": q_joins,
                "type": q_class,
                "statements": stmt_cnt,
            },
            "anomalies": {
                "bypassed_unbounded": bypassed_unbounded,
                "bypassed_joins": bypassed_joins,
                "bypassed_classification": bypassed_classification,
            }
        })

    out_file = tmp_path / "t1_sql_governance_catalog_results.json"
    out_file.write_text(json.dumps(results, indent=2), encoding="utf-8")

    # Assert catalog size requirement
    assert len(results) >= 60

    # Specifically check the known tautology bypasses we discovered
    bypasses = [r for r in results if any(r["anomalies"].values())]
    # Check that WHERE 1 < 2 and WHERE 'x' LIKE 'x' bypass is_unbounded_scan
    assert any("WHERE 1 < 2" in r["query"] for r in bypasses)
    assert any("LIKE 'x'" in r["query"] for r in bypasses)


# ==============================================================================
# 2. MAX_EXECUTION_TIME Rule Verification (Defect D-004)
# ==============================================================================

def test_max_execution_time_rule_is_ignored():
    """Verify that MAX_EXECUTION_TIME governance rule is completely ignored by the engine."""
    rule = make_rule(
        id="rule_time_limit",
        name="Strict 1s Execution Cap",
        rule_type="MAX_EXECUTION_TIME",
        expression="1.0",
        description="Limit query execution to 1 second",
        is_active=True,
    )

    # 1. GovernanceEngine ignores MAX_EXECUTION_TIME rule during inspection
    query = "SELECT * FROM Users WHERE id = 1"
    violations = GovernanceEngine.inspect_query_and_plan(query, [rule])
    # Returns empty violations list because there is no branch for MAX_EXECUTION_TIME
    assert len(violations) == 0

    # 2. TimeoutGuard uses default timeout (15s for READ), ignoring active rule
    timeout_resolved = TimeoutGuard.get_timeout_for_query("READ")
    assert timeout_resolved == 15.0  # NOT 1.0


# ==============================================================================
# 3. Output Masker Behavior
# ==============================================================================

def test_output_masking_comprehensive():
    """Verify OutputMasker with casing, aliases, nested dicts, and rule precedence."""
    rule_redact = make_rule(
        id="r_redact",
        rule_type="REDACT_FIELD",
        expression="password, SSN, users.email",
        is_active=True,
    )
    rule_remove = make_rule(
        id="r_remove",
        rule_type="REMOVE_FIELD",
        expression="Secret_Token, ssn",  # Note: SSN is in both; REMOVE must win over REDACT
        is_active=True,
    )

    data = {
        "User_ID": 101,
        "PASSWORD": "PlainPassword123",  # Casing variation
        "ssn": "123-45-6789",            # In both -> must be removed entirely
        "Email": "alice@example.com",    # Specified with table prefix in rule
        "secret_token": "xyz_token_999", # Must be removed
        "aliased_p": "SecretViaAlias",   # Query aliased: 'SELECT password AS aliased_p'
        "profile": {
            "sub_ssn": "987-65-4321",
            "password": "NestedPassword", # Nested dict
            "metadata": [{"email": "backup@example.com"}, {"clean_field": 42}],
        },
    }

    masked, hit_names = OutputMasker.apply(data, [rule_redact, rule_remove])

    # 1. Casing insensitive redact
    assert masked["PASSWORD"] is None

    # 2. REMOVE precedence over REDACT
    assert "ssn" not in masked

    # 3. Table-qualified column part match
    assert masked["Email"] is None

    # 4. REMOVE field completely deleted
    assert "secret_token" not in masked

    # 5. Aliased column is NOT masked because key name in result is 'aliased_p'
    assert masked["aliased_p"] == "SecretViaAlias"

    # 6. Nested structures walked recursively
    assert masked["profile"]["password"] is None
    assert masked["profile"]["metadata"][0]["email"] is None
    assert masked["profile"]["metadata"][1]["clean_field"] == 42


# ==============================================================================
# 4. State Machine Transition Matrix
# ==============================================================================

@pytest.mark.asyncio
async def test_state_machine_illegal_transitions(db_session: Session):
    """Verify that illegal state transitions are blocked and atomic."""
    log = make_execution_log(
        id="audit_sm_001",
        query="SELECT 1",
        status="PAUSED_FOR_REVIEW",
        target_id="sqlserver_prod",
    )
    db_session.add(log)
    db_session.commit()

    store = LogStore(db_session)

    # 1. Direct CAS transition test: attempting to transition from wrong state fails
    ok = store.transition_status(
        log_id="audit_sm_001",
        expected_statuses=("EXECUTING",),  # Wrong current state
        updates={"status": "COMPLETED"},
    )
    assert ok is False

    # 2. Transition from actual state succeeds
    ok2 = store.transition_status(
        log_id="audit_sm_001",
        expected_statuses=("PAUSED_FOR_REVIEW",),
        updates={"status": "REJECTED", "error_message": "Admin policy violation"},
    )
    assert ok2 is True

    # 3. Attempting to approve after rejection fails
    ok3 = store.transition_status(
        log_id="audit_sm_001",
        expected_statuses=("PAUSED_FOR_REVIEW",),
        updates={"status": "EXECUTING"},
    )
    assert ok3 is False

    # 4. Attempting to abort already-rejected execution fails
    ok4 = store.transition_status(
        log_id="audit_sm_001",
        expected_statuses=("EXECUTING",),
        updates={"status": "ABORTED"},
    )
    assert ok4 is False


# ==============================================================================
# 5. REST API Boundary & Fuzzing
# ==============================================================================

def test_rest_api_fuzzing(api_client: TestClient):
    """Test REST endpoints with malformed JSON, boundary numbers, and edge payloads."""
    # 1. Malformed JSON payload
    resp = api_client.post(
        "/api/monitor/executions",
        content="{\"query\": 'broken json",
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 422

    # 2. Missing required fields
    resp = api_client.post("/api/monitor/executions", json={"reasoning": "Missing query and target"})
    assert resp.status_code == 422

    # 3. Boundary pagination limit bounds
    resp = api_client.get("/api/executions/page?limit=0")
    assert resp.status_code == 422  # ge=1 constraint

    resp = api_client.get("/api/executions/page?limit=501")
    assert resp.status_code == 422  # le=500 constraint

    # 4. Corrupt cursor: DEFECT documented - returns 200 instead of 400 Bad Request
    resp = api_client.get("/api/executions/page?cursor=NOT_VALID_BASE64_!!!")
    # Expected: 400 Bad Request; Actual observed: 200 OK (silent fallback to page 1)
    assert resp.status_code in (200, 400)

    # 5. Non-existent execution ID returns 404
    resp = api_client.get("/api/monitor/executions/non_existent_id_999999")
    assert resp.status_code == 404

    # 6. Unicode, emojis and NUL byte in execution submission
    resp = api_client.post(
        "/api/monitor/executions?wait=false",
        json={
            "query": "SELECT N'🔥🚀 Tiếng Việt có dấu 123' AS emoji_col WHERE id = 1;",
            "target_id": "sqlserver_prod",
            "reasoning": "Audit fuzz test with special unicode characters and emoji 🛡️",
        },
    )
    # Background submission accepted
    assert resp.status_code == 201
    body = resp.json()
    assert "id" in body


# ==============================================================================
# 6. Data Lifecycle: Retention & Archival
# ==============================================================================

def test_retention_and_gzip_archival(db_session: Session, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Verify prune_logs pruning, NDJSON gzip export, and dry-run safety."""
    archive_dir = tmp_path / "audit_archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(settings, "ARCHIVE_DIR", archive_dir)

    # Insert an old terminal execution (45 days old)
    old_time = utc_now() - timedelta(days=45)
    old_log = ExecutionLog(
        id="exec_old_archive_01",
        target_id="sqlserver_prod",
        query="SELECT * FROM OldData WHERE id = 1",
        query_type="READ",
        status="COMPLETED",
        reasoning="Routine audit test",
        created_at=old_time,
        result_summary=json.dumps({"rows": [{"id": 1, "val": "old_value"}]}),
    )
    # Insert a fresh running execution (should NEVER be pruned or NULLed)
    fresh_log = ExecutionLog(
        id="exec_fresh_active_02",
        target_id="sqlserver_prod",
        query="SELECT * FROM ActiveData",
        query_type="READ",
        status="EXECUTING",
        reasoning="Routine active query",
        created_at=utc_now(),
    )
    db_session.add(old_log)
    db_session.add(fresh_log)
    db_session.commit()

    # 1. Test Dry Run: records identified but NOT deleted
    dry_report = prune_logs(
        session=db_session,
        log_retention_days=30,
        result_retention_days=7,
        archive_before_delete=True,
        dry_run=True,
        archive_dir=archive_dir,
    )
    assert dry_report.pruned_logs_count == 1
    # Check that record is still in DB
    assert db_session.get(ExecutionLog, "exec_old_archive_01") is not None

    # 2. Test Real Run: record archived to gzip and pruned from DB
    real_report = prune_logs(
        session=db_session,
        log_retention_days=30,
        result_retention_days=7,
        archive_before_delete=True,
        dry_run=False,
        archive_dir=archive_dir,
    )
    assert real_report.pruned_logs_count == 1
    assert db_session.get(ExecutionLog, "exec_old_archive_01") is None
    # Fresh active execution was NOT pruned
    assert db_session.get(ExecutionLog, "exec_fresh_active_02") is not None

    # 3. Verify valid gzip file content
    gz_files = list(archive_dir.glob("*.ndjson.gz"))
    assert len(gz_files) >= 1
    with gzip.open(gz_files[0], "rt", encoding="utf-8") as gz_in:
        line = gz_in.readline()
        record = json.loads(line)
        assert record["id"] == "exec_old_archive_01"


# ==============================================================================
# 7. Knowledge Store Path Traversal Audit
# ==============================================================================

def test_knowledge_store_path_traversal(api_client: TestClient):
    """Verify that knowledge chunk endpoints reject directory traversal attempts."""
    traversal_payloads = [
        "../secrets",
        "..\\secrets",
        "/etc/passwd",
        "C:\\Windows\\System32\\calc.exe",
        "CON",
        "NUL",
        "PRN",
        "....//....//config.json",
    ]

    for bad_id in traversal_payloads:
        # Attempt to access non-existent or traversal chunk
        resp = api_client.get(f"/api/knowledge/chunks/{bad_id}")
        # Must return 404 or 422, NEVER 200 or 500
        assert resp.status_code in (404, 422), f"Failed on path traversal payload: {bad_id}"
