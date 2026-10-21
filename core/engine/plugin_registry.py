"""Plugin Registry for discovering, registering, and managing plugins in AegisGate.

Adheres strictly to python_clean_code.md:
- 100% Type Hints
- Clean separation of concerns
- Custom exceptions
"""

import json
from pathlib import Path
from typing import Any, Optional
from sqlmodel import Session, select
from core.config import settings
from core.database import PluginProfile, utc_now
from core.engine.plugin_client import PluginSubprocessClient
from core.exceptions import PluginNotFoundError


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

    def list_profiles(self) -> list[PluginProfile]:
        """List all registered plugin profiles."""
        return list(self.session.exec(select(PluginProfile)).all())

    def update_metrics(
        self,
        plugin_id: str,
        latency_ms: Optional[float] = None,
        active_sessions_count: Optional[int] = None,
        status: Optional[str] = None,
    ) -> Optional[PluginProfile]:
        """Update live operational metrics for a plugin."""
        profile = self.session.exec(
            select(PluginProfile).where(PluginProfile.id == plugin_id)
        ).first()
        if not profile:
            return None

        if latency_ms is not None:
            # Simple running average
            if profile.latency_ms > 0:
                profile.latency_ms = round((profile.latency_ms + latency_ms) / 2.0, 2)
            else:
                profile.latency_ms = round(latency_ms, 2)

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

    def scan_and_load_manifests(self, plugins_dir: Optional[Path] = None) -> list[PluginProfile]:
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

                profile = PluginProfile(
                    id=plugin_id,
                    name=manifest_data.get("name", plugin_id),
                    driver=manifest_data.get("driver", "generic"),
                    entrypoint=manifest_data.get("entrypoint", f"python {manifest_path.parent / 'adapter.py'}"),
                    dry_run_command=manifest_data.get("dry_run_command", "EXPLAIN"),
                    abort_command=manifest_data.get("abort_command", "KILL {spid}"),
                    config_json=json.dumps(manifest_data.get("default_config", {})),
                    status="active",
                )
                registered = self.register_profile(profile)
                loaded.append(registered)
            except Exception as exc:
                # Log error loading specific manifest, but continue scanning
                continue

        return loaded

