"""Data lifecycle retention, gzip ndjson archival, and log pruning.

Adheres strictly to python_clean_code.md:
- Explicit type annotations
- Strict preservation of non-terminal in-flight executions
- Gzip compressed NDJSON archival format
"""

import gzip
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path

from sqlmodel import Session, col, select

from core.config import settings
from core.database import EventOutbox, ExecutionLog, utc_now

logger = logging.getLogger(__name__)

# Non-terminal statuses that must NEVER be deleted or scrubbed
ACTIVE_STATUSES: tuple[str, ...] = ("QUEUED", "EXECUTING", "PAUSED_FOR_REVIEW", "DRY_RUN")

# Terminal statuses eligible for retention pruning
TERMINAL_STATUSES: tuple[str, ...] = ("COMPLETED", "REJECTED", "TIMEOUT", "ABORTED", "FAILED")


@dataclass
class RetentionReport:
    """Summary of operations performed during log pruning and archival."""

    pruned_logs_count: int = 0
    archived_logs_count: int = 0
    scrubbed_results_count: int = 0
    pruned_outbox_count: int = 0
    archived_files: list[str] = field(default_factory=list)
    dry_run: bool = False


def prune_logs(
    session: Session,
    log_retention_days: int | None = None,
    result_retention_days: int | None = None,
    archive_before_delete: bool | None = None,
    dry_run: bool = False,
    archive_dir: Path | None = None,
) -> RetentionReport:
    """Prune old terminal execution records, scrub stale results, and archive to ndjson.gz.

    Parameters:
    - log_retention_days: Days to retain terminal logs before deletion (default: settings.LOG_RETENTION_DAYS).
    - result_retention_days: Days to retain bulky result_summary payloads (default: settings.RESULT_RETENTION_DAYS).
    - archive_before_delete: If True, writes records to YYYY-MM.ndjson.gz before deletion.
    - dry_run: If True, calculates records without mutating database or creating archives.
    - archive_dir: Output directory for archive files (default: settings.ARCHIVE_DIR).
    """
    effective_log_days = log_retention_days if log_retention_days is not None else settings.LOG_RETENTION_DAYS
    effective_result_days = (
        result_retention_days if result_retention_days is not None else settings.RESULT_RETENTION_DAYS
    )
    should_archive = archive_before_delete if archive_before_delete is not None else settings.ARCHIVE_BEFORE_DELETE
    target_archive_dir = archive_dir or settings.ARCHIVE_DIR

    report = RetentionReport(dry_run=dry_run)
    now = utc_now()

    # 1. Identify terminal logs older than log_retention_days
    log_cutoff = now - timedelta(days=effective_log_days)
    prune_stmt = (
        select(ExecutionLog)
        .where(col(ExecutionLog.status).in_(TERMINAL_STATUSES))
        .where(col(ExecutionLog.created_at) < log_cutoff)
    )
    eligible_logs = list(session.exec(prune_stmt).all())
    report.pruned_logs_count = len(eligible_logs)

    # 2. Archive to YYYY-MM.ndjson.gz if enabled
    if should_archive and eligible_logs and not dry_run:
        target_archive_dir.mkdir(parents=True, exist_ok=True)
        by_month: dict[str, list[ExecutionLog]] = defaultdict(list)
        for log in eligible_logs:
            month_key = log.created_at.strftime("%Y-%m")
            by_month[month_key].append(log)

        for month_key, month_logs in by_month.items():
            archive_file = target_archive_dir / f"{month_key}.ndjson.gz"
            with gzip.open(archive_file, "at", encoding="utf-8") as gz_out:
                for log in month_logs:
                    gz_out.write(log.model_dump_json() + "\n")
            report.archived_files.append(str(archive_file))
            report.archived_logs_count += len(month_logs)
            logger.info("Archived %d log(s) to %s", len(month_logs), archive_file)
    elif dry_run:
        report.archived_logs_count = len(eligible_logs)

    # 3. Delete pruned logs from database
    if not dry_run and eligible_logs:
        for log in eligible_logs:
            session.delete(log)
        session.commit()
        logger.info("Purged %d execution log(s) older than %s", len(eligible_logs), log_cutoff.isoformat())

    # 4. Scrub bulky result_summary payloads for surviving terminal logs older than result_retention_days
    result_cutoff = now - timedelta(days=effective_result_days)
    scrub_stmt = (
        select(ExecutionLog)
        .where(col(ExecutionLog.status).in_(TERMINAL_STATUSES))
        .where(col(ExecutionLog.created_at) < result_cutoff)
        .where(col(ExecutionLog.result_summary).is_not(None))
    )
    scrub_logs = list(session.exec(scrub_stmt).all())
    report.scrubbed_results_count = len(scrub_logs)

    if not dry_run and scrub_logs:
        for log in scrub_logs:
            log.result_summary = None
            session.add(log)
        session.commit()
        logger.info("Scrubbed %d result_summary payload(s) older than %s", len(scrub_logs), result_cutoff.isoformat())

    # 5. Prune event_outbox older than OUTBOX_RETENTION_HOURS
    outbox_cutoff = now - timedelta(hours=settings.OUTBOX_RETENTION_HOURS)
    outbox_stmt = select(EventOutbox).where(col(EventOutbox.created_at) < outbox_cutoff)
    stale_outbox = list(session.exec(outbox_stmt).all())
    report.pruned_outbox_count = len(stale_outbox)

    if not dry_run and stale_outbox:
        for ev in stale_outbox:
            session.delete(ev)
        session.commit()
        logger.info("Purged %d stale event_outbox row(s) older than %s", len(stale_outbox), outbox_cutoff.isoformat())

    return report
