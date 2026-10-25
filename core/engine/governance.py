"""Governance Rule Engine for validating AI queries against platform rules.

Adheres strictly to python_clean_code.md:
- 100% Type Hints
- Clean rule matching logic

Query text is analysed with the token-based ``plugins.sql_inspector`` (comments,
strings and quoted identifiers are ignored) instead of raw substring matching.
"""

import logging
import re
from typing import Any

from core.database import Rule
from plugins.sql_inspector import (
    classify_query,
    is_unbounded_scan,
    joins_tables,
    plan_mentions_table,
    statement_count,
)

logger = logging.getLogger(__name__)

RULE_TYPES: frozenset[str] = frozenset(
    {"FORBID_JOIN", "FORBID_TABLE_SCAN", "MAX_EXECUTION_TIME", "CUSTOM", "REDACT_FIELD", "REMOVE_FIELD"}
)
MAX_CUSTOM_PATTERN_LENGTH = 200
# Nested quantifiers such as (a+)+ , (a*)* , (a|b+)* are the classic catastrophic-backtracking shapes.
_NESTED_QUANTIFIER = re.compile(r"\((?:[^()\\]|\\.)*[+*](?:[^()\\]|\\.)*\)\s*(?:[+*]|\{\d*,\d*\})")


def validate_custom_pattern(pattern: str) -> str | None:
    """Return an error message if a CUSTOM regex is invalid or unsafe, else None."""
    if len(pattern) > MAX_CUSTOM_PATTERN_LENGTH:
        return f"Pattern longer than {MAX_CUSTOM_PATTERN_LENGTH} characters."
    if _NESTED_QUANTIFIER.search(pattern):
        return "Pattern contains nested quantifiers (risk of catastrophic backtracking)."
    try:
        re.compile(pattern)
    except re.error as exc:
        return f"Invalid regular expression: {exc}"
    return None


def validate_rule_definition(rule_type: str, expression: str) -> str | None:
    """Validate a rule before it is stored. Returns an error message or None."""
    kind = rule_type.upper()
    if kind not in RULE_TYPES:
        return f"Unknown rule_type '{rule_type}'. Allowed: {', '.join(sorted(RULE_TYPES))}."
    if kind == "CUSTOM":
        return validate_custom_pattern(expression.strip()) if expression.strip() else "CUSTOM rule needs a pattern."
    if kind == "FORBID_JOIN":
        tables = [t for t in expression.split(",") if t.strip()]
        return None if len(tables) >= 2 else "FORBID_JOIN needs at least two comma-separated tables."
    if kind in ("REDACT_FIELD", "REMOVE_FIELD"):
        return None if [f for f in expression.split(",") if f.strip()] else f"{kind} needs at least one field name."
    return None


class GovernanceEngine:
    """Evaluates active rules against query string and explain plan."""

    @staticmethod
    def inspect_query_and_plan(
        query: str,
        rules: list[Rule],
        explain_plan: Any | None = None,
    ) -> list[str]:
        """Check query text and explain plan against active governance rules.

        Returns a list of violation messages. Empty list means passed.
        """
        violations: list[str] = []
        plan_str = str(explain_plan) if explain_plan else ""

        # Built-in guard (always on): one statement per submission.
        if statement_count(query) > 1:
            violations.append("Rule Violation [builtin]: Multiple SQL statements in one submission are not allowed.")

        for rule in rules:
            if not rule.is_active:
                continue

            rule_type = rule.rule_type.upper()

            if rule_type == "FORBID_JOIN":
                # Expression format: "TableA,TableB"
                tables = [t.strip().upper() for t in rule.expression.split(",") if t.strip()]
                if len(tables) >= 2:
                    in_query = joins_tables(query, tables)
                    in_plan = all(plan_mentions_table(plan_str, tbl) for tbl in tables) and "JOIN" in plan_str.upper()
                    if in_query or in_plan:
                        violations.append(
                            f"Rule Violation [{rule.id}]: Prohibited JOIN between {', '.join(tables)}. {rule.description}"
                        )

            elif rule_type == "FORBID_TABLE_SCAN":
                plan_upper = plan_str.upper()
                if "TABLE SCAN" in plan_upper or "INDEX SCAN" in plan_upper:
                    violations.append(
                        f"Rule Violation [{rule.id}]: Full table scan detected in plan. {rule.description}"
                    )
                elif is_unbounded_scan(query):
                    violations.append(
                        f"Rule Violation [{rule.id}]: Query performs unbounded scan without a meaningful WHERE clause."
                    )

            elif rule_type == "CUSTOM":
                pattern = rule.expression.strip()
                if not pattern:
                    continue
                problem = validate_custom_pattern(pattern)
                if problem:
                    # Fail closed: a broken policy must not silently allow queries.
                    logger.error("CUSTOM rule %s is unusable: %s", rule.id, problem)
                    violations.append(f"Rule Violation [{rule.id}]: Rule pattern is unusable ({problem}).")
                elif re.search(pattern, query, re.IGNORECASE):
                    violations.append(
                        f"Rule Violation [{rule.id}]: Matched forbidden pattern '{pattern}'. {rule.description}"
                    )

        return violations

    @staticmethod
    def determine_query_type(query: str) -> str:
        """Token-based READ/WRITE classification (comments/strings/identifiers are ignored)."""
        return classify_query(query)
