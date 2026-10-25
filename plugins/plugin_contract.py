"""Standard Plugin Contract and JSON-RPC 2.0 protocol specifications for AegisGate.

Every AegisGate plugin conforms to this contract over Stdio / Subprocess IPC.
Adheres strictly to python_clean_code.md:
- 100% Type Hints
- Strict Pydantic models for all RPC payloads
"""

from abc import ABC, abstractmethod
from typing import Any, Literal, Optional, Union
from pydantic import BaseModel, Field


# --- JSON-RPC 2.0 Primitive Specifications ---

class JsonRpcRequest(BaseModel):
    """JSON-RPC 2.0 Request envelope."""
    jsonrpc: Literal["2.0"] = "2.0"
    method: str
    params: dict[str, Any] = Field(default_factory=dict)
    id: Union[int, str]


class JsonRpcErrorPayload(BaseModel):
    """JSON-RPC 2.0 Error descriptor."""
    code: int
    message: str
    data: Optional[Any] = None


class JsonRpcResponse(BaseModel):
    """JSON-RPC 2.0 Response envelope."""
    jsonrpc: Literal["2.0"] = "2.0"
    result: Optional[Any] = None
    error: Optional[JsonRpcErrorPayload] = None
    id: Optional[Union[int, str]] = None


# --- Standard Domain Payloads for the Contract Ports ---

# 1. Sync Knowledge Port
class ColumnSchema(BaseModel):
    """Column metadata representation."""
    name: str
    data_type: str
    is_nullable: bool = True
    is_primary_key: bool = False
    description: Optional[str] = None


class IndexSchema(BaseModel):
    """Index metadata representation."""
    name: str
    columns: list[str]
    is_unique: bool = False


class TableSchema(BaseModel):
    """Table structure representation."""
    name: str
    schema_name: str = "dbo"
    columns: list[ColumnSchema] = Field(default_factory=list)
    indexes: list[IndexSchema] = Field(default_factory=list)
    row_count_estimate: Optional[int] = None
    description: Optional[str] = None


class PartitionSchema(BaseModel):
    """Chunked partition of database tables."""
    partition_key: str
    title: str
    tables: list[TableSchema] = Field(default_factory=list)


class SyncKnowledgeParams(BaseModel):
    """Parameters passed to sync_knowledge."""
    config: dict[str, Any] = Field(default_factory=dict)


class SyncKnowledgeResult(BaseModel):
    """Payload returned by sync_knowledge."""
    partitions: list[PartitionSchema] = Field(default_factory=list)
    target_id: str
    timestamp: str


# 2. Dry-Run Port
class DryRunParams(BaseModel):
    """Parameters passed to dry_run."""
    query: str
    rules: list[dict[str, Any]] = Field(default_factory=list)


class DryRunResult(BaseModel):
    """Payload returned by dry_run."""
    is_valid: bool
    violations: list[str] = Field(default_factory=list)
    explain_plan: Union[dict[str, Any], str] = Field(default_factory=dict)
    estimated_time_ms: float = 0.0
    query_type: Literal["READ", "WRITE"] = "READ"


# 3. Execute Port
class ExecuteParams(BaseModel):
    """Parameters passed to execute."""
    execution_id: str
    query: str
    timeout_seconds: float = 15.0
    # True for READ queries: plugins should open a read-only transaction/connection
    # so the target itself rejects writes even if the core classifier is fooled.
    read_only: bool = False


class ExecuteResult(BaseModel):
    """Payload returned by execute."""
    data: Optional[Any] = None
    rows_affected: int = 0
    execution_time_ms: float = 0.0
    spid: Optional[int] = None
    # True when the plugin stopped reading rows at its configured row cap
    truncated: bool = False


# 4. Abort Port
class AbortParams(BaseModel):
    """Parameters passed to abort."""
    execution_id: str


class AbortResult(BaseModel):
    """Payload returned by abort."""
    success: bool
    message: str


# 5. Lifecycle Re-Init Port
class ReinitParams(BaseModel):
    """Parameters passed to reinitialize plugin connection with updated configuration."""
    config: dict[str, Any] = Field(default_factory=dict)


class ReinitResult(BaseModel):
    """Payload returned by reinit."""
    success: bool = True
    message: str = "Connection reinitialized successfully."
    status: str = "active"


# --- Abstract Base Interface for Plugin Adapters ---

class IPluginAdapter(ABC):
    """Abstract interface defining standard ports every plugin implements."""

    @abstractmethod
    def sync_knowledge(self, params: SyncKnowledgeParams) -> SyncKnowledgeResult:
        """Port 1: Extract structural metadata, chunk it, and return catalog."""
        pass

    @abstractmethod
    def dry_run(self, params: DryRunParams) -> DryRunResult:
        """Port 2: Inspect plan on target, enforce rules, return explain plan and violations."""
        pass

    @abstractmethod
    def execute(self, params: ExecuteParams) -> ExecuteResult:
        """Port 3: Execute query under strict timeout guard, track SPID and return results."""
        pass

    @abstractmethod
    def abort(self, params: AbortParams) -> AbortResult:
        """Port 4: Immediately kill session/SPID on target system."""
        pass

    def reinit(self, params: ReinitParams) -> ReinitResult:
        """Port 5 (Lifecycle): Reinitialize connection with updated configuration parameters."""
        return ReinitResult(
            success=True,
            message="Connection parameters updated successfully.",
            status="active",
        )
