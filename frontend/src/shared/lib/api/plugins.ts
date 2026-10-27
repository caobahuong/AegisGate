import {
  PluginProfileResponse,
  RegisterPluginRequest,
  InstallGitPluginRequest,
  PluginCertificationResponse,
  PluginSchemaResponse,
  UpdatePluginConfigRequest,
} from "@/types";
import { apiClient } from "./client";

export async function fetchPlugins(includeDisabled = false): Promise<PluginProfileResponse[]> {
  return apiClient<PluginProfileResponse[]>("/plugins", {
    params: includeDisabled ? { include_disabled: true } : undefined,
  });
}

export async function registerPlugin(data: RegisterPluginRequest): Promise<PluginProfileResponse> {
  return apiClient<PluginProfileResponse>("/plugins", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function installPluginZip(file: File): Promise<PluginProfileResponse> {
  const formData = new FormData();
  formData.append("file", file);
  return apiClient<PluginProfileResponse>("/plugins/install-zip", {
    method: "POST",
    body: formData,
  });
}

export async function installPluginGit(
  payload: InstallGitPluginRequest
): Promise<PluginProfileResponse> {
  return apiClient<PluginProfileResponse>("/plugins/install-git", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function verifyPlugin(pluginId: string): Promise<PluginCertificationResponse> {
  return apiClient<PluginCertificationResponse>(`/plugins/${encodeURIComponent(pluginId)}/verify`, {
    method: "POST",
  });
}

export async function fetchPluginSchema(pluginId: string): Promise<PluginSchemaResponse> {
  return apiClient<PluginSchemaResponse>(`/plugins/${encodeURIComponent(pluginId)}/schema`);
}

export async function updatePluginConfig(
  pluginId: string,
  payload: UpdatePluginConfigRequest
): Promise<PluginProfileResponse> {
  return apiClient<PluginProfileResponse>(`/plugins/${encodeURIComponent(pluginId)}`, {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}

export async function deletePlugin(
  pluginId: string,
  hardDelete: boolean = false
): Promise<{
  success: boolean;
  plugin_id: string;
  mode: string;
  message: string;
}> {
  return apiClient(`/plugins/${encodeURIComponent(pluginId)}`, {
    method: "DELETE",
    params: { hard_delete: hardDelete },
  });
}

export async function syncPluginCatalog(pluginId: string): Promise<Record<string, unknown>[]> {
  return apiClient<Record<string, unknown>[]>(`/plugins/${encodeURIComponent(pluginId)}/sync`, {
    method: "POST",
  });
}
