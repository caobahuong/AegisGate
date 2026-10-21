/**
 * AegisGate Shared Contract Types
 * 
 * Synchronized with Core Python Pydantic Models.
 * Strict Zero `any` Policy enforced per typescript_clean_code.md.
 */

export type ExecutionStatus =
  | "DRY_RUN"
  | "PAUSED_FOR_REVIEW"
  | "EXECUTING"
  | "COMPLETED"
  | "REJECTED"
  | "TIMEOUT"
  | "ABORTED";

export type QueryType = "READ" | "WRITE";

export type RuleType = "FORBID_JOIN" | "FORBID_TABLE_SCAN" | "MAX_EXECUTION_TIME" | "CUSTOM";

export type RuleSeverity = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";

export interface ExecutionResponse {
  id: string;
  target_id: string;
  query: string;
  query_type: QueryType;
  reasoning: string;
  status: ExecutionStatus;
  explain_plan: Record<string, unknown> | string | null;
  violations: string[];
  execution_time_ms: number | null;
  auto_approved: boolean;
  approved_by: string | null;
  result_summary: Record<string, unknown> | string | null;
  error_message: string | null;
  spid: number | null;
  created_at: string;
  finished_at: string | null;
}

export interface PluginProfileResponse {
  id: string;
  name: string;
  driver: string;
  entrypoint: string;
  dry_run_command: string;
  abort_command: string;
  config: Record<string, unknown>;
  status: "active" | "inactive" | "error";
  latency_ms: number;
  active_sessions_count: number;
  created_at: string;
  updated_at: string;
}

export interface ColumnSchema {
  name: string;
  data_type: string;
  is_nullable: boolean;
  is_primary_key: boolean;
  description?: string;
}

export interface IndexSchema {
  name: string;
  columns: string[];
  is_unique: boolean;
}

export interface TableSchema {
  name: string;
  schema_name: string;
  columns: ColumnSchema[];
  indexes: IndexSchema[];
  row_count_estimate?: number;
  description?: string;
}

export interface KnowledgeChunkResponse {
  id: string;
  target_id: string;
  partition_key: string;
  title: string;
  catalog: TableSchema[] | Record<string, unknown> | unknown;
  doc_content?: string;
  skills_content?: string;
  created_at: string;
  updated_at: string;
}

export interface RuleResponse {
  id: string;
  name: string;
  target_id: string | null;
  rule_type: RuleType;
  expression: string;
  description: string;
  severity: RuleSeverity;
  is_active: boolean;
  created_at: string;
}

export interface CreateRuleRequest {
  id: string;
  name: string;
  target_id?: string | null;
  rule_type: RuleType;
  expression: string;
  description: string;
  severity: RuleSeverity;
  is_active: boolean;
}

export interface RegisterPluginRequest {
  id: string;
  name: string;
  driver: string;
  entrypoint: string;
  dry_run_command: string;
  abort_command: string;
  config: Record<string, unknown>;
}

export interface SSEMessagePayload {
  event: string;
  data: Record<string, unknown>;
}

export type ActiveTab = "monitor" | "plugins" | "knowledge" | "rules" | "logs";
