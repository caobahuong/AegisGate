"""Unit tests for retention pruning, ndjson gzip archival, and result scrubbing."""

import gzip
import json
from datetime import timedelta
from pathlib import Path

from sqlmodel import Session, select

from core.database import EventOutbox, ExecutionLog, utc_now
from core.storage.retention import prune_logs


def test_prune_terminal_logs_archives_to_ndjson_gz(db_session: Session, tmp_path: Path) -> None:
    """Terminal logs older than retention days are archived to YYYY-MM.ndjson.gz and purged from DB."""
    now = utc_now()
    old_date = now - timedelta(days=45)

    # Insert 3 old terminal logs
    for i in range(3):
        db_session.add(
            ExecutionLog(
                id=f"exec_prune_term_{i}",
                target_id="sqlserver_prod",
                query=f"SELECT {i};",
                query_type="READ",
                status="COMPLETED",
                result_summary=json.dumps({"rows": i}),
                created_at=old_date + timedelta(minutes=i),
            )
        )
    # Insert 1 recent terminal log (should survive)
    db_session.add(
        ExecutionLog(
            id="exec_survivor_term",
            target_id="sqlserver_prod",
            query="SELECT 999;",
            query_type="READ",
            status="COMPLETED",
            created_at=now - timedelta(days=2),
        )
    )
    db_session.commit()

    archive_dir = tmp_path / "archive"
    report = prune_logs(
        session=db_session,
        log_retention_days=30,
        archive_before_delete=True,
        archive_dir=archive_dir,
    )

    assert report.pruned_logs_count == 3
    assert report.archived_logs_count == 3
    assert len(report.archived_files) == 1

    # Check database state
    remaining = db_session.exec(select(ExecutionLog)).all()
    remaining_ids = {log.id for log in remaining}
    assert remaining_ids == {"exec_survivor_term"}

    # Check archive content
    archive_file = Path(report.archived_files[0])
    assert archive_file.exists()
    assert archive_file.name.endswith(".ndjson.gz")

    with gzip.open(archive_file, "rt", encoding="utf-8") as gz_in:
        archived_lines = [json.loads(line) for line in gz_in if line.strip()]
    assert len(archived_lines) == 3
    assert {line_item["id"] for line_item in archived_lines} == {
        "exec_prune_term_0",
        "exec_prune_term_1",
        "exec_prune_term_2",
    }


def test_prune_never_deletes_non_terminal_active_executions(db_session: Session, tmp_path: Path) -> None:
    """Active non-terminal states (EXECUTING, QUEUED, PAUSED_FOR_REVIEW, DRY_RUN) must NEVER be pruned."""
    now = utc_now()
    ancient_date = now - timedelta(days=100)

    for status in ("EXECUTING", "QUEUED", "PAUSED_FOR_REVIEW", "DRY_RUN"):
        db_session.add(
            ExecutionLog(
                id=f"exec_active_{status.lower()}",
                target_id="sqlserver_prod",
                query="SELECT * FROM important_workflow;",
                query_type="READ",
                status=status,
                created_at=ancient_date,
            )
        )
    db_session.commit()

    report = prune_logs(
        session=db_session,
        log_retention_days=30,
        archive_dir=tmp_path / "archive",
    )

    assert report.pruned_logs_count == 0
    remaining = db_session.exec(select(ExecutionLog)).all()
    assert len(remaining) == 4


def test_prune_scrubs_bulky_results_older_than_result_days(db_session: Session, tmp_path: Path) -> None:
    """Surviving terminal logs older than result_retention_days have result_summary NULLed."""
    now = utc_now()

    # Log 15 days old (between 7 and 30 days): survives pruning but should have result scrubbed
    log_scrub = ExecutionLog(
        id="exec_scrub_target",
        target_id="sqlserver_prod",
        query="SELECT * FROM big_payload;",
        query_type="READ",
        status="COMPLETED",
        result_summary=json.dumps({"huge_data": [1, 2, 3] * 100}),
        created_at=now - timedelta(days=15),
    )
    # Log 2 days old: keeps its result_summary
    log_fresh = ExecutionLog(
        id="exec_fresh_target",
        target_id="sqlserver_prod",
        query="SELECT 1;",
        query_type="READ",
        status="COMPLETED",
        result_summary=json.dumps({"rows": 1}),
        created_at=now - timedelta(days=2),
    )
    db_session.add(log_scrub)
    db_session.add(log_fresh)
    db_session.commit()

    report = prune_logs(
        session=db_session,
        log_retention_days=30,
        result_retention_days=7,
        archive_dir=tmp_path / "archive",
    )

    assert report.pruned_logs_count == 0
    assert report.scrubbed_results_count == 1

    db_session.refresh(log_scrub)
    db_session.refresh(log_fresh)
    assert log_scrub.result_summary is None
    assert log_fresh.result_summary is not None


def test_prune_dry_run_leaves_database_and_disk_unmodified(db_session: Session, tmp_path: Path) -> None:
    """When dry_run=True, no records are deleted and no files are written."""
    now = utc_now()
    log = ExecutionLog(
        id="exec_dry_run_candidate",
        target_id="sqlserver_prod",
        query="SELECT 1;",
        query_type="READ",
        status="COMPLETED",
        created_at=now - timedelta(days=40),
    )
    db_session.add(log)
    db_session.commit()

    archive_dir = tmp_path / "archive"
    report = prune_logs(
        session=db_session,
        log_retention_days=30,
        dry_run=True,
        archive_dir=archive_dir,
    )

    assert report.dry_run is True
    assert report.pruned_logs_count == 1
    assert not archive_dir.exists()

    db_session.refresh(log)
    assert log is not None


def test_prune_outbox_events_cleanup(db_session: Session) -> None:
    """Stale outbox events older than OUTBOX_RETENTION_HOURS are purged."""
    now = utc_now()
    old_event = EventOutbox(
        event_type="execution_completed",
        payload_json="{}",
        created_at=now - timedelta(hours=36),
    )
    fresh_event = EventOutbox(
        event_type="execution_completed",
        payload_json="{}",
        created_at=now - timedelta(hours=2),
    )
    db_session.add(old_event)
    db_session.add(fresh_event)
    db_session.commit()

    report = prune_logs(session=db_session)
    assert report.pruned_outbox_count >= 1

    surviving = db_session.exec(select(EventOutbox)).all()
    surviving_ids = [e.id for e in surviving]
    assert fresh_event.id in surviving_ids
    assert old_event.id not in surviving_ids
