"""Plugin Registry and Lifecycle Management for AegisGate.

Adheres strictly to python_clean_code.md:
- Full type hinting
- Session dependency injection
- Decoupled from third-party vendor dialects
"""

import json
import logging
from pathlib import Path
from typing import Any

from sqlmodel import Session, select

from core.config import settings
from core.database import PluginProfile, utc_now
from core.engine.plugin_client import PluginSubprocessClient
from core.exceptions import PluginNotFoundError

logger = logging.getLogger(__name__)


class PluginRegistry:
    """Discovers plugins from manifests and manages their profiles in DB."""

    def __init__(self, session: Session) -> None:
        self.session: Session = session

    def register_profile(self, profile: PluginProfile) -> PluginProfile:
        """Register or update a plugin profile."""
        existing = self.session.exec(
            select(PluginProfile).where(PluginProfile.id == profile.id)
        ).first()

        if existing:
            existing.name = profile.name
            existing.driver = profile.driver
            existing.entrypoint = profile.entrypoint
            existing.dry_run_command = profile.dry_run_command
            existing.abort_command = profile.abort_command
            if profile.ui_schema_json and profile.ui_schema_json != "[]":
                existing.ui_schema_json = profile.ui_schema_json
            if profile.custom_card_json and profile.custom_card_json != "{}":
                existing.custom_card_json = profile.custom_card_json
            if profile.config_json and profile.config_json != "{}":
                existing.config_json = profile.config_json
            existing.status = profile.status
            existing.updated_at = utc_now()
            self.session.add(existing)
            self.session.commit()
            self.session.refresh(existing)
            return existing

        profile.created_at = utc_now()
        profile.updated_at = utc_now()
        self.session.add(profile)
        self.session.commit()
        self.session.refresh(profile)
        return profile

    def get_profile(self, plugin_id: str) -> PluginProfile:
        """Fetch plugin profile or raise PluginNotFoundError."""
        profile = self.session.exec(
            select(PluginProfile).where(PluginProfile.id == plugin_id)
        ).first()
        if not profile:
            raise PluginNotFoundError(f"Plugin with ID '{plugin_id}' not found in registry.")
        return profile

    def list_profiles(self, include_disabled: bool = False) -> list[PluginProfile]:
        """List registered plugin profiles."""
        if include_disabled:
            return list(self.session.exec(select(PluginProfile)).all())
        return list(
            self.session.exec(
                select(PluginProfile).where(PluginProfile.status != "disabled")
            ).all()
        )

    def unregister_profile(self, plugin_id: str, hard_delete: bool = False) -> PluginProfile:
        """Unregister or deactivate a plugin profile.
        
        If hard_delete is True, permanently deletes the record from DB.
        If False, sets status="disabled" to preserve history and prevent auto-discovery reactivation.
        """
        profile = self.get_profile(plugin_id)
        if hard_delete:
            self.session.delete(profile)
            self.session.commit()
            return profile

        profile.status = "disabled"
        profile.updated_at = utc_now()
        self.session.add(profile)
        self.session.commit()
        self.session.refresh(profile)
        return profile

    def update_metrics(
        self,
        plugin_id: str,
        latency_ms: float | None = None,
        active_sessions_count: int | None = None,
        status: str | None = None,
    ) -> PluginProfile:
        """Update live operational telemetry and health metrics."""
        profile = self.get_profile(plugin_id)
        if latency_ms is not None:
            profile.latency_ms = latency_ms
        if active_sessions_count is not None:
            profile.active_sessions_count = active_sessions_count
        if status is not None:
            profile.status = status
        profile.updated_at = utc_now()
        self.session.add(profile)
        self.session.commit()
        self.session.refresh(profile)
        return profile

    def get_client(self, plugin_id: str) -> PluginSubprocessClient:
        """Create a PluginSubprocessClient for the target plugin."""
        profile = self.get_profile(plugin_id)
        return PluginSubprocessClient(
            entrypoint_cmd=profile.entrypoint,
            working_dir=str(settings.BASE_DIR),
        )

    def scan_and_load_manifests(self, plugins_dir: Path | None = None) -> list[PluginProfile]:
        """Scan plugins directory for plugin_manifest.json files and register them."""
        target_dir = plugins_dir or settings.PLUGINS_DIR
        if not target_dir.exists():
            return []

        loaded: list[PluginProfile] = []
        for manifest_path in target_dir.glob("*/plugin_manifest.json"):
            try:
                content = manifest_path.read_text(encoding="utf-8")
                manifest_data: dict[str, Any] = json.loads(content)
                plugin_id = manifest_data["id"]

                ui_schema = manifest_data.get("ui_schema", [])
                custom_card = manifest_data.get("custom_card", {})
                default_config = manifest_data.get("default_config", {})

                # Check if already in db to preserve user configuration and disabled status
                existing = self.session.exec(
                    select(PluginProfile).where(PluginProfile.id == plugin_id)
                ).first()

                if existing and existing.status == "disabled":
                    logger.info("Plugin '%s' is marked as disabled in DB; skipping auto-activation.", plugin_id)
                    continue

                config_to_save = json.dumps(default_config)
                if existing and existing.config_json and existing.config_json != "{}":
                    config_to_save = existing.config_json

                profile = PluginProfile(
                    id=plugin_id,
                    name=manifest_data.get("name", plugin_id),
                    driver=manifest_data.get("driver", "generic"),
                    entrypoint=manifest_data.get("entrypoint", f"python {manifest_path.parent / 'adapter.py'}"),
                    dry_run_command=manifest_data.get("dry_run_command", "EXPLAIN"),
                    abort_command=manifest_data.get("abort_command", "KILL {spid}"),
                    config_json=config_to_save,
                    ui_schema_json=json.dumps(ui_schema),
                    custom_card_json=json.dumps(custom_card),
                    status="active",
                )
                registered = self.register_profile(profile)
                loaded.append(registered)
            except Exception as exc:
                logger.warning("Error reading manifest %s: %s", manifest_path, exc)
                continue

        return loaded
