"""Cluster coordination, process ownership, heartbeat janitor, and cross-process control.

Adheres strictly to python_clean_code.md:
- Explicit type annotations
- Asyncio background tasks with graceful cancellation
- Compare-and-set and distributed locking for multi-process safety
"""

import asyncio
import contextlib
import logging
import os
import socket
import uuid
from datetime import timedelta
from typing import Any

from sqlmodel import Session, col, select

from core.config import settings
from core.database import (
    DistributedLock,
    ExecutionControl,
    ExecutionLog,
    ProcessHeartbeat,
    engine,
    utc_now,
)
from core.gateway.sse_broadcaster import sse_broadcaster
from core.storage.log_store import LogStore
from plugins.plugin_contract import AbortParams

logger = logging.getLogger(__name__)

# Process-level unique owner identifier
_PROCESS_OWNER_ID: str = f"worker_{uuid.uuid4().hex[:10]}"


def get_owner_id() -> str:
    """Return the unique owner identifier for the current process instance."""
    return _PROCESS_OWNER_ID


def try_acquire_lock(session: Session, name: str, owner_id: str, ttl_seconds: float) -> bool:
    """Attempt to acquire or refresh a distributed lock lease."""
    now = utc_now()
    expires_at = now + timedelta(seconds=ttl_seconds)

    existing = session.exec(select(DistributedLock).where(DistributedLock.name == name)).first()
    if existing is None:
        try:
            lock = DistributedLock(name=name, owner_id=owner_id, acquired_at=now, expires_at=expires_at)
            session.add(lock)
            session.commit()
            return True
        except Exception:
            session.rollback()
            return False

    # Check if lock has expired or is already held by this owner
    if existing.owner_id == owner_id or existing.expires_at < now:
        existing.owner_id = owner_id
        existing.acquired_at = now
        existing.expires_at = expires_at
        session.add(existing)
        session.commit()
        return True

    return False


def release_lock(session: Session, name: str, owner_id: str) -> None:
    """Release distributed lock lease if held by owner_id."""
    existing = session.exec(select(DistributedLock).where(DistributedLock.name == name)).first()
    if existing and existing.owner_id == owner_id:
        session.delete(existing)
        session.commit()


class ClusterManager:
    """Manages cluster heartbeats, stale execution janitor, and cross-process abort listener."""

    def __init__(self, db_engine: Any = engine, owner_id: str = _PROCESS_OWNER_ID) -> None:
        self.engine = db_engine
        self.owner_id = owner_id
        self.hostname = socket.gethostname()
        self.pid = os.getpid()
        self._running = False
        self._heartbeat_task: asyncio.Task[None] | None = None
        self._janitor_task: asyncio.Task[None] | None = None
        self._control_listener_task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        """Start background cluster management coroutines."""
        if self._running:
            return
        self._running = True

        # Initial heartbeat write
        self._record_heartbeat()

        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        self._janitor_task = asyncio.create_task(self._janitor_loop())
        self._control_listener_task = asyncio.create_task(self._control_listener_loop())
        logger.info("ClusterManager started for owner_id=%s (pid=%d, host=%s)", self.owner_id, self.pid, self.hostname)

    async def stop(self) -> None:
        """Stop background tasks and remove heartbeat record."""
        self._running = False

        for task in (self._heartbeat_task, self._janitor_task, self._control_listener_task):
            if task:
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task

        self._heartbeat_task = None
        self._janitor_task = None
        self._control_listener_task = None

        # Clean up heartbeat and held locks
        with contextlib.suppress(Exception), Session(self.engine) as session:
            hb = session.exec(select(ProcessHeartbeat).where(ProcessHeartbeat.owner_id == self.owner_id)).first()
            if hb:
                session.delete(hb)
            release_lock(session, "janitor_lock", self.owner_id)
            session.commit()

        logger.info("ClusterManager stopped for owner_id=%s", self.owner_id)

    def _record_heartbeat(self) -> None:
        """Upsert current process heartbeat timestamp."""
        try:
            with Session(self.engine) as session:
                hb = session.exec(select(ProcessHeartbeat).where(ProcessHeartbeat.owner_id == self.owner_id)).first()
                now = utc_now()
                if hb:
                    hb.last_seen = now
                    hb.pid = self.pid
                    hb.host = self.hostname
                    session.add(hb)
                else:
                    hb = ProcessHeartbeat(
                        owner_id=self.owner_id,
                        pid=self.pid,
                        host=self.hostname,
                        last_seen=now,
                    )
                    session.add(hb)
                session.commit()
        except Exception as exc:
            logger.debug("Failed to record heartbeat: %s", exc)

    async def _heartbeat_loop(self) -> None:
        """Periodically broadcast process liveliness heartbeat."""
        while self._running:
            try:
                await asyncio.sleep(settings.HEARTBEAT_INTERVAL_SECONDS)
                self._record_heartbeat()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.debug("Error in heartbeat loop: %s", exc)

    async def _janitor_loop(self) -> None:
        """Janitor task: cleans up orphaned executions when owner process crashes."""
        while self._running:
            try:
                await asyncio.sleep(5.0)

                with Session(self.engine) as session:
                    # Compete for single-runner janitor lock with 15s TTL
                    has_lock = try_acquire_lock(session, "janitor_lock", self.owner_id, ttl_seconds=15.0)
                    if not has_lock:
                        continue

                    await self._run_janitor_cleanup(session)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.warning("Error in janitor loop: %s", exc)

    async def _run_janitor_cleanup(self, session: Session) -> None:
        """Inspect running executions and dead processes."""
        now = utc_now()
        heartbeat_timeout = timedelta(seconds=settings.HEARTBEAT_TIMEOUT_SECONDS)

        # 1. Fetch active heartbeats
        heartbeats = session.exec(select(ProcessHeartbeat)).all()
        alive_owners: set[str] = {hb.owner_id for hb in heartbeats if hb.last_seen >= (now - heartbeat_timeout)}

        # 2. Inspect executions currently in EXECUTING state
        executing_logs = session.exec(select(ExecutionLog).where(ExecutionLog.status == "EXECUTING")).all()

        log_store = LogStore(session)

        for log in executing_logs:
            # If execution owner is not in alive_owners, mark as FAILED
            if log.owner_id and log.owner_id not in alive_owners:
                logger.warning(
                    "Janitor detected orphaned execution %s (owner %s dead). Failing execution.",
                    log.id,
                    log.owner_id,
                )
                won = log_store.transition_status(
                    log.id,
                    ("EXECUTING",),
                    {
                        "status": "FAILED",
                        "error_message": "owner process died",
                        "finished_at": now,
                    },
                )
                if won:
                    await sse_broadcaster.broadcast(
                        "execution_failed",
                        {
                            "execution_id": log.id,
                            "error": "owner process died",
                            "status": "FAILED",
                        },
                    )

        # 3. Prune old stale heartbeat entries (> 120s)
        stale_threshold = now - timedelta(seconds=120)
        stale_hbs = session.exec(
            select(ProcessHeartbeat).where(col(ProcessHeartbeat.last_seen) < stale_threshold)
        ).all()
        for stale in stale_hbs:
            session.delete(stale)

        session.commit()

    async def _control_listener_loop(self) -> None:
        """Poll execution_control table for commands targeting executions owned by this process."""
        while self._running:
            try:
                await asyncio.sleep(0.15)
                await self._process_pending_controls()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.debug("Error in control listener: %s", exc)

    async def _process_pending_controls(self) -> None:
        """Process pending unhandled commands targeting executions in our local worker."""
        from core.engine.plugin_registry import PluginRegistry

        with Session(self.engine) as session:
            pending_controls = session.exec(
                select(ExecutionControl)
                .where(ExecutionControl.handled_at == None)  # noqa: E711
                .order_by(col(ExecutionControl.id).asc())
                .limit(20)
            ).all()

            if not pending_controls:
                return

            registry = PluginRegistry(session)

            for ctl in pending_controls:
                if ctl.command == "ABORT":
                    # Check if execution belongs to this process
                    log = session.exec(select(ExecutionLog).where(ExecutionLog.id == ctl.execution_id)).first()

                    # Only act if execution belongs to us or has no owner
                    if log and (log.owner_id == self.owner_id or log.owner_id is None):
                        logger.info(
                            "Owner %s received cross-process ABORT for execution %s",
                            self.owner_id,
                            ctl.execution_id,
                        )
                        try:
                            client = registry.get_client(log.target_id)
                            abort_res = await client.abort(AbortParams(execution_id=ctl.execution_id))
                            logger.info("Cross-process abort result for %s: %s", ctl.execution_id, abort_res)
                        except Exception as abort_err:
                            logger.warning("Cross-process abort error for %s: %s", ctl.execution_id, abort_err)

                        ctl.handled_at = utc_now()
                        session.add(ctl)
                        session.commit()


# Process singleton cluster manager instance
cluster_manager = ClusterManager()
