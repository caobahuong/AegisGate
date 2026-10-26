"""Main Application Entrypoint for AegisGate Core.

Adheres strictly to python_clean_code.md:
- Lifespan context manager for startup & shutdown
- Dependency Injection
- CORS configured for Next.js Dashboard
- 100% Type Hints
"""

import logging
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse, Response
from sqlmodel import Session

from core.config import settings
from core.database import engine, init_db
from core.engine.cluster import cluster_manager
from core.engine.plugin_client import terminate_all_subprocesses
from core.engine.plugin_registry import PluginRegistry
from core.gateway.api_routes import router as api_router
from core.gateway.event_bus import get_event_bus

logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("AegisGate")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and shutdown lifespan handler."""
    logger.info("Starting AegisGate Core Engine...")
    init_db()

    # Start event bus (DbOutboxBus tailer if enabled)
    bus = get_event_bus()
    await bus.start()

    # Start cluster manager (heartbeats, stale execution janitor, cross-process abort)
    await cluster_manager.start()

    # Automatically discover manifests in plugins directory
    with Session(engine) as session:
        registry = PluginRegistry(session)
        loaded = registry.scan_and_load_manifests()
        logger.info("Discovered and registered %d plugin(s) from manifests", len(loaded))

    yield
    logger.info("Shutting down AegisGate Core Engine...")
    await cluster_manager.stop()
    await bus.stop()
    stopped = await terminate_all_subprocesses()
    logger.info("Stopped %d plugin worker process(es)", stopped)


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI Execution Proxy & Pluggable Harness Platform",
    lifespan=lifespan,
)

# 1. TrustedHostMiddleware: Prevents DNS Rebinding attacks
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=[
        "localhost",
        "127.0.0.1",
        "testserver",
        settings.API_HOST,
        "*.localhost",
    ],
)

# 2. Enable CORS for Next.js frontend (default http://localhost:3000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_guard_middleware(
    request: Request,
    call_next: Callable[[Request], AsyncGenerator[Response, None] | Any],
) -> Response:
    """Security guard middleware: CSRF defense, body size limit, and security headers."""
    # CSRF Protection via Fetch Metadata (Sec-Fetch-Site)
    sec_fetch_site = request.headers.get("sec-fetch-site")
    if sec_fetch_site == "cross-site" and request.method in ("POST", "PUT", "DELETE", "PATCH"):
        return JSONResponse(
            status_code=403,
            content={"detail": "Cross-site state-changing request blocked (CSRF protection)."},
        )

    # Request body size limits
    max_bytes = (
        settings.PLUGIN_MAX_ZIP_BYTES + 5 * 1024 * 1024
        if request.url.path == "/api/plugins/install-zip"
        else 10 * 1024 * 1024
    )
    content_length = request.headers.get("content-length")
    if content_length and content_length.isdigit() and int(content_length) > max_bytes:
        return JSONResponse(
            status_code=413,
            content={"detail": f"Payload too large. Maximum allowed size is {max_bytes // (1024 * 1024)} MB."},
        )

    response: Response = await call_next(request)

    # Security headers
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")

    return response


# Mount REST API
app.include_router(api_router)


@app.get("/health", tags=["System"])
def health_check() -> dict[str, str]:
    """Health check endpoint for platform monitoring."""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "core.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG,
    )
