"""System Settings Store for managing runtime configuration flags.

Adheres strictly to python_clean_code.md:
- Full type hinting
"""

from typing import Optional
from sqlmodel import Session, select
from core.database import SystemSetting, utc_now


class SettingStore:
    """Manages persistent system configuration in SQLite."""

    def __init__(self, session: Session) -> None:
        self.session: Session = session

    def get_setting(self, key: str, default: str = "") -> str:
        """Fetch setting value by key."""
        statement = select(SystemSetting).where(SystemSetting.key == key)
        setting = self.session.exec(statement).first()
        if not setting:
            return default
        return setting.value

    def set_setting(self, key: str, value: str, description: Optional[str] = None) -> str:
        """Set or update setting value."""
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
        self.session.commit()
        return value

    def is_auto_approval_enabled(self) -> bool:
        """Check if Auto Approval Mode is enabled."""
        val = self.get_setting("auto_approval_mode", "false")
        return val.lower() in ("true", "1", "yes")

    def set_auto_approval(self, enabled: bool) -> bool:
        """Update Auto Approval Mode status."""
        self.set_setting("auto_approval_mode", "true" if enabled else "false")
        return enabled

