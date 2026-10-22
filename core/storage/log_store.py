"""Execution Log Store for recording and querying query audit logs and states.

Adheres strictly to python_clean_code.md:
- Full type hinting
- Efficient querying
"""

from typing import Any

from sqlmodel import Session, desc, select

from core.database import ExecutionLog


class LogStore:
    """Manages execution logs in SQLite."""

    def __init__(self, session: Session) -> None:
        self.session: Session = session

    def create_log(self, log: ExecutionLog) -> ExecutionLog:
        """Create and persist a new execution log."""
        self.session.add(log)
        self.session.commit()
        self.session.refresh(log)
        return log

    def get_log(self, log_id: str) -> ExecutionLog | None:
        """Fetch log by execution ID."""
        statement = select(ExecutionLog).where(ExecutionLog.id == log_id)
        return self.session.exec(statement).first()

    def update_log(self, log_id: str, updates: dict[str, Any]) -> ExecutionLog | None:
        """Update existing execution log with results or state changes."""
        log = self.get_log(log_id)
        if not log:
            return None

        for field, value in updates.items():
            if hasattr(log, field):
                setattr(log, field, value)

        self.session.add(log)
        self.session.commit()
        self.session.refresh(log)
        return log

    def list_logs(
        self,
        limit: int = 100,
        target_id: str | None = None,
        status: str | None = None,
    ) -> list[ExecutionLog]:
        """List execution logs ordered by most recent."""
        statement = select(ExecutionLog).order_by(desc(ExecutionLog.created_at))
        if target_id:
            statement = statement.where(ExecutionLog.target_id == target_id)
        if status:
            statement = statement.where(ExecutionLog.status == status)
        statement = statement.limit(limit)

        return list(self.session.exec(statement).all())

