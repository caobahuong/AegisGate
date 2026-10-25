"""Rule Store for persisting and querying Governance Rules.

Adheres strictly to python_clean_code.md:
- Full type hinting
- Safe query execution
"""

from typing import Any

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

    def get_rule(self, rule_id: str) -> Rule | None:
        """Fetch a rule by ID."""
        statement = select(Rule).where(Rule.id == rule_id)
        return self.session.exec(statement).first()

    def list_rules(
        self,
        target_id: str | None = None,
        is_active_only: bool = False,
        exact_target: bool = False,
    ) -> list[Rule]:
        """List rules, optionally filtered by target and active status.

        If target_id == 'global', matches rules where target_id is None.
        If exact_target is True, matches Rule.target_id == target_id strictly.
        Otherwise, target_id includes both target-specific and global rules.
        """
        statement = select(Rule)
        if target_id == "global":
            statement = statement.where(Rule.target_id == None)
        elif target_id is not None:
            if exact_target:
                statement = statement.where(Rule.target_id == target_id)
            else:
                statement = statement.where((Rule.target_id == target_id) | (Rule.target_id == None))
        if is_active_only:
            statement = statement.where(Rule.is_active == True)

        return list(self.session.exec(statement).all())

    def update_rule(self, rule_id: str, updates: dict[str, Any]) -> Rule | None:
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
