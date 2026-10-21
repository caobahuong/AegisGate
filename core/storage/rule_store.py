"""Rule Store for persisting and querying Governance Rules.

Adheres strictly to python_clean_code.md:
- Full type hinting
- Safe query execution
"""

from typing import Any, Optional
from sqlmodel import Session, select
from core.database import Rule


class RuleStore:
    """Manages governance rules in SQLite."""

    def __init__(self, session: Session) -> None:
        self.session: Session = session

    def create_rule(self, rule: Rule) -> Rule:
        """Create and persist a new rule."""
        self.session.add(rule)
        self.session.commit()
        self.session.refresh(rule)
        return rule

    def get_rule(self, rule_id: str) -> Optional[Rule]:
        """Fetch a rule by ID."""
        statement = select(Rule).where(Rule.id == rule_id)
        return self.session.exec(statement).first()

    def list_rules(
        self,
        target_id: Optional[str] = None,
        is_active_only: bool = False,
    ) -> list[Rule]:
        """List rules, optionally filtered by target and active status.
        
        Rules with target_id == None are global rules and apply to all targets.
        """
        statement = select(Rule)
        if target_id is not None:
            # Include both target-specific rules and global rules
            statement = statement.where((Rule.target_id == target_id) | (Rule.target_id == None))  # noqa: E711
        if is_active_only:
            statement = statement.where(Rule.is_active == True)  # noqa: E712

        return list(self.session.exec(statement).all())

    def update_rule(self, rule_id: str, updates: dict[str, Any]) -> Optional[Rule]:
        """Update existing rule fields."""
        rule = self.get_rule(rule_id)
        if not rule:
            return None

        for field, value in updates.items():
            if hasattr(rule, field):
                setattr(rule, field, value)

        self.session.add(rule)
        self.session.commit()
        self.session.refresh(rule)
        return rule

    def delete_rule(self, rule_id: str) -> bool:
        """Delete a rule by ID."""
        rule = self.get_rule(rule_id)
        if not rule:
            return False
        self.session.delete(rule)
        self.session.commit()
        return True

