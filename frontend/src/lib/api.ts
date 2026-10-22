/**
 * Typed API Client for AegisGate Core Gateway.
 * 
 * Strict Zero `any` Policy.
 */

import {
  CreateRuleRequest,
  ExecutionResponse,
  KnowledgeChunkResponse,
  McpConfigResponse,
  PluginProfileResponse,
  PluginSchemaResponse,
  RegisterPluginRequest,
  RuleResponse,
  UpdatePluginConfigRequest,
  UpdateRuleRequest,
} from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000/api";

export async function fetchExecutions(targetId?: string): Promise<ExecutionResponse[]> {
  const url = targetId
    ? `${API_BASE}/monitor/executions?target_id=${encodeURIComponent(targetId)}`
    : `${API_BASE}/monitor/executions`;
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch executions");
  return res.json();
}

export async function submitExecution(payload: {
  target_id: string;
  query: string;
  reasoning: string;
}): Promise<ExecutionResponse> {
  const res = await fetch(`${API_BASE}/monitor/executions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Submission failed" }));
    throw new Error(err.detail || "Submission failed");
  }
  return res.json();
}

export async function approveExecution(executionId: string, approvedBy = "Admin"): Promise<ExecutionResponse> {
  const res = await fetch(`${API_BASE}/monitor/executions/${executionId}/approve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ approved_by: approvedBy }),
  });
  if (!res.ok) throw new Error("Approval failed");
  return res.json();
}

export async function rejectExecution(executionId: string, reason = "Admin Rejected"): Promise<ExecutionResponse> {
  const res = await fetch(`${API_BASE}/monitor/executions/${executionId}/reject`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ rejected_by: "Admin", reason }),
  });
  if (!res.ok) throw new Error("Rejection failed");
  return res.json();
}

export async function abortExecution(executionId: string): Promise<ExecutionResponse> {
  const res = await fetch(`${API_BASE}/monitor/executions/${executionId}/abort`, {
    method: "POST",
  });
  if (!res.ok) throw new Error("Abort failed");
  return res.json();
}

export async function fetchPlugins(): Promise<PluginProfileResponse[]> {
  const res = await fetch(`${API_BASE}/plugins`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch plugins");
  return res.json();
}

export async function registerPlugin(data: RegisterPluginRequest): Promise<PluginProfileResponse> {
  const res = await fetch(`${API_BASE}/plugins`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to register plugin");
  return res.json();
}

export async function fetchPluginSchema(pluginId: string): Promise<PluginSchemaResponse> {
  const res = await fetch(`${API_BASE}/plugins/${encodeURIComponent(pluginId)}/schema`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error("Failed to fetch plugin schema");
  return res.json();
}

export async function updatePluginConfig(
  pluginId: string,
  payload: UpdatePluginConfigRequest
): Promise<PluginProfileResponse> {
  const res = await fetch(`${API_BASE}/plugins/${encodeURIComponent(pluginId)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Failed to update plugin config" }));
    throw new Error(err.detail || "Failed to update plugin config");
  }
  return res.json();
}

export async function deletePlugin(
  pluginId: string,
  hardDelete: boolean = false
): Promise<{ success: boolean; plugin_id: string; mode: string; message: string }> {
  const res = await fetch(
    `${API_BASE}/plugins/${encodeURIComponent(pluginId)}?hard_delete=${hardDelete}`,
    {
      method: "DELETE",
    }
  );
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Failed to uninstall plugin" }));
    throw new Error(err.detail || "Failed to uninstall plugin");
  }
  return res.json();
}

export async function fetchGlobalMcpConfig(): Promise<McpConfigResponse> {
  const res = await fetch(`${API_BASE}/mcp/config`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch global MCP config");
  return res.json();
}

export async function fetchPluginMcpConfig(pluginId: string): Promise<McpConfigResponse> {
  const res = await fetch(
    `${API_BASE}/plugins/${encodeURIComponent(pluginId)}/mcp-config`,
    { cache: "no-store" }
  );
  if (!res.ok) throw new Error("Failed to fetch plugin MCP config");
  return res.json();
}

export async function syncPluginCatalog(pluginId: string): Promise<Record<string, unknown>[]> {
  const res = await fetch(`${API_BASE}/plugins/${encodeURIComponent(pluginId)}/sync`, {
    method: "POST",
  });
  if (!res.ok) throw new Error("Catalog sync failed");
  return res.json();
}

export async function fetchKnowledgeChunks(targetId?: string): Promise<KnowledgeChunkResponse[]> {
  const url = targetId
    ? `${API_BASE}/knowledge?target_id=${encodeURIComponent(targetId)}`
    : `${API_BASE}/knowledge`;
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch knowledge chunks");
  return res.json();
}

export async function fetchKnowledgeChunkDetail(chunkId: string): Promise<KnowledgeChunkResponse> {
  const res = await fetch(`${API_BASE}/knowledge/${encodeURIComponent(chunkId)}`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch chunk detail");
  return res.json();
}

export async function updateKnowledgeDocs(
  chunkId: string,
  docContent?: string,
  skillsContent?: string
): Promise<{ success: boolean }> {
  const res = await fetch(`${API_BASE}/knowledge/${encodeURIComponent(chunkId)}/docs`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ doc_content: docContent, skills_content: skillsContent }),
  });
  if (!res.ok) throw new Error("Failed to update docs");
  return res.json();
}

export async function fetchRules(targetId?: string, exact?: boolean): Promise<RuleResponse[]> {
  const params = new URLSearchParams();
  if (targetId) params.append("target_id", targetId);
  if (exact) params.append("exact", "true");
  const queryStr = params.toString() ? `?${params.toString()}` : "";
  const res = await fetch(`${API_BASE}/rules${queryStr}`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch rules");
  return res.json();
}

export async function fetchSkills(targetId?: string): Promise<Record<string, unknown>[]> {
  const url = targetId
    ? `${API_BASE}/skills?target_id=${encodeURIComponent(targetId)}`
    : `${API_BASE}/skills`;
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch skills");
  return res.json();
}

export async function createRule(rule: CreateRuleRequest): Promise<RuleResponse> {
  const res = await fetch(`${API_BASE}/rules`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(rule),
  });
  if (!res.ok) throw new Error("Failed to create rule");
  return res.json();
}

export async function updateRule(
  ruleId: string,
  payload: UpdateRuleRequest
): Promise<RuleResponse> {
  const res = await fetch(`${API_BASE}/rules/${encodeURIComponent(ruleId)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Failed to update rule" }));
    throw new Error(err.detail || "Failed to update rule");
  }
  return res.json();
}

export async function deleteRule(ruleId: string): Promise<{ success: boolean }> {
  const res = await fetch(`${API_BASE}/rules/${encodeURIComponent(ruleId)}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Failed to delete rule");
  return res.json();
}

export async function fetchAutoMode(): Promise<boolean> {
  const res = await fetch(`${API_BASE}/settings/auto-mode`, { cache: "no-store" });
  if (!res.ok) return false;
  const data = await res.json();
  return Boolean(data.auto_approval_enabled);
}

export async function setAutoMode(enabled: boolean): Promise<boolean> {
  const res = await fetch(`${API_BASE}/settings/auto-mode`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ enabled }),
  });
  if (!res.ok) throw new Error("Failed to set auto mode");
  const data = await res.json();
  return Boolean(data.auto_approval_enabled);
}
