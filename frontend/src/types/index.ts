/**
 * AegisGate Shared Contract Types
 *
 * Synchronized with Core Python Pydantic Models.
 * Strict Zero `any` Policy enforced per typescript_clean_code.md.
 */

import type { components, paths } from "./api.generated";

export type ApiPaths = paths;
export type ApiSchemas = components["schemas"];

export type GeneratedExecutionResponse = components["schemas"]["ExecutionResponse"];
export type GeneratedPluginProfileResponse = components["schemas"]["PluginProfileResponse"];
export type GeneratedRuleResponse = components["schemas"]["RuleResponse"];
export type GeneratedKnowledgeChunkResponse = components["schemas"]["KnowledgeChunkResponse"];
export type GeneratedCreateRuleRequest = components["schemas"]["CreateRuleRequest"];
export type GeneratedSubmitExecutionRequest = components["schemas"]["SubmitExecutionRequest"];
export type GeneratedAutoModeResponse = components["schemas"]["AutoModeResponse"];
export type GeneratedPluginCertificationResponse =
  components["schemas"]["PluginCertificationResponse"];
export type GeneratedPluginSchemaResponse = components["schemas"]["PluginSchemaResponse"];
export type GeneratedMcpConfigResponse = components["schemas"]["McpConfigResponse"];

export type ExecutionStatus =
  "DRY_RUN" | "PAUSED_FOR_REVIEW" | "EXECUTING" | "COMPLETED" | "REJECTED" | "TIMEOUT" | "ABORTED";

export type QueryType = "READ" | "WRITE";

export type RuleType =
  | "FORBID_JOIN"
  | "FORBID_TABLE_SCAN"
  | "MAX_EXECUTION_TIME"
  | "CUSTOM"
  | "REDACT_FIELD"
  | "REMOVE_FIELD";

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

export type UiFieldType = "text" | "password" | "number" | "select" | "boolean" | "textarea";

export interface UiFieldSchema {
  key: string;
  label: string;
  type: UiFieldType;
  default?: unknown;
  required?: boolean;
  options?: string[];
  placeholder?: string;
  description?: string;
}

export interface CustomCardData {
  type?: string;
  title: string;
  badge?: string;
  badges?: Array<{ label: string; value: string }>;
  columns?: string[];
  sample_data?: Record<string, unknown>[];
}

export interface PluginProfileResponse {
  id: string;
  name: string;
  driver: string;
  entrypoint: string;
  dry_run_command: string;
  abort_command: string;
  config: Record<string, unknown>;
  ui_schema?: UiFieldSchema[];
  custom_card?: CustomCardData | null;
  status: "active" | "inactive" | "error";
  latency_ms: number;
  active_sessions_count: number;
  is_certified?: boolean;
  certification_report?: PluginCertificationReport | null;
  created_at: string;
  updated_at: string;
}

export interface PluginSchemaResponse {
  plugin_id: string;
  name: string;
  driver: string;
  ui_schema: UiFieldSchema[];
  current_config: Record<string, unknown>;
  custom_card?: CustomCardData | null;
}

export interface UpdatePluginConfigRequest {
  name?: string;
  config: Record<string, unknown>;
  driver?: string;
  entrypoint?: string;
  dry_run_command?: string;
  abort_command?: string;
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

export interface UpdateRuleRequest {
  name?: string;
  target_id?: string | null;
  rule_type?: RuleType;
  expression?: string;
  description?: string;
  severity?: RuleSeverity;
  is_active?: boolean;
}

export interface SanityCheckItem {
  status: "PASSED" | "FAILED";
  latency_ms?: number;
  details?: string;
  error?: string;
}

export interface PluginCertificationReport {
  plugin_id: string;
  certified: boolean;
  badge: "CERTIFIED_READY" | "COMPATIBILITY_WARNING";
  checks: Record<string, SanityCheckItem>;
  verified_at: string;
  error?: string | null;
}

export interface InstallGitPluginRequest {
  git_url: string;
  branch?: string;
  plugin_id?: string;
}

export interface PluginCertificationResponse {
  plugin_id: string;
  certified: boolean;
  badge: string;
  checks: Record<string, SanityCheckItem>;
  verified_at: string;
  error?: string | null;
}

export interface RegisterPluginRequest {
  id: string;
  name: string;
  driver: string;
  entrypoint: string;
  dry_run_command: string;
  abort_command: string;
  config: Record<string, unknown>;
  ui_schema?: UiFieldSchema[];
  custom_card?: CustomCardData | null;
}

export interface SSEMessagePayload {
  event: string;
  data: Record<string, unknown>;
}

export interface McpServerItem {
  command: string;
  args: string[];
  env: Record<string, string>;
}

export interface McpConfigResponse {
  server_name: string;
  plugin_id?: string | null;
  command: string;
  args: string[];
  env: Record<string, string>;
  mcpServers: Record<string, McpServerItem>;
  client_configs?: Record<string, { mcpServers: Record<string, McpServerItem> }>;
}

export type ActiveTab = "monitor" | "plugins" | "knowledge" | "rules" | "logs";
