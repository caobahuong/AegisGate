import { ExecutionResponse } from "@/types";
import { apiClient } from "./client";

export interface FetchExecutionsParams {
  targetId?: string;
  limit?: number;
  offset?: number;
}

export async function fetchExecutions(
  targetIdOrParams?: string | FetchExecutionsParams
): Promise<ExecutionResponse[]> {
  let params: Record<string, string | number | undefined> = {};

  if (typeof targetIdOrParams === "string") {
    params = { target_id: targetIdOrParams };
  } else if (targetIdOrParams && typeof targetIdOrParams === "object") {
    params = {
      target_id: targetIdOrParams.targetId,
      limit: targetIdOrParams.limit,
      offset: targetIdOrParams.offset,
    };
  }

  return apiClient<ExecutionResponse[]>("/monitor/executions", { params });
}

export async function submitExecution(payload: {
  target_id: string;
  query: string;
  reasoning: string;
}): Promise<ExecutionResponse> {
  return apiClient<ExecutionResponse>("/monitor/executions", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function approveExecution(
  executionId: string,
  approvedBy = "Admin"
): Promise<ExecutionResponse> {
  return apiClient<ExecutionResponse>(
    `/monitor/executions/${encodeURIComponent(executionId)}/approve`,
    {
      method: "POST",
      body: JSON.stringify({ approved_by: approvedBy }),
    }
  );
}

export async function rejectExecution(
  executionId: string,
  reason = "Admin Rejected"
): Promise<ExecutionResponse> {
  return apiClient<ExecutionResponse>(
    `/monitor/executions/${encodeURIComponent(executionId)}/reject`,
    {
      method: "POST",
      body: JSON.stringify({ rejected_by: "Admin", reason }),
    }
  );
}

export async function abortExecution(executionId: string): Promise<ExecutionResponse> {
  return apiClient<ExecutionResponse>(
    `/monitor/executions/${encodeURIComponent(executionId)}/abort`,
    {
      method: "POST",
    }
  );
}
