"""Comprehensive unit tests for GovernanceEngine rule evaluation and pattern validation."""

from core.engine.governance import (
    GovernanceEngine,
    validate_custom_pattern,
    validate_rule_definition,
)
from tests.factories import make_rule


def test_validate_custom_pattern_edge_cases():
    """Verify validation of custom regex patterns including length and ReDoS shapes."""
    # 1. Valid safe pattern
    assert validate_custom_pattern(r"\bDROP\s+TABLE\b") is None

    # 2. Overly long pattern (> 200 chars)
    long_pattern = "a" * 201
    err = validate_custom_pattern(long_pattern)
    assert err is not None
    assert "longer than 200 characters" in err

    # 3. Invalid regex syntax
    err_syntax = validate_custom_pattern(r"[unclosed_bracket")
    assert err_syntax is not None
    assert "Invalid regular expression" in err_syntax

    # 4. Catastrophic backtracking / ReDoS nested quantifiers
    redos_patterns = [
        r"(a+)+",
        r"(a*)*",
        r"(a|b+)*",
        r"([a-z]+)+$",
    ]
    for pattern in redos_patterns:
        err_redos = validate_custom_pattern(pattern)
        assert err_redos is not None, f"Expected ReDoS detection for {pattern}"
        assert "nested quantifiers" in err_redos


def test_validate_rule_definition():
    """Verify validation of all rule types before persistence."""
    # Unknown rule type
    err = validate_rule_definition("FORBID_UNKNOWN", "expr")
    assert err is not None
    assert "Unknown rule_type" in err

    # CUSTOM without pattern
    assert "needs a pattern" in (validate_rule_definition("CUSTOM", "   ") or "")

    # FORBID_JOIN with fewer than 2 tables
    err_join = validate_rule_definition("FORBID_JOIN", "OnlyOneTable")
    assert err_join is not None
    assert "at least two comma-separated tables" in err_join

    # FORBID_JOIN valid
    assert validate_rule_definition("FORBID_JOIN", "Users,Secrets") is None

    # REDACT_FIELD / REMOVE_FIELD without fields
    assert "needs at least one field" in (validate_rule_definition("REDACT_FIELD", "") or "")
    assert "needs at least one field" in (validate_rule_definition("REMOVE_FIELD", "  ") or "")
    assert validate_rule_definition("REDACT_FIELD", "ssn,password") is None


def test_governance_engine_multiple_rules_and_priority():
    """Verify evaluation of multiple rules accumulates all violations."""
    rule1 = make_rule(
        id="rule_1",
        name="No Joins",
        rule_type="FORBID_JOIN",
        expression="Users,AuditLogs",
        description="Forbidden join",
    )
    rule2 = make_rule(
        id="rule_2",
        name="No Table Scan",
        rule_type="FORBID_TABLE_SCAN",
        expression="",
        description="No full scan",
    )
    rule3 = make_rule(
        id="rule_3",
        name="Forbid Truncate",
        rule_type="CUSTOM",
        expression=r"\bTRUNCATE\b",
        description="No truncate allowed",
    )
    rule4_inactive = make_rule(
        id="rule_4",
        name="Inactive Rule",
        rule_type="CUSTOM",
        expression=r"\bSELECT\b",
        is_active=False,
    )

    # Query triggers rule 1, rule 2 (unbounded), rule 3, but rule 4 is inactive
    query = "TRUNCATE TABLE Temp; SELECT * FROM Users, AuditLogs"
    # Note: query has 2 statements -> also triggers built-in multi-statement guard
    violations = GovernanceEngine.inspect_query_and_plan(
        query=query,
        rules=[rule1, rule2, rule3, rule4_inactive],
        explain_plan=None,
    )

    assert any("Multiple SQL statements" in v for v in violations)
    assert any("rule_1" in v for v in violations)
    assert any("rule_3" in v for v in violations)
    assert not any("rule_4" in v for v in violations)


def test_governance_table_scan_in_explain_plan():
    """Verify FORBID_TABLE_SCAN triggers when plan mentions TABLE SCAN or INDEX SCAN."""
    rule = make_rule(
        id="rule_scan",
        rule_type="FORBID_TABLE_SCAN",
        expression="",
        description="Scan forbidden in production",
    )

    # Query is bounded but plan reveals Table Scan
    query = "SELECT * FROM LargeTable WHERE Date > '2026-01-01'"
    plan_with_scan = {
        "PhysicalOp": "Clustered Index Scan",
        "EstimatedCost": 450.2,
    }

    violations = GovernanceEngine.inspect_query_and_plan(
        query=query,
        rules=[rule],
        explain_plan=plan_with_scan,
    )
    assert len(violations) == 1
    assert "rule_scan" in violations[0]
    assert "Full table scan detected in plan" in violations[0]


def test_governance_custom_pattern_fail_closed():
    """Verify that if an existing CUSTOM rule has an unusable pattern, it fails closed."""
    broken_rule = make_rule(
        id="broken_rule",
        rule_type="CUSTOM",
        expression=r"(evil+)+",  # ReDoS shape
        description="Broken ReDoS rule",
    )

    violations = GovernanceEngine.inspect_query_and_plan(
        query="SELECT 1",
        rules=[broken_rule],
    )
    assert len(violations) == 1
    assert "broken_rule" in violations[0]
    assert "unusable" in violations[0]


def test_governance_unicode_lookalike_normalization():
    """Verify full-width Unicode characters cannot bypass classification and rules."""
    from plugins.sql_inspector import classify_query, statement_count

    # Full-width DROP TABLE
    evil_query = "ＤＲＯＰ ＴＡＢＬＥ users"
    assert classify_query(evil_query) == "WRITE"

    # Full-width multi-statement
    evil_multi = "ＳＥＬＥＣＴ 1; ＤＲＯＰ ＴＡＢＬＥ users"
    assert statement_count(evil_multi) == 2


def test_governance_multi_statement_without_semicolon():
    """Verify queries with multiple un-delimited SQL statements are blocked."""
    from plugins.sql_inspector import statement_count

    query_no_semi = "SELECT * FROM users\nDROP TABLE orders"
    assert statement_count(query_no_semi) == 2

    violations = GovernanceEngine.inspect_query_and_plan(query=query_no_semi, rules=[])
    assert any("Multiple SQL statements" in v for v in violations)


def test_governance_tautology_and_constant_unbounded_scans():
    """Verify various tautology and constant condition bypasses are caught as unbounded scans."""
    from plugins.sql_inspector import is_unbounded_scan

    # Comparison tautologies
    assert is_unbounded_scan("SELECT * FROM users WHERE 1 < 2") is True
    assert is_unbounded_scan("SELECT * FROM users WHERE 2 > 1") is True
    assert is_unbounded_scan("SELECT * FROM users WHERE 1 <= 2") is True
    assert is_unbounded_scan("SELECT * FROM users WHERE 2 >= 1") is True
    assert is_unbounded_scan("SELECT * FROM users WHERE 5 = 5") is True
    assert is_unbounded_scan("SELECT * FROM users WHERE 'a' = 'a'") is True
    assert is_unbounded_scan("SELECT * FROM users WHERE 1 <> 2") is True

    # Pure constant expressions with no column references
    assert is_unbounded_scan("SELECT * FROM users WHERE 1 IS NOT NULL") is True
    assert is_unbounded_scan("SELECT * FROM users WHERE TRUE") is True

    # Legitimate bounded query referencing real columns
    assert is_unbounded_scan("SELECT * FROM users WHERE user_id = 42") is False
    assert is_unbounded_scan("SELECT * FROM users WHERE [Status] = 'active'") is False


def test_governance_custom_rule_comment_tricks():
    """Verify inline comments and unicode cannot bypass CUSTOM governance rules."""
    rule = make_rule(
        id="forbid_delete",
        rule_type="CUSTOM",
        expression=r"DELETE\s+FROM",
        description="Delete forbidden",
    )

    # 1. Inline comment trick DELETE/**/FROM
    comment_trick = "DELETE/**/FROM users WHERE id = 1"
    v1 = GovernanceEngine.inspect_query_and_plan(query=comment_trick, rules=[rule])
    assert any("forbid_delete" in v for v in v1)

    # 2. Unicode lookalike ＤＥＬＥＴＥ ＦＲＯＭ
    unicode_trick = "ＤＥＬＥＴＥ ＦＲＯＭ users WHERE id = 1"
    v2 = GovernanceEngine.inspect_query_and_plan(query=unicode_trick, rules=[rule])
    assert any("forbid_delete" in v for v in v2)
