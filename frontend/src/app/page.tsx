"use client";

import React, { useState, useEffect, useCallback } from "react";
import { Header } from "@/components/Header";
import { Sidebar } from "@/components/Sidebar";
import { LiveExecutionMonitor, useExecutions } from "@/features/monitor";
import { PluginManagement, usePlugins } from "@/features/plugins";
import { KnowledgeAndRules } from "@/features/knowledge";
import { AuditLogs } from "@/features/audit";
import { McpConfigModal } from "@/features/mcp";
import { UserGuideModal } from "@/features/guide";
import {
  ActiveTab,
  KnowledgeChunkResponse,
  McpConfigResponse,
  PluginProfileResponse,
  RuleResponse,
} from "@/types";
import {
  fetchAutoMode,
  fetchGlobalMcpConfig,
  fetchKnowledgeChunks,
  fetchPluginMcpConfig,
  fetchRules,
  setAutoMode as apiSetAutoMode,
  updateKnowledgeDocs,
  createRule,
  updateRule,
  deleteRule,
} from "@/shared/lib/api";
import { ToastProvider, useToast } from "@/shared/hooks/useToast";
import { useTheme } from "@/shared/hooks/useTheme";
import { ErrorBoundary } from "@/shared/ui/ErrorBoundary";

function DashboardContent() {
  const [activeTab, setActiveTab] = useState<ActiveTab>("monitor");
  const [autoMode, setAutoMode] = useState<boolean>(false);
  const [chunks, setChunks] = useState<KnowledgeChunkResponse[]>([]);
  const [rules, setRules] = useState<RuleResponse[]>([]);
  const { theme, toggleTheme } = useTheme();
  const { showToast } = useToast();

  const {
    executions,
    selectedExecution,
    setSelectedExecution,
    submitQuery,
    approve,
    reject,
    abort,
    sseStatus,
  } = useExecutions();
  const {
    plugins,
    register,
    installZip,
    installGit,
    updateConfig,
    syncCatalog,
    verify,
    uninstall,
  } = usePlugins();

  const [showMcpModal, setShowMcpModal] = useState<boolean>(false);
  const [showGuideModal, setShowGuideModal] = useState<boolean>(false);
  const [mcpModalData, setMcpModalData] = useState<McpConfigResponse | null>(null);
  const [mcpModalTitle, setMcpModalTitle] = useState<string>("MCP Connection Configuration");
  const [mcpModalSubtitle, setMcpModalSubtitle] = useState<string>(
    "Global AegisGate MCP Server configuration"
  );
  const [isMcpLoading, setIsMcpLoading] = useState<boolean>(false);

  useEffect(() => {
    Promise.all([
      fetchAutoMode().then(setAutoMode),
      fetchKnowledgeChunks().then(setChunks),
      fetchRules().then(setRules),
    ]).catch(console.error);
  }, []);

  const handleToggleAutoMode = async () => {
    try {
      const updated = await apiSetAutoMode(!autoMode);
      setAutoMode(updated);
      showToast(`Auto approval mode ${updated ? "enabled" : "disabled"}`, "info");
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : "Failed to toggle auto mode", "error");
    }
  };

  const handleOpenGlobalMcp = async () => {
    setMcpModalTitle("AegisGate Global MCP Connection");
    setMcpModalSubtitle("Connect Claude Desktop, Cursor, or Cline to AegisGate Core Gateway");
    setShowMcpModal(true);
    setIsMcpLoading(true);
    try {
      setMcpModalData(await fetchGlobalMcpConfig());
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
      setMcpModalData(await fetchPluginMcpConfig(plugin.id));
    } finally {
      setIsMcpLoading(false);
    }
  };

  const reloadChunks = useCallback(async () => setChunks(await fetchKnowledgeChunks()), []);
  const reloadRules = useCallback(async () => setRules(await fetchRules()), []);

  return (
    <div className="h-screen w-screen bg-slate-100 dark:bg-slate-950 text-slate-900 dark:text-slate-100 flex flex-col overflow-hidden">
      <Header
        autoMode={autoMode}
        onToggleAutoMode={handleToggleAutoMode}
        sseStatus={sseStatus}
        onOpenMcpModal={handleOpenGlobalMcp}
        theme={theme}
        onToggleTheme={toggleTheme}
      />
      <div className="flex-1 flex overflow-hidden min-h-0">
        <Sidebar
          activeTab={activeTab}
          onTabChange={setActiveTab}
          plugins={plugins}
          onOpenUserGuide={() => setShowGuideModal(true)}
        />
        <main className="flex-1 overflow-y-auto p-6 min-h-0">
          <ErrorBoundary>
            {activeTab === "monitor" && (
              <LiveExecutionMonitor
                executions={executions}
                selectedExecution={selectedExecution}
                onSelectExecution={setSelectedExecution}
                onSubmitQuery={submitQuery}
                onApprove={approve}
                onReject={reject}
                onAbort={abort}
                plugins={plugins}
              />
            )}
            {activeTab === "plugins" && (
              <PluginManagement
                plugins={plugins}
                onRegisterPlugin={register}
                onUpdatePlugin={updateConfig}
                onSyncPlugin={async (id) => {
                  await syncCatalog(id);
                  await reloadChunks();
                }}
                onUninstallPlugin={uninstall}
                onViewMcpConfig={handleOpenPluginMcp}
                onInstallZip={installZip}
                onInstallGit={installGit}
                onVerifyPlugin={verify}
              />
            )}
            {activeTab === "knowledge" && (
              <KnowledgeAndRules
                chunks={chunks}
                rules={rules}
                plugins={plugins}
                onSaveDocs={async (id, d, s) => {
                  await updateKnowledgeDocs(id, d, s);
                  await reloadChunks();
                }}
                onCreateRule={async (r) => {
                  await createRule(r);
                  await reloadRules();
                }}
                onUpdateRule={async (id, r) => {
                  await updateRule(id, r);
                  await reloadRules();
                }}
                onDeleteRule={async (id) => {
                  await deleteRule(id);
                  await reloadRules();
                }}
              />
            )}
            {activeTab === "logs" && <AuditLogs executions={executions} plugins={plugins} />}
          </ErrorBoundary>
        </main>
      </div>
      <McpConfigModal
        isOpen={showMcpModal}
        onClose={() => setShowMcpModal(false)}
        title={mcpModalTitle}
        subtitle={mcpModalSubtitle}
        configData={mcpModalData}
        isLoading={isMcpLoading}
      />
      <UserGuideModal isOpen={showGuideModal} onClose={() => setShowGuideModal(false)} />
    </div>
  );
}

export default function DashboardPage() {
  return (
    <ToastProvider>
      <ErrorBoundary>
        <DashboardContent />
      </ErrorBoundary>
    </ToastProvider>
  );
}
