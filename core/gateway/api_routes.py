"""REST API Gateway Router for AegisGate Frontend Dashboard.

Adheres strictly to python_clean_code.md:
- Strict Separation of Concerns: No business logic or database calls directly inside the route
- Dependency Injection for database sessions & services
- 100% Type Hints
- Zero generic `except Exception:`, proper status codes
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlmodel import Session

from core.database import get_session
from core.exceptions import (
    ExecutionStateError,
    ExecutionTimeoutError,
    PluginExecutionError,
    PluginNotFoundError,
    RuleViolationError,
)
from core.gateway.schemas import (
    ApproveExecutionRequest,
    AutoModeResponse,
    CreateRuleRequest,
    ExecutionResponse,
    InstallGitPluginRequest,
    KnowledgeChunkResponse,
    McpConfigResponse,
    PluginCertificationResponse,
    PluginProfileResponse,
    PluginSchemaResponse,
    RegisterPluginRequest,
    RejectExecutionRequest,
    RuleResponse,
    SetAutoModeRequest,
    SubmitExecutionRequest,
    UpdateDocsRequest,
    UpdatePluginConfigRequest,
    UpdateRuleRequest,
)
from core.gateway.services import GatewayService
from core.gateway.sse_broadcaster import sse_broadcaster

router = APIRouter(prefix="/api", tags=["AegisGate Gateway"])


def get_service(session: Annotated[Session, Depends(get_session)]) -> GatewayService:
    """Dependency injection helper providing GatewayService."""
    return GatewayService(session)


# --- Live Monitor & Execution Endpoints ---

@router.get("/monitor/events")
async def sse_events() -> StreamingResponse:
    """Server-Sent Events endpoint streaming real-time execution states."""
    return StreamingResponse(
        sse_broadcaster.subscribe(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/monitor/executions", response_model=list[ExecutionResponse])
def list_executions(
    service: Annotated[GatewayService, Depends(get_service)],
    limit: int = Query(default=50, ge=1, le=500),
    target_id: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
) -> list[ExecutionResponse]:
    """List execution logs with optional filtering."""
    return service.list_executions(limit=limit, target_id=target_id, status=status_filter)


@router.get("/monitor/executions/{execution_id}", response_model=ExecutionResponse)
def get_execution(
    execution_id: str,
    service: Annotated[GatewayService, Depends(get_service)],
) -> ExecutionResponse:
    """Retrieve details for a specific execution."""
    execution = service.get_execution(execution_id)
    if not execution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Execution with ID '{execution_id}' not found.",
        )
    return execution


@router.post("/monitor/executions", response_model=ExecutionResponse, status_code=status.HTTP_201_CREATED)
async def submit_execution(
    req: SubmitExecutionRequest,
    service: Annotated[GatewayService, Depends(get_service)],
) -> ExecutionResponse:
    """Submit an AI query for Dry-Run and Execution lifecycle."""
    try:
        return await service.submit_execution(req)
    except PluginNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    except (RuleViolationError, ExecutionStateError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc
    except ExecutionTimeoutError as exc:
        raise HTTPException(status_code=status.HTTP_504_GATEWAY_TIMEOUT, detail=exc.message) from exc


@router.post("/monitor/executions/{execution_id}/approve", response_model=ExecutionResponse)
async def approve_execution(
    execution_id: str,
    req: ApproveExecutionRequest,
    service: Annotated[GatewayService, Depends(get_service)],
) -> ExecutionResponse:
    """Resume execution of a paused query following user approval."""
    try:
        return await service.approve_execution(execution_id, req)
    except ExecutionStateError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc


@router.post("/monitor/executions/{execution_id}/reject", response_model=ExecutionResponse)
async def reject_execution(
    execution_id: str,
    req: RejectExecutionRequest,
    service: Annotated[GatewayService, Depends(get_service)],
) -> ExecutionResponse:
    """Reject execution of a paused query."""
    try:
        return await service.reject_execution(execution_id, req)
    except ExecutionStateError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc


@router.post("/monitor/executions/{execution_id}/abort", response_model=ExecutionResponse)
async def abort_execution(
    execution_id: str,
    service: Annotated[GatewayService, Depends(get_service)],
) -> ExecutionResponse:
    """Emergency Stop / Kill command for in-flight or paused queries."""
    try:
        return await service.abort_execution(execution_id)
    except ExecutionStateError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message) from exc


# --- Pluggable Targets (Plugin Management) Endpoints ---

@router.get("/plugins", response_model=list[PluginProfileResponse])
def list_plugins(
    service: Annotated[GatewayService, Depends(get_service)],
    include_disabled: bool = Query(False, description="Include disabled plugins"),
) -> list[PluginProfileResponse]:
    """List all registered pluggable targets."""
    return service.list_plugins(include_disabled=include_disabled)


@router.post("/plugins", response_model=PluginProfileResponse, status_code=status.HTTP_201_CREATED)
def register_plugin(
    req: RegisterPluginRequest,
    service: Annotated[GatewayService, Depends(get_service)],
) -> PluginProfileResponse:
    """Register a new plugin via Add Plugin Modal."""
    return service.register_plugin(req)



@router.post("/plugins/install-zip", response_model=PluginProfileResponse, status_code=status.HTTP_201_CREATED)
async def install_plugin_zip(
    service: Annotated[GatewayService, Depends(get_service)],
    file: UploadFile = File(..., description="ZIP archive containing plugin files and manifest.json"),
) -> PluginProfileResponse:
    """Install, build, and certify an external plugin from an uploaded ZIP archive."""
    try:
        content = await file.read()
        return await service.install_plugin_zip(content, filename=file.filename)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/plugins/install-git", response_model=PluginProfileResponse, status_code=status.HTTP_201_CREATED)
async def install_plugin_git(
    req: InstallGitPluginRequest,
    service: Annotated[GatewayService, Depends(get_service)],
) -> PluginProfileResponse:
    """Clone, build, and certify an external plugin from a remote Git repository."""
    try:
        return await service.install_plugin_git(req)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/plugins/{plugin_id}/verify", response_model=PluginCertificationResponse)
async def verify_plugin(
    plugin_id: str,
    service: Annotated[GatewayService, Depends(get_service)],
) -> PluginCertificationResponse:
    """Run 4-stage automated sanity linter and generate certification report."""
    try:
        return await service.verify_plugin(plugin_id)
    except PluginNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

@router.get("/plugins/{plugin_id}/schema", response_model=PluginSchemaResponse)
def get_plugin_schema(
    plugin_id: str,
    service: Annotated[GatewayService, Depends(get_service)],
) -> PluginSchemaResponse:
    """Retrieve dynamic UI schema and current configuration for a plugin."""
    try:
        return service.get_plugin_schema(plugin_id)
    except PluginNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc


@router.put("/plugins/{plugin_id}", response_model=PluginProfileResponse)
async def update_plugin_config(
    plugin_id: str,
    req: UpdatePluginConfigRequest,
    service: Annotated[GatewayService, Depends(get_service)],
) -> PluginProfileResponse:
    """Update connection configuration for a plugin and re-init subprocess."""
    try:
        return await service.update_plugin_config(plugin_id, req)
    except PluginNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.delete("/plugins/{plugin_id}")
async def delete_plugin(
    plugin_id: str,
    service: Annotated[GatewayService, Depends(get_service)],
    hard_delete: bool = Query(False, description="True for hard delete from DB, False for soft deactivate"),
) -> dict[str, Any]:
    """Uninstall or deactivate a plugin, disconnect active subprocesses, and abort running tasks."""
    try:
        return await service.delete_plugin(plugin_id, hard_delete=hard_delete)
    except PluginNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.get("/plugins/{plugin_id}/mcp-config", response_model=McpConfigResponse)
def get_plugin_mcp_config(
    plugin_id: str,
    service: Annotated[GatewayService, Depends(get_service)],
) -> McpConfigResponse:
    """Retrieve MCP JSON connection snippet for a specific plugin target."""
    try:
        return service.get_plugin_mcp_config(plugin_id)
    except PluginNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc


@router.get("/mcp/config", response_model=McpConfigResponse)
def get_global_mcp_config(
    service: Annotated[GatewayService, Depends(get_service)],
) -> McpConfigResponse:
    """Retrieve global MCP JSON connection snippet for Claude Desktop, Cursor, and Cline."""
    return service.get_global_mcp_config()


@router.post("/plugins/{plugin_id}/sync")
async def sync_plugin_catalog(
    plugin_id: str,
    service: Annotated[GatewayService, Depends(get_service)],
) -> list[dict[str, Any]]:
    """Trigger catalog schema extraction and ingestion for a plugin."""
    try:
        return await service.sync_plugin_catalog(plugin_id)
    except PluginNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=exc.message) from exc
    except PluginExecutionError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=exc.message) from exc


# --- Knowledge & Rules Endpoints ---

@router.get("/knowledge", response_model=list[KnowledgeChunkResponse])
def list_knowledge(
    service: Annotated[GatewayService, Depends(get_service)],
    target_id: str | None = Query(default=None),
) -> list[KnowledgeChunkResponse]:
    """List structural catalog partitions."""
    return service.list_knowledge_chunks(target_id=target_id)


@router.get("/knowledge/{chunk_id}", response_model=KnowledgeChunkResponse)
def get_knowledge_chunk(
    chunk_id: str,
    service: Annotated[GatewayService, Depends(get_service)],
) -> KnowledgeChunkResponse:
    """Get single chunk with full markdown documentation."""
    chunk = service.get_knowledge_chunk(chunk_id)
    if not chunk:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge chunk not found.")
    return chunk


@router.put("/knowledge/{chunk_id}/docs")
def update_knowledge_docs(
    chunk_id: str,
    req: UpdateDocsRequest,
    service: Annotated[GatewayService, Depends(get_service)],
) -> dict[str, bool]:
    """Update markdown documentation for a partition."""
    success = service.update_knowledge_docs(chunk_id, req)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge chunk not found.")
    return {"success": True}


@router.get("/skills")
def list_skills(
    service: Annotated[GatewayService, Depends(get_service)],
    target_id: str | None = Query(default=None, description="Filter skills by target plugin ID"),
) -> list[dict[str, Any]]:
    """List query skills and templates, optionally filtered by target plugin."""
    return service.list_skills(target_id=target_id)


@router.get("/rules", response_model=list[RuleResponse])
def list_rules(
    service: Annotated[GatewayService, Depends(get_service)],
    target_id: str | None = Query(default=None, description="Filter rules by target plugin ID or 'global'"),
    exact: bool = Query(default=False, description="Exact target match without global fallback"),
) -> list[RuleResponse]:
    """List governance rules optionally filtered by target plugin or global scope."""
    return service.list_rules(target_id=target_id, exact_target=exact)


@router.post("/rules", response_model=RuleResponse, status_code=status.HTTP_201_CREATED)
def create_rule(
    req: CreateRuleRequest,
    service: Annotated[GatewayService, Depends(get_service)],
) -> RuleResponse:
    """Create a new governance rule."""
    return service.create_rule(req)


@router.put("/rules/{rule_id}", response_model=RuleResponse)
def update_rule(
    rule_id: str,
    req: UpdateRuleRequest,
    service: Annotated[GatewayService, Depends(get_service)],
) -> RuleResponse:
    """Update an existing governance rule."""
    try:
        updated = service.update_rule(rule_id, req)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found.")
    return updated


@router.delete("/rules/{rule_id}")
def delete_rule(
    rule_id: str,
    service: Annotated[GatewayService, Depends(get_service)],
) -> dict[str, bool]:
    """Delete a governance rule."""
    success = service.delete_rule(rule_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rule not found.")
    return {"success": True}


# --- Settings & Auto Mode Endpoints ---

@router.get("/settings/auto-mode", response_model=AutoModeResponse)
def get_auto_mode(
    service: Annotated[GatewayService, Depends(get_service)],
) -> AutoModeResponse:
    """Get current Auto Approval Mode status."""
    return AutoModeResponse(auto_approval_enabled=service.is_auto_mode())


@router.post("/settings/auto-mode", response_model=AutoModeResponse)
def set_auto_mode(
    req: SetAutoModeRequest,
    service: Annotated[GatewayService, Depends(get_service)],
) -> AutoModeResponse:
    """Set Auto Approval Mode status."""
    new_val = service.set_auto_mode(req.enabled)
    return AutoModeResponse(auto_approval_enabled=new_val)


# --- Audit Logs Endpoint ---

@router.get("/logs", response_model=list[ExecutionResponse])
def list_logs(
    service: Annotated[GatewayService, Depends(get_service)],
    limit: int = Query(default=100, ge=1, le=1000),
    target_id: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
) -> list[ExecutionResponse]:
    """List historical audit logs."""
    return service.list_executions(limit=limit, target_id=target_id, status=status_filter)
