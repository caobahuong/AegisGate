import { apiClient } from "./client";

export async function fetchAutoMode(): Promise<boolean> {
  try {
    const data = await apiClient<{ auto_approval_enabled: boolean }>("/settings/auto-mode");
    return Boolean(data.auto_approval_enabled);
  } catch {
    return false;
  }
}

export async function setAutoMode(enabled: boolean): Promise<boolean> {
  const data = await apiClient<{ auto_approval_enabled: boolean }>("/settings/auto-mode", {
    method: "POST",
    body: JSON.stringify({ enabled }),
  });
  return Boolean(data.auto_approval_enabled);
}
