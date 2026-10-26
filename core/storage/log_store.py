"""Execution Log Store for recording and querying query audit logs and states.

Adheres strictly to python_clean_code.md:
- Full type hinting
- Efficient querying
"""

import base64
import contextlib
from datetime import datetime
from typing import Any

from sqlalchemy import and_, func, or_
from sqlalchemy import update as sa_update
from sqlmodel import Session, col, desc, select

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

    def transition_status(
        self,
        log_id: str,
        expected_statuses: tuple[str, ...],
        updates: dict[str, Any],
    ) -> bool:
        """Atomically move a log out of ``expected_statuses`` (compare-and-set).

        Issues a single conditional UPDATE so two concurrent callers (e.g. a double
        click on Approve) cannot both win. Returns True only for the winner.
        """
        statement = (
            sa_update(ExecutionLog)
            .where(ExecutionLog.id == log_id, ExecutionLog.status.in_(expected_statuses))  # type: ignore[attr-defined, arg-type]
            .values(**updates)
        )
        result = self.session.exec(statement)
        self.session.commit()
        return bool(result.rowcount)

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

    def paginate_logs(
        self,
        cursor: str | None = None,
        limit: int = 50,
        status: str | None = None,
        target_id: str | None = None,
        query_search: str | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
    ) -> tuple[list[ExecutionLog], str | None, int]:
        """Cursor-paginated log query with filtering and total count."""
        base_conditions: list[Any] = []

        if target_id:
            base_conditions.append(ExecutionLog.target_id == target_id)
        if status and status != "ALL":
            base_conditions.append(ExecutionLog.status == status)
        if query_search:
            pattern = f"%{query_search}%"
            base_conditions.append(
                or_(
                    col(ExecutionLog.query).ilike(pattern),
                    col(ExecutionLog.reasoning).ilike(pattern),
                    col(ExecutionLog.id).ilike(pattern),
                )
            )
        if from_date:
            base_conditions.append(col(ExecutionLog.created_at) >= from_date)
        if to_date:
            base_conditions.append(col(ExecutionLog.created_at) <= to_date)

        # 1. Total count query with base filters
        total_stmt = select(func.count(col(ExecutionLog.id)))
        if base_conditions:
            total_stmt = total_stmt.where(and_(*base_conditions))
        total_count = self.session.exec(total_stmt).one()

        # 2. Page query
        page_conditions: list[Any] = list(base_conditions)
        if cursor:
            with contextlib.suppress(Exception):
                decoded = base64.urlsafe_b64decode(cursor.encode("utf-8")).decode("utf-8")
                parts = decoded.split("|", 1)
                if len(parts) == 2:
                    cursor_ts = datetime.fromisoformat(parts[0])
                    cursor_id = parts[1]
                    page_conditions.append(
                        or_(
                            col(ExecutionLog.created_at) < cursor_ts,
                            and_(col(ExecutionLog.created_at) == cursor_ts, col(ExecutionLog.id) < cursor_id),
                        )
                    )

        stmt = select(ExecutionLog)
        if page_conditions:
            stmt = stmt.where(and_(*page_conditions))

        stmt = stmt.order_by(col(ExecutionLog.created_at).desc(), col(ExecutionLog.id).desc()).limit(limit + 1)
        items = list(self.session.exec(stmt).all())

        next_cursor: str | None = None
        if len(items) > limit:
            items = items[:limit]
            last_item = items[-1]
            raw_cursor = f"{last_item.created_at.isoformat()}|{last_item.id}"
            next_cursor = base64.urlsafe_b64encode(raw_cursor.encode("utf-8")).decode("utf-8")

        return items, next_cursor, total_count
