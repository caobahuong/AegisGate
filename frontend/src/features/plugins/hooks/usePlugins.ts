"use client";

import { useState, useCallback, useEffect } from "react";
import {
  PluginProfileResponse,
  RegisterPluginRequest,
  InstallGitPluginRequest,
  UpdatePluginConfigRequest,
  PluginCertificationResponse,
  PluginCertificationReport,
} from "@/types";
import {
  fetchPlugins as apiFetchPlugins,
  registerPlugin as apiRegisterPlugin,
  installPluginZip as apiInstallPluginZip,
  installPluginGit as apiInstallPluginGit,
  updatePluginConfig as apiUpdatePluginConfig,
  syncPluginCatalog as apiSyncPluginCatalog,
  verifyPlugin as apiVerifyPlugin,
  deletePlugin as apiDeletePlugin,
} from "@/shared/lib/api";
import { useToast } from "@/shared/hooks/useToast";

export function usePlugins(initialPlugins: PluginProfileResponse[] = []) {
  const [plugins, setPlugins] = useState<PluginProfileResponse[]>(initialPlugins);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const { showToast } = useToast();

  const loadPlugins = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await apiFetchPlugins();
      setPlugins(data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load plugins";
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (initialPlugins.length === 0) {
      loadPlugins();
    }
  }, [initialPlugins.length, loadPlugins]);

  const register = useCallback(async (req: RegisterPluginRequest) => {
    const created = await apiRegisterPlugin(req);
    setPlugins((prev) => [...prev.filter((p) => p.id !== created.id), created]);
  }, []);

  const installZip = useCallback(async (file: File) => {
    const installed = await apiInstallPluginZip(file);
    setPlugins((prev) => [...prev.filter((p) => p.id !== installed.id), installed]);
  }, []);

  const installGit = useCallback(async (req: InstallGitPluginRequest) => {
    const installed = await apiInstallPluginGit(req);
    setPlugins((prev) => [...prev.filter((p) => p.id !== installed.id), installed]);
  }, []);

  const updateConfig = useCallback(async (pluginId: string, req: UpdatePluginConfigRequest) => {
    const updated = await apiUpdatePluginConfig(pluginId, req);
    setPlugins((prev) => prev.map((p) => (p.id === updated.id ? updated : p)));
  }, []);

  const syncCatalog = useCallback(
    async (pluginId: string) => {
      try {
        await apiSyncPluginCatalog(pluginId);
        showToast("Schema catalog refreshed and synced into Knowledge Store!", "success");
      } catch (err: unknown) {
        showToast(err instanceof Error ? err.message : "Catalog sync failed", "error");
        throw err;
      }
    },
    [showToast]
  );

  const verify = useCallback(
    async (pluginId: string): Promise<PluginCertificationResponse> => {
      const report = await apiVerifyPlugin(pluginId);
      setPlugins((prev) =>
        prev.map((p) =>
          p.id === pluginId
            ? {
                ...p,
                is_certified: report.certified,
                certification_report: report as unknown as PluginCertificationReport,
              }
            : p
        )
      );
      if (report.certified) {
        showToast(`Plugin #${pluginId} passed 4-stage sanity linter!`, "success");
      } else {
        showToast(`Plugin #${pluginId} has warnings or failed checks`, "warning");
      }
      return report;
    },
    [showToast]
  );

  const uninstall = useCallback(async (pluginId: string, hardDelete: boolean) => {
    await apiDeletePlugin(pluginId, hardDelete);
    setPlugins((prev) => prev.filter((p) => p.id !== pluginId));
  }, []);

  return {
    plugins,
    setPlugins,
    isLoading,
    error,
    refresh: loadPlugins,
    register,
    installZip,
    installGit,
    updateConfig,
    syncCatalog,
    verify,
    uninstall,
  };
}
