"""Output Masker: blanks or removes configured fields from execution results.

Driven by governance rules (applied before the result is stored, broadcast, or
returned to the AI agent, so the raw value is never persisted):
- ``REDACT_FIELD``: keep the key, set its value to ``null`` ("làm rỗng")
- ``REMOVE_FIELD``: delete the key entirely ("xóa")

Rule expression: comma-separated field names, case-insensitive. ``table.column``
is accepted and matched on the column part. Nested dicts/lists are walked
recursively, so it also works for document stores (MongoDB).
"""

from typing import Any

from core.database import Rule

REDACT = "REDACT_FIELD"
REMOVE = "REMOVE_FIELD"


def _field_names(expression: str) -> set[str]:
    return {part.strip().split(".")[-1].strip().lower() for part in expression.split(",") if part.strip()}


class OutputMasker:
    """Applies REDACT_FIELD / REMOVE_FIELD rules to result payloads."""

    @staticmethod
    def apply(data: Any, rules: list[Rule]) -> tuple[Any, list[str]]:
        """Return ``(masked_data, masked_field_names)``. Input is not mutated."""
        redact: set[str] = set()
        remove: set[str] = set()
        for rule in rules:
            if not rule.is_active:
                continue
            kind = rule.rule_type.upper()
            if kind == REDACT:
                redact |= _field_names(rule.expression)
            elif kind == REMOVE:
                remove |= _field_names(rule.expression)
        # REMOVE wins over REDACT when both name the same field.
        redact -= remove
        if not redact and not remove:
            return data, []

        hit: dict[str, str] = {}  # lower-cased name -> first-seen original casing

        def walk(node: Any) -> Any:
            if isinstance(node, list):
                return [walk(item) for item in node]
            if isinstance(node, dict):
                out: dict[str, Any] = {}
                for key, value in node.items():
                    lowered = str(key).lower()
                    if lowered in remove:
                        hit.setdefault(lowered, str(key))
                        continue
                    if lowered in redact:
                        hit.setdefault(lowered, str(key))
                        out[key] = None
                        continue
                    out[key] = walk(value)
                return out
            return node

        masked = walk(data)
        return masked, sorted(hit.values(), key=str.lower)
