# AegisGate Configuration Reference

This document provides a comprehensive specification of all runtime configuration parameters managed by `core.config.Settings` (Pydantic Settings).

Configuration variables are read from system environment variables or a `.env` file located in the repository root.

---

## Configuration Parameter Table

| Name | Type | Default | Meaning | When to Change |
| :--- | :--- | :--- | :--- | :--- |
| `APP_NAME` | `str` | `"AegisGate Core"` | Display identifier for the application instance in logs, responses, and Swagger docs. | Change when deploying white-labeled or enterprise-branded proxy instances. |
| `APP_VERSION` | `str` | `"1.0.0"` | Semantic version reported by the service and `/health` endpoint. | Bumped during release versions. |
| `DEBUG` | `bool` | `False` | Enables verbose SQL logging and stack traces in error responses. | Set to `true` during local debugging or unit testing; keep `false` in production. |
| `API_HOST` | `str` | `"127.0.0.1"` | Network interface IP to bind the FastAPI Uvicorn server to. | Keep `127.0.0.1` for local zero-trust usage; change if containerized inside Docker/K8s network. |
| `API_PORT` | `int` | `8000` | Network port for the FastAPI REST Gateway and SSE stream. | Change if port 8000 conflicts with another local service. |
| `MCP_PORT` | `int` | `8001` | Network port allocated for the standalone FastMCP service. | Change if running dedicated FastMCP listener on an alternative port. |
| `BASE_DIR` | `Path` | Root of repo | Absolute path to repository root containing `core/`. | Automatically resolved; override only if packaging into isolated execution roots. |
| `DATA_DIR` | `Path` | `<BASE_DIR>/data` | Directory where SQLite metadata and local storage artifacts are stored. | Change to redirect storage to a persistent volume or external mount. |
| `DATABASE_URL` | `str` | `"sqlite:///<BASE_DIR>/data/aegisgate.db"` | SQLAlchemy database connection string for AegisGate internal state. | Change to use an external SQLite path or alternative database engine. |
| `KNOWLEDGE_DOCS_DIR` | `Path` | `<BASE_DIR>/data/knowledge_docs` | Directory storing human-authored Markdown docs (`doc.md`, `skills.md`). | Change to point to a shared knowledge base or documentation volume. |
| `PLUGINS_DIR` | `Path` | `<BASE_DIR>/plugins` | Directory where target plugin manifests, adapters, and worker modules reside. | Change if plugins are mounted from an external plugin directory. |
| `READ_TIMEOUT_SECONDS` | `float` | `15.0` | Maximum execution duration allowed for read queries before triggering emergency abort. | Increase for complex analytical queries that are expected to take longer than 15s. |
| `WRITE_TIMEOUT_SECONDS` | `float` | `30.0` | Maximum execution duration allowed for write transactions before emergency abort. | Increase for batch updates or heavy writes requiring longer commit windows. |
| `DEFAULT_TIMEOUT_SECONDS` | `float` | `15.0` | Fallback timeout duration when query intent (READ/WRITE) cannot be classified. | Adjust if default unclassified queries need a different guardrail window. |
| `FAIL_CLOSED_ON_DRY_RUN_ERROR` | `bool` | `True` | When `true`, queries fail-closed (rejected) if plugin dry-run crashes; when `false`, forces manual review. | Keep `true` for zero-trust security; set `false` only during development of unstable plugins. |
| `PLUGIN_GIT_ALLOWED_HOSTS` | `list[str]` | `["github.com", "gitlab.com", "bitbucket.org"]` | Whitelist of HTTPS domains permitted for Git plugin installation. | Add internal company Git server domains (e.g., `git.internal.company.com`). |
| `PLUGIN_MAX_ZIP_BYTES` | `int` | `52428800` (50MB) | Maximum permitted file size for uploaded plugin ZIP packages. | Increase if plugins bundle large offline wheel dependencies or models. |
| `PLUGIN_MAX_UNZIPPED_BYTES` | `int` | `209715200` (200MB) | Maximum cumulative extracted disk size for an unzipped plugin. | Increase if plugin virtual environments or assets exceed 200MB. |
| `PLUGIN_MAX_ZIP_ENTRIES` | `int` | `5000` | Maximum number of individual file entries allowed inside a plugin ZIP. | Increase for plugins with deep dependency trees. |
| `PLUGIN_GIT_CLONE_TIMEOUT_SECONDS` | `float` | `60.0` | Timeout in seconds for Git clone subprocess during remote plugin install. | Increase on slower network links. |
| `PLUGIN_MAX_MESSAGE_BYTES` | `int` | `67108864` (64MB) | Maximum allowed size of a single JSON-RPC message over Stdio from a plugin worker. | Increase if query results or schema catalogs exceed 64MB. |
| `AUTO_APPROVAL_DEFAULT` | `bool` | `False` | Default state of the Auto Approval toggle when initialized for the first time. | Set `true` if you want all clean dry-run queries to auto-execute without human review. |
| `SSE_HEARTBEAT_INTERVAL_SECONDS` | `float` | `2.0` | Frequency in seconds of SSE heartbeat keep-alive events sent to the frontend dashboard. | Increase to reduce network traffic or decrease for higher-resolution liveliness checks. |

---

## Frontend Environment Variables

Located in `frontend/.env.local` (see `frontend/.env.example`):

| Variable | Default | Purpose |
| :--- | :--- | :--- |
| `NEXT_PUBLIC_API_URL` | `http://127.0.0.1:8000` | Base URL of the AegisGate Core REST API Gateway. |
| `NEXT_PUBLIC_SSE_URL` | `http://127.0.0.1:8000/api/monitor/events` | SSE endpoint URL for real-time state streaming to the Next.js dashboard. |
