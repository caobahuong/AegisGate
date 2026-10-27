"""System Settings Store for managing runtime configuration flags.

Adheres strictly to python_clean_code.md:
- Full type hinting
"""

from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from core.database import SystemSetting, utc_now


class SettingStore:
    """Manages persistent system configuration in SQLite with session-scoped caching."""

    def __init__(self, session: Session) -> None:
        self.session: Session = session
        self._settings_cache: dict[str, str] = {}

    def get_setting(self, key: str, default: str = "") -> str:
        """Fetch setting value by key."""
        if key in self._settings_cache:
            return self._settings_cache[key]

        statement = select(SystemSetting).where(SystemSetting.key == key)
        setting = self.session.exec(statement).first()
        if not setting:
            return default

        self._settings_cache[key] = setting.value
        return setting.value

    def set_setting(self, key: str, value: str, description: str | None = None) -> str:
        """Set or update setting value with race-condition resilient upsert."""
        statement = select(SystemSetting).where(SystemSetting.key == key)
        setting = self.session.exec(statement).first()
        if setting:
            setting.value = value
            if description:
                setting.description = description
            setting.updated_at = utc_now()
            self.session.add(setting)
        else:
            setting = SystemSetting(
                key=key,
                value=value,
                description=description,
                updated_at=utc_now(),
            )
            self.session.add(setting)

        try:
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            # Concurrent insertion won race; update the winning record
            existing = self.session.exec(select(SystemSetting).where(SystemSetting.key == key)).first()
            if existing:
                existing.value = value
                if description:
                    existing.description = description
                existing.updated_at = utc_now()
                self.session.add(existing)
                self.session.commit()

        self._settings_cache.clear()
        return value

    def is_auto_approval_enabled(self) -> bool:
        """Check if Auto Approval Mode is enabled."""
        val = self.get_setting("auto_approval_mode", "false")
        return val.lower() in ("true", "1", "yes")

    def set_auto_approval(self, enabled: bool) -> bool:
        """Update Auto Approval Mode status."""
        self.set_setting("auto_approval_mode", "true" if enabled else "false")
        return enabled
