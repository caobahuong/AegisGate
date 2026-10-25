"""Drift guard tests ensuring Settings, .env.example, and docs/configuration.md stay in sync.

Adheres to python_clean_code.md:
- Automated guardrail against documentation drift
- 100% Type Hints
"""

from pathlib import Path
import re
from core.config import Settings


def test_settings_drift_guard() -> None:
    """Ensure every Settings field is documented in .env.example and docs/configuration.md."""
    base_dir = Path(__file__).resolve().parent.parent
    env_example_path = base_dir / ".env.example"
    docs_config_path = base_dir / "docs" / "configuration.md"

    assert env_example_path.exists(), ".env.example file must exist at repo root"
    assert docs_config_path.exists(), "docs/configuration.md file must exist"

    env_content = env_example_path.read_text(encoding="utf-8")
    docs_content = docs_config_path.read_text(encoding="utf-8")

    settings_fields = set(Settings.model_fields.keys())
    assert len(settings_fields) > 0, "Settings must have fields defined"

    # 1. Check every field is in .env.example
    # Pattern matches line starting with optional # and the variable name followed by =
    missing_in_env: list[str] = []
    for field in sorted(settings_fields):
        # Matches either FIELD= or # FIELD=
        pattern = rf"(?:^|\n)\s*#?\s*{re.escape(field)}="
        if not re.search(pattern, env_content):
            missing_in_env.append(field)

    assert not missing_in_env, (
        f"The following Settings field(s) are missing from .env.example: {missing_in_env}. "
        "Update .env.example to match core/config.py."
    )

    # 2. Check every field is documented in docs/configuration.md
    missing_in_docs: list[str] = []
    for field in sorted(settings_fields):
        # Look for `FIELD` in the markdown table
        pattern = rf"`{re.escape(field)}`"
        if not re.search(pattern, docs_content):
            missing_in_docs.append(field)

    assert not missing_in_docs, (
        f"The following Settings field(s) are missing from docs/configuration.md: {missing_in_docs}. "
        "Update docs/configuration.md to document all fields."
    )

