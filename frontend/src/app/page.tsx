"use client";

import React, { useEffect, useState } from "react";
import { Header } from "@/components/Header";
import { Sidebar } from "@/components/Sidebar";
import { LiveExecutionMonitor } from "@/components/LiveExecutionMonitor";
import { PluginManagement } from "@/components/PluginManagement";
import { KnowledgeAndRules } from "@/components/KnowledgeAndRules";
import { AuditLogs } from "@/components/AuditLogs";
import { McpConfigModal } from "@/components/McpConfigModal";
import { UserGuideModal } from "@/components/UserGuideModal";
import {
  ActiveTab,
  CreateRuleRequest,
  ExecutionResponse,
  KnowledgeChunkResponse,
  McpConfigResponse,
  PluginProfileResponse,
  RegisterPluginRequest,
  InstallGitPluginRequest,
  PluginCertificationReport,
  PluginCertificationResponse,
  RuleResponse,
  UpdatePluginConfigRequest,
  UpdateRuleRequest,
} from "@/types";
import {
  abortExecution,
  approveExecution,
  createRule,
  deletePlugin,
  deleteRule,
  fetchAutoMode,
  fetchExecutions,
  fetchGlobalMcpConfig,
  fetchKnowledgeChunks,
  fetchPluginMcpConfig,
  fetchPlugins,
  fetchRules,
  registerPlugin,
  installPluginZip,
  installPluginGit,
  verifyPlugin,
  rejectExecution,
  setAutoMode,
  submitExecution,
  syncPluginCatalog,
  updateKnowledgeDocs,
  updatePluginConfig,
  updateRule,
} from "@/lib/api";

const SSE_URL = process.env.NEXT_PUBLIC_SSE_URL || "http://127.0.0.1:8000/api/monitor/events";

export default function DashboardPage() {
  const [activeTab, setActiveTab] = useState<ActiveTab>("monitor");
  const [autoMode, setAutoModeState] = useState<boolean>(false);
  const [mcpOnline, setMcpOnline] = useState<boolean>(true);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  // Core Data Collections
  const [executions, setExecutions] = useState<ExecutionResponse[]>([]);
  const [selectedExecution, setSelectedExecution] = useState<ExecutionResponse | null>(null);
  const [plugins, setPlugins] = useState<PluginProfileResponse[]>([]);
  const [chunks, setChunks] = useState<KnowledgeChunkResponse[]>([]);
  const [rules, setRules] = useState<RuleResponse[]>([]);

  // MCP Connection Modal State
  const [showMcpModal, setShowMcpModal] = useState<boolean>(false);
  const [showUserGuideModal, setShowUserGuideModal] = useState<boolean>(false);
  const [mcpModalData, setMcpModalData] = useState<McpConfigResponse | null>(null);
  const [mcpModalTitle, setMcpModalTitle] = useState<string>("MCP Connection Configuration");
  const [mcpModalSubtitle, setMcpModalSubtitle] = useState<string>(
    "Global AegisGate MCP Server configuration for Claude, Cursor, and Cline"
  );
  const [isMcpLoading, setIsMcpLoading] = useState<boolean>(false);

  // Theme State: Light Mode is DEFAULT
  const [theme, setTheme] = useState<"light" | "dark">("light");

  useEffect(() => {
    try {
      const savedTheme = localStorage.getItem("aegisgate-theme") as "light" | "dark" | null;
      if (savedTheme === "dark") {
        setTheme("dark");
        document.documentElement.classList.add("dark");
      } else {
        setTheme("light");
        document.documentElement.classList.remove("dark");
      }
    } catch {
      setTheme("light");
      document.documentElement.classList.remove("dark");
    }
  }, []);

  const handleToggleTheme = () => {
    const nextTheme = theme === "light" ? "dark" : "light";
    setTheme(nextTheme);
    if (nextTheme === "dark") {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
    try {
      localStorage.setItem("aegisgate-theme", nextTheme);
    } catch {}
  };

  // 1. Initial Data Load
  useEffect(() => {
    let isMounted = true;

    async function loadInitialData() {
      try {
        const [loadedAutoMode, loadedExecutions, loadedPlugins, loadedChunks, loadedRules] =
          await Promise.all([
            fetchAutoMode(),
            fetchExecutions(),
            fetchPlugins(),
            fetchKnowledgeChunks(),
            fetchRules(),
          ]);

        if (isMounted) {
          setAutoModeState(loadedAutoMode);
          setExecutions(loadedExecutions);
          if (loadedExecutions.length > 0) {
            setSelectedExecution(loadedExecutions[0]);
          }
          setPlugins(loadedPlugins);
          setChunks(loadedChunks);
          setRules(loadedRules);
        }
      } catch (err) {
        console.error("Failed to load initial AegisGate data:", err);
      }
    }

    loadInitialData();

    return () => {
      isMounted = false;
    };
  }, []);

  // 2. Real-Time SSE Listener (Server-Sent Events)
  useEffect(() => {
    let eventSource: EventSource | null = null;
    let reconnectTimer: NodeJS.Timeout | null = null;

    // Re-sync the execution list from the API. Used for every backend lifecycle event
    // (execution_created / paused / completed / ...), on (re)connect, and as a safety-net poll.
    const refreshExecutions = async () => {
      try {
        const list = await fetchExecutions();
        setExecutions(list);
        setSelectedExecution((current) =>
          current ? (list.find((e) => e.id === current.id) ?? current) : (list[0] ?? null)
        );
      } catch (err) {
        console.error("Failed to refresh executions:", err);
      }
    };

    const setupSSE = () => {
      try {
        eventSource = new EventSource(SSE_URL);

        eventSource.onopen = () => {
          setMcpOnline(true);
          void refreshExecutions(); // catch up on anything missed while disconnected
        };

        eventSource.onmessage = (event) => {
          try {
            const rawData = JSON.parse(event.data);
            if (rawData.event === "execution_update" && rawData.data) {
              const updatedExec: ExecutionResponse = rawData.data;

              // Immutable list update
              setExecutions((prev) => {
                const exists = prev.some((e) => e.id === updatedExec.id);
                if (exists) {
                  return prev.map((e) => (e.id === updatedExec.id ? updatedExec : e));
                }
                return [updatedExec, ...prev];
              });

              // Keep selected execution synced
              setSelectedExecution((current) => {
                if (!current || current.id === updatedExec.id) {
                  return updatedExec;
                }
                return current;
              });
            } else if (rawData.event === "auto_mode_changed") {
              setAutoModeState(Boolean(rawData.data?.enabled));
            } else if (
              typeof rawData.event === "string" &&
              rawData.event.startsWith("execution_")
            ) {
              void refreshExecutions();
            } else if (rawData.event === "plugin_installed") {
              fetchPlugins()
                .then(setPlugins)
                .catch((err) => console.error("Failed to refresh plugins:", err));
            }
          } catch (err) {
            console.error("SSE parse error:", err);
          }
        };

        eventSource.onerror = () => {
          setMcpOnline(false);
          eventSource?.close();
          // Attempt reconnection after 5 seconds
          reconnectTimer = setTimeout(setupSSE, 5000);
        };
      } catch (err) {
        console.error("SSE connection setup failed:", err);
      }
    };

    setupSSE();

    // Safety net: poll while the tab is visible in case an event is dropped (full queue, proxy, etc.)
    const pollTimer = setInterval(() => {
      if (document.visibilityState === "visible") {
        void refreshExecutions();
      }
    }, 10000);

    // Mandatory cleanup per typescript_clean_code.md to prevent memory leaks
    return () => {
      clearInterval(pollTimer);
      if (eventSource) {
        eventSource.close();
      }
      if (reconnectTimer) {
        clearTimeout(reconnectTimer);
      }
    };
  }, []);

  // Handlers
  const handleToggleAutoMode = async () => {
    try {
      const updated = await setAutoMode(!autoMode);
      setAutoModeState(updated);
    } catch (err) {
      console.error("Toggle auto mode error:", err);
    }
  };

  const handleSubmitQuery = async (targetId: string, queryText: string, reasoningText: string) => {
    setIsSubmitting(true);
    try {
      const newExec = await submitExecution({
        target_id: targetId,
        query: queryText,
        reasoning: reasoningText,
      });
      // Immutable state update
      setExecutions((prev) => [newExec, ...prev.filter((e) => e.id !== newExec.id)]);
      setSelectedExecution(newExec);
    } catch (err) {
      alert(`Submission failed: ${err instanceof Error ? err.message : "Unknown error"}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleApprove = async (id: string) => {
    try {
      const updated = await approveExecution(id, "Admin Dashboard");
      setExecutions((prev) => prev.map((e) => (e.id === updated.id ? updated : e)));
      setSelectedExecution(updated);
    } catch (err) {
      alert(`Approval error: ${err instanceof Error ? err.message : "Unknown error"}`);
    }
  };

  const handleReject = async (id: string) => {
    try {
      const updated = await rejectExecution(id, "Rejected by Admin Dashboard");
      setExecutions((prev) => prev.map((e) => (e.id === updated.id ? updated : e)));
      setSelectedExecution(updated);
    } catch (err) {
      alert(`Rejection error: ${err instanceof Error ? err.message : "Unknown error"}`);
    }
  };

  const handleAbort = async (id: string) => {
    try {
      const updated = await abortExecution(id);
      setExecutions((prev) => prev.map((e) => (e.id === updated.id ? updated : e)));
      setSelectedExecution(updated);
    } catch (err) {
      alert(`Abort error: ${err instanceof Error ? err.message : "Unknown error"}`);
    }
  };

  const handleInstallZip = async (file: File) => {
    const installed = await installPluginZip(file);
    setPlugins((prev) => [...prev.filter((p) => p.id !== installed.id), installed]);
  };

  const handleInstallGit = async (req: InstallGitPluginRequest) => {
    const installed = await installPluginGit(req);
    setPlugins((prev) => [...prev.filter((p) => p.id !== installed.id), installed]);
  };

  const handleVerifyPlugin = async (pluginId: string): Promise<PluginCertificationResponse> => {
    const report = await verifyPlugin(pluginId);
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
    return report;
  };

  const handleRegisterPlugin = async (req: RegisterPluginRequest) => {
    const newPlugin = await registerPlugin(req);
    setPlugins((prev) => [...prev.filter((p) => p.id !== newPlugin.id), newPlugin]);
  };

  const handleUpdatePlugin = async (pluginId: string, req: UpdatePluginConfigRequest) => {
    const updated = await updatePluginConfig(pluginId, req);
    setPlugins((prev) => prev.map((p) => (p.id === updated.id ? updated : p)));
  };

  const handleSyncPlugin = async (pluginId: string) => {
    await syncPluginCatalog(pluginId);
    // Refresh chunks
    const updatedChunks = await fetchKnowledgeChunks();
    setChunks(updatedChunks);
  };

  const handleSaveDocs = async (chunkId: string, docText: string, skillsText: string) => {
    await updateKnowledgeDocs(chunkId, docText, skillsText);
    const updatedChunks = await fetchKnowledgeChunks();
    setChunks(updatedChunks);
  };

  const handleCreateRule = async (ruleReq: CreateRuleRequest) => {
    const newRule = await createRule(ruleReq);
    setRules((prev) => [...prev.filter((r) => r.id !== newRule.id), newRule]);
  };

  const handleUpdateRule = async (ruleId: string, ruleReq: UpdateRuleRequest) => {
    const updated = await updateRule(ruleId, ruleReq);
    setRules((prev) => prev.map((r) => (r.id === updated.id ? updated : r)));
  };

  const handleDeleteRule = async (ruleId: string) => {
    await deleteRule(ruleId);
    setRules((prev) => prev.filter((r) => r.id !== ruleId));
  };

  const handleUninstallPlugin = async (pluginId: string, hardDelete: boolean = false) => {
    await deletePlugin(pluginId, hardDelete);
    setPlugins((prev) => prev.filter((p) => p.id !== pluginId));
  };

  const handleOpenGlobalMcp = async () => {
    setMcpModalTitle("AegisGate Global MCP Connection");
    setMcpModalSubtitle(
      "Connect Claude Desktop, Cursor, or Cline to AegisGate Core Gateway & Governance Proxy"
    );
    setShowMcpModal(true);
    setIsMcpLoading(true);
    try {
      const data = await fetchGlobalMcpConfig();
      setMcpModalData(data);
    } catch (err) {
      console.error("Failed to fetch global MCP config:", err);
    } finally {
      setIsMcpLoading(false);
    }
  };

  const handleOpenPluginMcp = async (plugin: PluginProfileResponse) => {
    setMcpModalTitle(`MCP Connection: ${plugin.name}`);
    setMcpModalSubtitle(`Target connector snippet for ${plugin.driver} (${plugin.id})`);
    setShowMcpModal(true);
    setIsMcpLoading(true);
    try {
      const data = await fetchPluginMcpConfig(plugin.id);
      setMcpModalData(data);
    } catch (err) {
      console.error(`Failed to fetch MCP config for ${plugin.id}:`, err);
    } finally {
      setIsMcpLoading(false);
    }
  };

  return (
    <div className="h-screen w-screen bg-slate-950 text-slate-100 flex flex-col overflow-hidden">
      {/* Top Header */}
      <Header
        autoMode={autoMode}
        onToggleAutoMode={handleToggleAutoMode}
        mcpOnline={mcpOnline}
        onOpenMcpModal={handleOpenGlobalMcp}
        theme={theme}
        onToggleTheme={handleToggleTheme}
      />

      {/* Main Grid: Sidebar + Dynamic Tabbed Views */}
      <div className="flex-1 flex overflow-hidden min-h-0">
        {/* Left Sidebar */}
        <Sidebar
          activeTab={activeTab}
          onTabChange={setActiveTab}
          plugins={plugins}
          onOpenUserGuide={() => setShowUserGuideModal(true)}
        />

        {/* Dynamic Main Workspace Tab Content */}
        <main className="flex-1 overflow-y-auto p-6 min-h-0">
          {activeTab === "monitor" && (
            <LiveExecutionMonitor
              executions={executions}
              selectedExecution={selectedExecution}
              onSelectExecution={setSelectedExecution}
              onSubmitQuery={handleSubmitQuery}
              onApprove={handleApprove}
              onReject={handleReject}
              onAbort={handleAbort}
              plugins={plugins}
              isSubmitting={isSubmitting}
            />
          )}

          {activeTab === "plugins" && (
            <PluginManagement
              plugins={plugins}
              onRegisterPlugin={handleRegisterPlugin}
              onUpdatePlugin={handleUpdatePlugin}
              onSyncPlugin={handleSyncPlugin}
              onUninstallPlugin={handleUninstallPlugin}
              onViewMcpConfig={handleOpenPluginMcp}
              onInstallZip={handleInstallZip}
              onInstallGit={handleInstallGit}
              onVerifyPlugin={handleVerifyPlugin}
            />
          )}

          {activeTab === "knowledge" && (
            <KnowledgeAndRules
              chunks={chunks}
              rules={rules}
              plugins={plugins}
              onSaveDocs={handleSaveDocs}
              onCreateRule={handleCreateRule}
              onUpdateRule={handleUpdateRule}
              onDeleteRule={handleDeleteRule}
            />
          )}

          {activeTab === "logs" && <AuditLogs executions={executions} plugins={plugins} />}
        </main>
      </div>

      {/* Reusable MCP Snippet Modal */}
      <McpConfigModal
        isOpen={showMcpModal}
        onClose={() => setShowMcpModal(false)}
        title={mcpModalTitle}
        subtitle={mcpModalSubtitle}
        configData={mcpModalData}
        isLoading={isMcpLoading}
      />

      {/* Interactive User Guide & Documentation Modal */}
      <UserGuideModal isOpen={showUserGuideModal} onClose={() => setShowUserGuideModal(false)} />
    </div>
  );
}
