import { ExecutionResponse } from "@/types";
import { apiClient } from "./client";

export interface FetchExecutionsParams {
  targetId?: string;
  limit?: number;
  offset?: number;
}

export interface PaginatedExecutionsResponse {
  items: ExecutionResponse[];
  next_cursor: string | null;
  total_count: number;
}

export interface FetchPaginatedParams {
  cursor?: string;
  limit?: number;
  status?: string;
  targetId?: string;
  q?: string;
  fromDate?: string;
  toDate?: string;
}

export async function fetchPaginatedExecutions(
  params?: FetchPaginatedParams
): Promise<PaginatedExecutionsResponse> {
  const queryParams: Record<string, string | number | undefined> = {
    cursor: params?.cursor,
    limit: params?.limit,
    status: params?.status,
    target_id: params?.targetId,
    q: params?.q,
    from_date: params?.fromDate,
    to_date: params?.toDate,
  };
  return apiClient<PaginatedExecutionsResponse>("/executions/page", {
    params: queryParams,
  });
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
