#!/usr/bin/env python3
"""Dumps the AegisGate FastAPI application OpenAPI schema to data/openapi.json.

Allows generating TypeScript definitions without running the uvicorn server.
"""

import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from core.config import settings
from core.main import app

OUTPUT_PATH = settings.BASE_DIR / "data" / "openapi.json"


def generate_openapi_spec() -> None:
    """Export the OpenAPI schema dictionary as formatted JSON."""
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    openapi_schema = app.openapi()
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(openapi_schema, f, indent=2)
    print(f"Exported OpenAPI schema to {OUTPUT_PATH}")


if __name__ == "__main__":
    generate_openapi_spec()
