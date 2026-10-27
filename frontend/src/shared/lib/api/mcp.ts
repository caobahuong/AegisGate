import { McpConfigResponse } from "@/types";
import { apiClient } from "./client";

export async function fetchGlobalMcpConfig(): Promise<McpConfigResponse> {
  return apiClient<McpConfigResponse>("/mcp/config");
}

export async function fetchPluginMcpConfig(pluginId: string): Promise<McpConfigResponse> {
  return apiClient<McpConfigResponse>(`/plugins/${encodeURIComponent(pluginId)}/mcp-config`);
}
