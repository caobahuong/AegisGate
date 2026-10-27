/**
 * Core API Client & Fetch Wrapper with Timeout, Typed ApiError, and Sane Env Resolution.
 */

export class ApiError extends Error {
  public status: number;
  public data?: unknown;

  constructor(status: number, message: string, data?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.data = data;
    Object.setPrototypeOf(this, ApiError.prototype);
  }
}

/**
 * Resolves the backend base URL at runtime.
 * Sane default: http://127.0.0.1:8000
 */
export function getApiBaseUrl(): string {
  const envUrl = process.env.NEXT_PUBLIC_API_URL;
  if (!envUrl) {
    return "http://127.0.0.1:8000/api";
  }
  return envUrl.endsWith("/api") ? envUrl : `${envUrl.replace(/\/+$/, "")}/api`;
}

/**
 * Resolves backend origin (for guide display and websocket/SSE fallback).
 */
export function getBackendOrigin(): string {
  const base = getApiBaseUrl();
  return base.replace(/\/api\/?$/, "");
}

interface RequestOptions extends RequestInit {
  timeoutMs?: number;
  params?: Record<string, string | number | boolean | undefined | null>;
}

export async function apiClient<T>(endpoint: string, options: RequestOptions = {}): Promise<T> {
  const { timeoutMs = 15000, params, headers, ...customConfig } = options;
  const baseUrl = getApiBaseUrl();

  let url =
    endpoint.startsWith("http://") || endpoint.startsWith("https://")
      ? endpoint
      : `${baseUrl}${endpoint.startsWith("/") ? "" : "/"}${endpoint}`;

  if (params) {
    const searchParams = new URLSearchParams();
    Object.entries(params).forEach(([key, val]) => {
      if (val !== undefined && val !== null) {
        searchParams.append(key, String(val));
      }
    });
    const qs = searchParams.toString();
    if (qs) {
      url += (url.includes("?") ? "&" : "?") + qs;
    }
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const config: RequestInit = {
      ...customConfig,
      headers: {
        ...(customConfig.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
        ...headers,
      },
      signal: controller.signal,
      cache: customConfig.cache || "no-store",
    };

    const res = await fetch(url, config);
    clearTimeout(timeoutId);

    if (!res.ok) {
      let errDetail = `HTTP ${res.status}: ${res.statusText}`;
      let errData: unknown = null;
      try {
        errData = await res.json();
        if (typeof errData === "object" && errData !== null && "detail" in errData) {
          errDetail = String((errData as { detail: unknown }).detail);
        }
      } catch {
        // Fallback to status text
      }
      throw new ApiError(res.status, errDetail, errData);
    }

    if (res.status === 204) {
      return {} as T;
    }

    return await res.json();
  } catch (err: unknown) {
    clearTimeout(timeoutId);
    if (err instanceof ApiError) {
      throw err;
    }
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new ApiError(408, `Request timed out after ${timeoutMs}ms`);
    }
    throw new ApiError(0, err instanceof Error ? err.message : "Network error");
  }
}
