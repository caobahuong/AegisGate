"""Main Application Entrypoint for AegisGate Core.

Adheres strictly to python_clean_code.md:
- Lifespan context manager for startup & shutdown
- Dependency Injection
- CORS configured for Next.js Dashboard
- 100% Type Hints
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session

from core.config import settings
from core.database import engine, init_db
from core.engine.plugin_client import terminate_all_subprocesses
from core.engine.plugin_registry import PluginRegistry
from core.gateway.api_routes import router as api_router

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

    # Automatically discover manifests in plugins directory
    with Session(engine) as session:
        registry = PluginRegistry(session)
        loaded = registry.scan_and_load_manifests()
        logger.info("Discovered and registered %d plugin(s) from manifests", len(loaded))

    yield
    logger.info("Shutting down AegisGate Core Engine...")
    stopped = await terminate_all_subprocesses()
    logger.info("Stopped %d plugin worker process(es)", stopped)


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI Execution Proxy & Pluggable Harness Platform",
    lifespan=lifespan,
)

# Enable CORS for Next.js frontend (default http://localhost:3000)
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
