"""Governance Rule Engine for validating AI queries against platform rules.

Adheres strictly to python_clean_code.md:
- 100% Type Hints
- Clean rule matching logic
"""

import re
from typing import Any

from core.database import Rule


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
        normalized_query = query.upper()
        plan_str = str(explain_plan).upper() if explain_plan else ""

        for rule in rules:
            if not rule.is_active:
                continue

            rule_type = rule.rule_type.upper()

            if rule_type == "FORBID_JOIN":
                # Expression format: "TableA,TableB"
                tables = [t.strip().upper() for t in rule.expression.split(",") if t.strip()]
                if len(tables) >= 2:
                    # Check if query or plan references both prohibited entities
                    all_present = all(
                        (re.search(rf"\b{re.escape(tbl)}\b", normalized_query) is not None)
                        or (tbl in plan_str)
                        for tbl in tables
                    )
                    if all_present:
                        violations.append(
                            f"Rule Violation [{rule.id}]: Prohibited JOIN between {', '.join(tables)}. {rule.description}"
                        )

            elif rule_type == "FORBID_TABLE_SCAN":
                # Check for full table scan indicators in explain plan or query without WHERE
                if "TABLE SCAN" in plan_str or "INDEX SCAN" in plan_str:
                    violations.append(
                        f"Rule Violation [{rule.id}]: Full table scan detected in plan. {rule.description}"
                    )
                elif "SELECT" in normalized_query and "FROM" in normalized_query and "WHERE" not in normalized_query:
                    violations.append(
                        f"Rule Violation [{rule.id}]: Query performs unbounded scan without WHERE clause."
                    )

            elif rule_type == "CUSTOM":
                # Regex or keyword check
                pattern = rule.expression.strip()
                if pattern and re.search(pattern, query, re.IGNORECASE):
                    violations.append(
                        f"Rule Violation [{rule.id}]: Matched forbidden pattern '{pattern}'. {rule.description}"
                    )

        return violations

    @staticmethod
    def determine_query_type(query: str) -> str:
        """Heuristic to determine if query is READ or WRITE."""
        cleaned = query.strip().upper()
        write_keywords = ("INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE", "MERGE")
        for kw in write_keywords:
            if cleaned.startswith(kw) or re.search(rf"\b{kw}\b", cleaned):
                return "WRITE"
        return "READ"

