"""Pydantic schemas for AegisGate REST API Gateway requests and responses.

Adheres to python_clean_code.md:
- 100% Type Hints
- Strict validation models
"""

from typing import Any, Optional, Union
from pydantic import BaseModel, Field


# --- Monitor & Execution Schemas ---

class SubmitExecutionRequest(BaseModel):
    """Payload for submitting an AI query for execution."""
    target_id: str = Field(description="Target plugin identifier")
    query: str = Field(description="SQL or command query string")
    reasoning: str = Field(default="", description="AI intent or chain of thought reasoning")


class ExecutionResponse(BaseModel):
    """Response representing an execution's full state."""
    id: str
    target_id: str
    query: str
    query_type: str
    reasoning: str
    status: str
    explain_plan: Optional[Any] = None
    violations: list[str] = Field(default_factory=list)
    execution_time_ms: Optional[float] = None
    auto_approved: bool = False
    approved_by: Optional[str] = None
    result_summary: Optional[Any] = None
    error_message: Optional[str] = None
    spid: Optional[int] = None
    created_at: str
    finished_at: Optional[str] = None


class ApproveExecutionRequest(BaseModel):
    """Payload for approving and resuming a paused execution."""
    approved_by: str = Field(default="Admin", description="User or approver identifier")


class RejectExecutionRequest(BaseModel):
    """Payload for rejecting an execution."""
    rejected_by: str = Field(default="Admin")
    reason: str = Field(default="Rejected by admin review")


# --- Plugin Schemas ---

class RegisterPluginRequest(BaseModel):
    """Payload for registering a new plugin via Add Plugin Modal."""
    id: str = Field(description="Unique plugin key (e.g. sqlserver_prod)")
    name: str = Field(description="Display name")
    driver: str = Field(description="Driver identifier e.g. pyodbc/mssql")
    entrypoint: str = Field(description="Command to invoke plugin subprocess")
    dry_run_command: str = Field(default="SET SHOWPLAN_XML ON")
    abort_command: str = Field(default="KILL {spid}")
    config: dict[str, Any] = Field(default_factory=dict)


class PluginProfileResponse(BaseModel):
    """Plugin profile data for UI rendering."""
    id: str
    name: str
    driver: str
    entrypoint: str
    dry_run_command: str
    abort_command: str
    config: dict[str, Any]
    status: str
    latency_ms: float
    active_sessions_count: int
    created_at: str
    updated_at: str


# --- Knowledge Schemas ---

class KnowledgeChunkResponse(BaseModel):
    """Knowledge chunk metadata and doc references."""
    id: str
    target_id: str
    partition_key: str
    title: str
    catalog: Union[dict[str, Any], list[Any], Any]
    doc_content: Optional[str] = None
    skills_content: Optional[str] = None
    created_at: str
    updated_at: str


class UpdateDocsRequest(BaseModel):
    """Payload for updating doc.md and skills.md markdown text."""
    doc_content: Optional[str] = None
    skills_content: Optional[str] = None


# --- Rule Schemas ---

class CreateRuleRequest(BaseModel):
    """Payload for creating a governance rule."""
    id: str
    name: str
    target_id: Optional[str] = None
    rule_type: str = Field(description="FORBID_JOIN | FORBID_TABLE_SCAN | MAX_EXECUTION_TIME | CUSTOM")
    expression: str
    description: str = ""
    severity: str = "HIGH"
    is_active: bool = True


class UpdateRuleRequest(BaseModel):
    """Payload for updating an existing rule."""
    name: Optional[str] = None
    target_id: Optional[str] = None
    rule_type: Optional[str] = None
    expression: Optional[str] = None
    description: Optional[str] = None
    severity: Optional[str] = None
    is_active: Optional[bool] = None


class RuleResponse(BaseModel):
    """Governance rule representation."""
    id: str
    name: str
    target_id: Optional[str] = None
    rule_type: str
    expression: str
    description: str
    severity: str
    is_active: bool
    created_at: str


# --- System Settings Schemas ---

class AutoModeResponse(BaseModel):
    """Auto approval mode status."""
    auto_approval_enabled: bool


class SetAutoModeRequest(BaseModel):
    """Payload to toggle auto approval mode."""
    enabled: bool
