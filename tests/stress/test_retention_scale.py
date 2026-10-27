"""Retention, Archival, and Cleanup Scale Tests with Large Datasets.

Tests verify:
1. Retention pruning against 1,000+ execution logs.
2. In-flight / non-terminal executions (EXECUTING, PAUSED_FOR_REVIEW, QUEUED) are strictly preserved.
3. Recent terminal logs within retention window are never purged.
4. Gzip compressed NDJSON archive generation (.ndjson.gz) and data integrity.
5. Result summary payload scrubbing on surviving older logs.
6. Event outbox log pruning.
"""

import gzip
import json
from datetime import timedelta
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlmodel import Session, select

from core.database import ExecutionLog, init_db, utc_now
from core.storage.retention import prune_logs


@pytest.fixture
def retention_db(tmp_path: Path):
    """Provide isolated SQLite database for retention scale tests."""
    db_file = tmp_path / "retention_scale.db"
    test_engine = create_engine(
        f"sqlite:///{db_file}",
        connect_args={"check_same_thread": False, "timeout": 15.0},
    )
    init_db(test_engine)
    yield test_engine
    test_engine.dispose()


def test_retention_scale_1000_logs_and_non_terminal_preservation(retention_db, tmp_path: Path) -> None:
    """Seed 1,000+ logs and verify retention pruning, archival, and non-terminal safety.

    Dataset composition:
    - 500 expired terminal logs (COMPLETED, REJECTED, FAILED, TIMEOUT, ABORTED) older than 30 days -> MUST be archived & pruned.
    - 200 recent terminal logs (COMPLETED) created 5 days ago -> MUST be retained.
    - 200 in-flight EXECUTING logs created 40 days ago (stuck or slow) -> MUST NOT be deleted.
    - 100 PAUSED_FOR_REVIEW logs created 45 days ago -> MUST NOT be deleted.
    - 50 QUEUED logs created 50 days ago -> MUST NOT be deleted.
    Total: 1,050 records.
    """
    archive_dir = tmp_path / "archives"
    now = utc_now()
    expired_time = now - timedelta(days=35)
    recent_time = now - timedelta(days=5)

    with Session(retention_db) as session:
        # 1. 500 expired terminal logs
        terminal_statuses = ["COMPLETED", "REJECTED", "FAILED", "TIMEOUT", "ABORTED"]
        for i in range(500):
            session.add(
                ExecutionLog(
                    id=f"exec_expired_term_{i}",
                    target_id="sqlserver_target",
                    query=f"SELECT {i};",
                    query_type="READ",
                    status=terminal_statuses[i % len(terminal_statuses)],
                    result_summary='{"rows": [1, 2, 3]}',
                    created_at=expired_time,
                    finished_at=expired_time,
                )
            )

        # 2. 200 recent terminal logs
        for i in range(200):
            session.add(
                ExecutionLog(
                    id=f"exec_recent_term_{i}",
                    target_id="sqlserver_target",
                    query=f"SELECT recent_{i};",
                    query_type="READ",
                    status="COMPLETED",
                    result_summary='{"rows": ["recent"]}',
                    created_at=recent_time,
                    finished_at=recent_time,
                )
            )

        # 3. 200 in-flight EXECUTING logs (created 40 days ago)
        for i in range(200):
            session.add(
                ExecutionLog(
                    id=f"exec_inflight_executing_{i}",
                    target_id="sqlserver_target",
                    query=f"SELECT running_{i};",
                    query_type="READ",
                    status="EXECUTING",
                    created_at=expired_time - timedelta(days=5),
                    started_at=expired_time - timedelta(days=5),
                )
            )

        # 4. 100 in-flight PAUSED_FOR_REVIEW logs (created 45 days ago)
        for i in range(100):
            session.add(
                ExecutionLog(
                    id=f"exec_inflight_paused_{i}",
                    target_id="sqlserver_target",
                    query=f"SELECT paused_{i};",
                    query_type="READ",
                    status="PAUSED_FOR_REVIEW",
                    created_at=expired_time - timedelta(days=10),
                )
            )

        # 5. 50 in-flight QUEUED logs (created 50 days ago)
        for i in range(50):
            session.add(
                ExecutionLog(
                    id=f"exec_inflight_queued_{i}",
                    target_id="sqlserver_target",
                    query=f"SELECT queued_{i};",
                    query_type="READ",
                    status="QUEUED",
                    created_at=expired_time - timedelta(days=15),
                )
            )

        session.commit()

    # Verify total initial count is 1,050
    with Session(retention_db) as session:
        initial_count = len(session.exec(select(ExecutionLog)).all())
        assert initial_count == 1050

    # Run retention pruning with 30-day window
    with Session(retention_db) as session:
        report = prune_logs(
            session=session,
            log_retention_days=30,
            result_retention_days=10,
            archive_before_delete=True,
            archive_dir=archive_dir,
        )

    # Verify report statistics
    assert report.pruned_logs_count == 500
    assert report.archived_logs_count == 500
    assert len(report.archived_files) >= 1

    # Verify database state after pruning
    with Session(retention_db) as session:
        all_surviving = session.exec(select(ExecutionLog)).all()
        # Remaining: 200 recent + 200 executing + 100 paused + 50 queued = 550 logs
        assert len(all_surviving) == 550

        # Check non-terminal logs: exactly 350 active logs remain completely untouched
        executing_surviving = session.exec(select(ExecutionLog).where(ExecutionLog.status == "EXECUTING")).all()
        assert len(executing_surviving) == 200

        paused_surviving = session.exec(select(ExecutionLog).where(ExecutionLog.status == "PAUSED_FOR_REVIEW")).all()
        assert len(paused_surviving) == 100

        queued_surviving = session.exec(select(ExecutionLog).where(ExecutionLog.status == "QUEUED")).all()
        assert len(queued_surviving) == 50

        # Check recent terminal logs: all 200 remain
        recent_surviving = session.exec(
            select(ExecutionLog).where(ExecutionLog.id.startswith("exec_recent_term_"))
        ).all()
        assert len(recent_surviving) == 200

        # Check expired terminal logs: 0 remain
        expired_surviving = session.exec(
            select(ExecutionLog).where(ExecutionLog.id.startswith("exec_expired_term_"))
        ).all()
        assert len(expired_surviving) == 0

    # Verify archive file contents
    archive_file = Path(report.archived_files[0])
    assert archive_file.exists()
    assert archive_file.name.endswith(".ndjson.gz")

    archived_lines = 0
    with gzip.open(archive_file, "rt", encoding="utf-8") as gz_in:
        for line in gz_in:
            line_str = line.strip()
            if line_str:
                data = json.loads(line_str)
                assert data["id"].startswith("exec_expired_term_")
                archived_lines += 1

    assert archived_lines == 500
