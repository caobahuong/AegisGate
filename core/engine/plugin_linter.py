"""AegisGate Plugin Certification Linter Engine (Idea 5).

Runs an automated 4-stage sanity test pipeline with strict timeout guards:
1. Handshake & RPC Ping (ping / RPC responsiveness)
2. Sync Knowledge Schema (sync_knowledge)
3. Dry-Run Analysis (dry_run)
4. Abort Hook Protocol (abort)

Saves certification report into SQLite database and provides badges.
Strictly follows python_clean_code.md:
- 100% Type Hints
- Explicit exception handling
- Clean async/await
"""

import json
import logging
import time
from typing import Any

from sqlmodel import Session, select

from core.database import PluginProfile, utc_now
from core.engine.plugin_client import PluginSubprocessClient
from core.exceptions import JsonRpcProtocolError

logger = logging.getLogger(__name__)

TIMEOUT_PER_STAGE_SECONDS = 5.0


class PluginLinter:
    """Verifies and certifies AegisGate database plugins via 4-stage automated QA."""

    def __init__(self, session: Session) -> None:
        self.session = session

    async def verify_plugin(self, plugin_id: str) -> dict[str, Any]:
        """Execute 4-stage sanity checks against a registered plugin."""
        statement = select(PluginProfile).where(PluginProfile.id == plugin_id)
        profile = self.session.exec(statement).first()
        if not profile:
            raise ValueError(f"Plugin with ID '{plugin_id}' not found.")

        config = {}
        try:
            config = json.loads(profile.config_json or "{}")
        except Exception:
            config = {}

        client = PluginSubprocessClient(profile.entrypoint, plugin_id=profile.id, config=config)
        checks: dict[str, Any] = {}
        all_passed = True
        overall_error: str | None = None

        # ---------------------------------------------------------
        # Stage 1: Handshake & RPC Ping
        # ---------------------------------------------------------
        t0 = time.perf_counter()
        try:
            try:
                ping_res = await client.send_rpc_command(
                    "ping",
                    {"config": config},
                    timeout=TIMEOUT_PER_STAGE_SECONDS,
                )
                status_info = ping_res.get("status") if isinstance(ping_res, dict) else "ok"
            except JsonRpcProtocolError:
                # If ping method is not explicitly supported by plugin, RPC responsiveness is still verified
                status_info = "rpc_ready"

            latency_ms = round((time.perf_counter() - t0) * 1000, 2)
            checks["handshake"] = {
                "status": "PASSED",
                "latency_ms": latency_ms,
                "details": f"Handshake successful ({status_info})",
            }
        except TimeoutError:
            all_passed = False
            latency_ms = round((time.perf_counter() - t0) * 1000, 2)
            checks["handshake"] = {
                "status": "FAILED",
                "latency_ms": latency_ms,
                "error": f"Handshake timed out after {TIMEOUT_PER_STAGE_SECONDS}s",
            }
            overall_error = "Stage 1 Handshake timed out."
        except Exception as exc:
            all_passed = False
            latency_ms = round((time.perf_counter() - t0) * 1000, 2)
            checks["handshake"] = {
                "status": "FAILED",
                "latency_ms": latency_ms,
                "error": str(exc),
            }
            overall_error = f"Stage 1 Handshake failed: {exc!s}"

        # ---------------------------------------------------------
        # Stage 2: Sync Knowledge Schema
        # ---------------------------------------------------------
        t0 = time.perf_counter()
        try:
            sync_res = await client.send_rpc_command(
                "sync_knowledge",
                {"config": config},
                timeout=TIMEOUT_PER_STAGE_SECONDS,
            )
            latency_ms = round((time.perf_counter() - t0) * 1000, 2)

            catalog_valid = isinstance(sync_res, dict) and (
                "schemas" in sync_res
                or "tables" in sync_res
                or "collections" in sync_res
                or "views" in sync_res
                or "partitions" in sync_res
            )
            if catalog_valid:
                count_items = len(sync_res.get("tables", sync_res.get("collections", sync_res.get("partitions", []))))
                checks["sync_knowledge"] = {
                    "status": "PASSED",
                    "latency_ms": latency_ms,
                    "details": f"Extracted catalog schema ({count_items} items)",
                }
            else:
                all_passed = False
                checks["sync_knowledge"] = {
                    "status": "FAILED",
                    "latency_ms": latency_ms,
                    "error": "Catalog response missing required schema/tables/partitions keys",
                }
                if not overall_error:
                    overall_error = "Stage 2 Schema missing required keys."
        except TimeoutError:
            all_passed = False
            checks["sync_knowledge"] = {
                "status": "FAILED",
                "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
                "error": f"sync_knowledge timed out after {TIMEOUT_PER_STAGE_SECONDS}s",
            }
            if not overall_error:
                overall_error = "Stage 2 sync_knowledge timed out."
        except Exception as exc:
            all_passed = False
            checks["sync_knowledge"] = {
                "status": "FAILED",
                "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
                "error": str(exc),
            }
            if not overall_error:
                overall_error = f"Stage 2 sync_knowledge failed: {exc!s}"

        # ---------------------------------------------------------
        # Stage 3: Dry-Run Analysis
        # ---------------------------------------------------------
        t0 = time.perf_counter()
        try:
            dry_res = await client.send_rpc_command(
                "dry_run",
                {"query": "SELECT 1 AS test_val;", "config": config},
                timeout=TIMEOUT_PER_STAGE_SECONDS,
            )
            latency_ms = round((time.perf_counter() - t0) * 1000, 2)

            if isinstance(dry_res, dict) and (
                "explain_plan" in dry_res or "risk_score" in dry_res or "estimated_cost" in dry_res
            ):
                checks["dry_run"] = {
                    "status": "PASSED",
                    "latency_ms": latency_ms,
                    "details": "Dry-run generated SHOWPLAN/EXPLAIN successfully",
                }
            else:
                all_passed = False
                checks["dry_run"] = {
                    "status": "FAILED",
                    "latency_ms": latency_ms,
                    "error": "dry_run response missing 'explain_plan' or 'risk_score'",
                }
                if not overall_error:
                    overall_error = "Stage 3 dry_run missing explain_plan."
        except TimeoutError:
            all_passed = False
            checks["dry_run"] = {
                "status": "FAILED",
                "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
                "error": f"dry_run timed out after {TIMEOUT_PER_STAGE_SECONDS}s",
            }
            if not overall_error:
                overall_error = "Stage 3 dry_run timed out."
        except Exception as exc:
            all_passed = False
            checks["dry_run"] = {
                "status": "FAILED",
                "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
                "error": str(exc),
            }
            if not overall_error:
                overall_error = f"Stage 3 dry_run failed: {exc!s}"

        # ---------------------------------------------------------
        # Stage 4: Abort Hook Protocol
        # ---------------------------------------------------------
        t0 = time.perf_counter()
        try:
            abort_res = await client.send_rpc_command(
                "abort",
                {"execution_id": "test_sanity_abort", "spid": 99999, "config": config},
                timeout=TIMEOUT_PER_STAGE_SECONDS,
            )
            latency_ms = round((time.perf_counter() - t0) * 1000, 2)
            checks["abort"] = {
                "status": "PASSED",
                "latency_ms": latency_ms,
                "details": f"Abort protocol verified (returned: {abort_res})",
            }
        except TimeoutError:
            all_passed = False
            checks["abort"] = {
                "status": "FAILED",
                "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
                "error": f"abort hook timed out after {TIMEOUT_PER_STAGE_SECONDS}s",
            }
            if not overall_error:
                overall_error = "Stage 4 abort hook timed out."
        except Exception as exc:
            all_passed = False
            checks["abort"] = {
                "status": "FAILED",
                "latency_ms": round((time.perf_counter() - t0) * 1000, 2),
                "error": str(exc),
            }
            if not overall_error:
                overall_error = f"Stage 4 abort failed: {exc!s}"

        # ---------------------------------------------------------
        # Consolidate and Save Certification Report
        # ---------------------------------------------------------
        badge = "CERTIFIED_READY" if all_passed else "COMPATIBILITY_WARNING"
        verified_at = utc_now().isoformat()

        report = {
            "plugin_id": plugin_id,
            "certified": all_passed,
            "badge": badge,
            "checks": checks,
            "verified_at": verified_at,
            "error": overall_error,
        }

        # Update SQLModel Entity
        profile.is_certified = all_passed
        profile.certification_report_json = json.dumps(report)
        profile.updated_at = utc_now()
        self.session.add(profile)
        self.session.commit()

        return report
