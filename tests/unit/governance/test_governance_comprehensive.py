"""Comprehensive unit tests for GovernanceEngine rule evaluation and pattern validation."""

import pytest

from core.database import Rule
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
