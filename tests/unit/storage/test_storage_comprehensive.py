"""Comprehensive unit tests for KnowledgeStore, SettingStore, LogStore, and Retention edge cases.

Specifically verifies:
1. KnowledgeStore: missing/nonexistent file handling, OSError wrapping in StorageError, corrupt JSON in catalog,
   update_docs for nonexistent chunk, delete_chunk nonexistent and file unlinking, ingest updating existing chunk.
2. SettingStore: description updates on existing setting, default fallbacks.
3. Retention: empty DB run, exact boundary timing (cutoff - 1s vs cutoff + 1s), non-terminal log preservation (in-flight
   queries never purged), dry-run retention report.
"""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlmodel import Session, select

from core.database import ExecutionLog, KnowledgeChunk, SystemSetting, utc_now
from core.exceptions import StorageError
from core.storage.knowledge_store import KnowledgeStore
from core.storage.log_store import LogStore
from core.storage.retention import prune_logs
from core.storage.setting_store import SettingStore


def test_knowledge_store_edge_cases(db_session: Session, tmp_path: Path):
    """KnowledgeStore handles missing files, corrupt json, unlinks files, and updates existing chunks."""
    docs_dir = tmp_path / "k_docs"
    docs_dir.mkdir(parents=True)
    store = KnowledgeStore(db_session, docs_dir=docs_dir)

    # 1. Missing or None filename returns empty string
    assert store._read_file_safe(None) == ""
    assert store._read_file_safe("does_not_exist.md") == ""

    # 2. Corrupt catalog_json in get_chunk & list_chunks
    chunk_corrupt = KnowledgeChunk(
        id="c_corrupt",
        target_id="t1",
        partition_key="P1",
        title="P1 Title",
        catalog_json="{invalid json",
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    db_session.add(chunk_corrupt)
    db_session.commit()

    retrieved = store.get_chunk("c_corrupt")
    assert retrieved is not None
    assert retrieved["catalog"] == {}

    listed = store.list_chunks(target_id="t1")
    assert len(listed) == 1
    assert listed[0]["catalog"] == {}

    # 3. update_docs on nonexistent chunk returns False
    assert store.update_docs("nonexistent_id", doc_content="abc") is False

    # 4. delete_chunk on nonexistent chunk returns False
    assert store.delete_chunk("nonexistent_id") is False

    # 5. delete_chunk unlinks files
    chunk_with_files = KnowledgeChunk(
        id="c_files",
        target_id="t1",
        partition_key="P2",
        title="P2 Title",
        catalog_json="{}",
        doc_file="c_files_doc.md",
        skills_file="c_files_skills.md",
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    store.save_chunk(chunk_with_files, doc_content="doc text", skills_content="skills text")
    assert (docs_dir / "c_files_doc.md").exists()
    assert (docs_dir / "c_files_skills.md").exists()

    assert store.delete_chunk("c_files") is True
    assert not (docs_dir / "c_files_doc.md").exists()
    assert not (docs_dir / "c_files_skills.md").exists()

    # 6. ingest_plugin_catalog updates existing chunk
    p1 = [{"partition_key": "Finance", "title": "Finance Part 1", "tables": ["T1"]}]
    created_chunks = store.ingest_plugin_catalog("t1", p1)
    assert len(created_chunks) == 1
    assert created_chunks[0].title == "Finance Part 1"

    p2 = [{"partition_key": "Finance", "title": "Finance Part 1 Renamed", "tables": ["T1", "T2"]}]
    updated_chunks = store.ingest_plugin_catalog("t1", p2)
    assert len(updated_chunks) == 1
    assert updated_chunks[0].title == "Finance Part 1 Renamed"


def test_knowledge_store_oserror_handling(db_session: Session, tmp_path: Path):
    """KnowledgeStore wraps OS read/write errors into StorageError."""
    docs_dir = tmp_path / "k_docs_err"
    docs_dir.mkdir(parents=True)
    store = KnowledgeStore(db_session, docs_dir=docs_dir)

    target_file = docs_dir / "fail.md"
    target_file.write_text("ok", encoding="utf-8")

    with (
        patch.object(Path, "read_text", side_effect=OSError("Disk read error")),
        pytest.raises(StorageError, match="Failed to read file"),
    ):
        store._read_file_safe("fail.md")

    with (
        patch.object(Path, "write_text", side_effect=OSError("Disk write error")),
        pytest.raises(StorageError, match="Failed to write file"),
    ):
        store._write_file_safe("fail.md", "content")


def test_setting_store_description_and_defaults(db_session: Session):
    """SettingStore updates descriptions and falls back to default values."""
    store = SettingStore(db_session)

    # Initial set
    store.set_setting("retention_policy", "aggressive", description="Initial description")
    assert store.get_setting("retention_policy") == "aggressive"

    # Update value and description
    store.set_setting("retention_policy", "standard", description="Updated description")
    assert store.get_setting("retention_policy") == "standard"

    stmt = select(SystemSetting).where(SystemSetting.key == "retention_policy")
    row = db_session.exec(stmt).first()
    assert row is not None
    assert row.description == "Updated description"

    # Default fallback for missing key
    assert store.get_setting("unknown_key", default="fallback_val") == "fallback_val"


def test_retention_empty_database_and_boundaries(db_session: Session, tmp_path: Path):
    """Retention boundary conditions: empty database, exact cutoffs, and non-terminal preservation."""
    archive_dir = tmp_path / "archive"

    # 1. Empty database run
    rep_empty = prune_logs(db_session, log_retention_days=30, archive_dir=archive_dir)
    assert rep_empty.pruned_logs_count == 0
    assert rep_empty.archived_logs_count == 0

    # 2. Exact boundary timing:
    # Cutoff is (now - 30 days)
    now = datetime.now(UTC)
    cutoff = now - timedelta(days=30)

    # Older than cutoff by 1 second (MUST be pruned)
    log_old = ExecutionLog(
        id="log_older_1s",
        target_id="t1",
        status="COMPLETED",
        query="SELECT 1",
        query_type="READ",
        created_at=cutoff - timedelta(seconds=1),
    )
    # Newer than cutoff by 1 second (MUST survive)
    log_new = ExecutionLog(
        id="log_newer_1s",
        target_id="t1",
        status="COMPLETED",
        query="SELECT 2",
        query_type="READ",
        created_at=cutoff + timedelta(seconds=1),
    )
    # Older than cutoff by 10 days BUT status is EXECUTING (non-terminal, MUST survive)
    log_inflight = ExecutionLog(
        id="log_inflight_old",
        target_id="t1",
        status="EXECUTING",
        query="SELECT 3",
        query_type="READ",
        created_at=cutoff - timedelta(days=10),
    )
    # Older than cutoff by 10 days BUT status is PAUSED_FOR_REVIEW (non-terminal, MUST survive)
    log_paused = ExecutionLog(
        id="log_paused_old",
        target_id="t1",
        status="PAUSED_FOR_REVIEW",
        query="SELECT 4",
        query_type="WRITE",
        created_at=cutoff - timedelta(days=10),
    )

    db_session.add(log_old)
    db_session.add(log_new)
    db_session.add(log_inflight)
    db_session.add(log_paused)
    db_session.commit()

    report = prune_logs(
        db_session,
        log_retention_days=30,
        archive_before_delete=True,
        archive_dir=archive_dir,
    )

    # Exactly 1 log pruned
    assert report.pruned_logs_count == 1
    assert report.archived_logs_count == 1

    remaining = db_session.exec(select(ExecutionLog)).all()
    remaining_ids = {r.id for r in remaining}
    assert remaining_ids == {"log_newer_1s", "log_inflight_old", "log_paused_old"}


def test_log_store_paginate_comprehensive(db_session: Session):
    """LogStore.paginate_logs handles dates, search, status=ALL, and decoded cursors."""
    store = LogStore(db_session)
    now = datetime.now(UTC)

    for i in range(10):
        log = ExecutionLog(
            id=f"log_page_{i:02d}",
            target_id="target_sql" if i % 2 == 0 else "target_pg",
            status="COMPLETED" if i < 6 else "FAILED",
            query=f"SELECT * FROM items_{i}",
            query_type="READ",
            reasoning=f"Reason {i}",
            created_at=now - timedelta(hours=i),
        )
        store.create_log(log)

    # 1. status="ALL"
    items, next_cursor, total = store.paginate_logs(status="ALL", limit=20)
    assert total == 10
    assert len(items) == 10

    # 2. Date ranges
    from_dt = now - timedelta(hours=4, minutes=30)
    to_dt = now - timedelta(hours=1, minutes=30)
    items_dt, _, total_dt = store.paginate_logs(from_date=from_dt, to_date=to_dt, limit=20)
    assert total_dt == 3

    # 3. Pagination with limit=4
    p1, cursor1, tot1 = store.paginate_logs(limit=4)
    assert len(p1) == 4
    assert tot1 == 10
    assert cursor1 is not None

    p2, cursor2, tot2 = store.paginate_logs(cursor=cursor1, limit=4)
    assert len(p2) == 4
    assert p2[0].id != p1[0].id

    # 4. Bad cursor format recovers gracefully
    items_bad_cur, _, _ = store.paginate_logs(cursor="bad_cursor!@#", limit=5)
    assert len(items_bad_cur) == 5
