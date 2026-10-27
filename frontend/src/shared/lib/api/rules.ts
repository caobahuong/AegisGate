import { CreateRuleRequest, RuleResponse, UpdateRuleRequest } from "@/types";
import { apiClient } from "./client";

export async function fetchRules(targetId?: string, exact?: boolean): Promise<RuleResponse[]> {
  const params: Record<string, string | boolean | undefined> = {};
  if (targetId) params.target_id = targetId;
  if (exact) params.exact = "true";

  return apiClient<RuleResponse[]>("/rules", { params });
}

export async function fetchSkills(targetId?: string): Promise<Record<string, unknown>[]> {
  return apiClient<Record<string, unknown>[]>("/skills", {
    params: targetId ? { target_id: targetId } : undefined,
  });
}

export async function createRule(rule: CreateRuleRequest): Promise<RuleResponse> {
  return apiClient<RuleResponse>("/rules", {
    method: "POST",
    body: JSON.stringify(rule),
  });
}

export async function updateRule(
  ruleId: string,
  payload: UpdateRuleRequest
): Promise<RuleResponse> {
  return apiClient<RuleResponse>(`/rules/${encodeURIComponent(ruleId)}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export async function deleteRule(ruleId: string): Promise<{ success: boolean }> {
  return apiClient<{ success: boolean }>(`/rules/${encodeURIComponent(ruleId)}`, {
    method: "DELETE",
  });
}
