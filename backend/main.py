"""Backend root entrypoint delegating to core.main."""

from core.main import app

__all__ = ["app"]

if __name__ == "__main__":
    import uvicorn

    from core.config import settings

    uvicorn.run("core.main:app", host=settings.API_HOST, port=settings.API_PORT, reload=settings.DEBUG)
