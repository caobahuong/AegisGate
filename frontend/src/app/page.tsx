"use client";

import React from "react";
import { Header } from "@/components/Header";
import { Sidebar } from "@/components/Sidebar";
import { LiveExecutionMonitor, useExecutions } from "@/features/monitor";
import { PluginManagement, usePlugins } from "@/features/plugins";
import { KnowledgeAndRules } from "@/features/knowledge";
import { AuditLogs } from "@/features/audit";
import { McpConfigModal } from "@/features/mcp";
import { UserGuideModal } from "@/features/guide";
import { updateKnowledgeDocs, createRule, updateRule, deleteRule } from "@/shared/lib/api";
import { ToastProvider } from "@/shared/hooks/useToast";
import { useTheme } from "@/shared/hooks/useTheme";
import { useDashboardState } from "@/shared/hooks/useDashboardState";
import { ErrorBoundary } from "@/shared/ui/ErrorBoundary";

function DashboardContent() {
  const { theme, toggleTheme } = useTheme();
  const dash = useDashboardState();
  const exec = useExecutions();
  const plugs = usePlugins();

  return (
    <div className="h-screen w-screen bg-slate-100 dark:bg-slate-950 text-slate-900 dark:text-slate-100 flex flex-col overflow-hidden">
      <Header
        autoMode={dash.autoMode}
        onToggleAutoMode={dash.handleToggleAutoMode}
        sseStatus={exec.sseStatus}
        onOpenMcpModal={dash.handleOpenGlobalMcp}
        theme={theme}
        onToggleTheme={toggleTheme}
      />
      <div className="flex-1 flex overflow-hidden min-h-0">
        <Sidebar
          activeTab={dash.activeTab}
          onTabChange={dash.setActiveTab}
          plugins={plugs.plugins}
          onOpenUserGuide={() => dash.setShowGuideModal(true)}
        />
        <main className="flex-1 overflow-y-auto p-6 min-h-0">
          <ErrorBoundary>
            {dash.activeTab === "monitor" && (
              <LiveExecutionMonitor
                executions={exec.executions}
                selectedExecution={exec.selectedExecution}
                onSelectExecution={exec.setSelectedExecution}
                onSubmitQuery={exec.submitQuery}
                onApprove={exec.approve}
                onReject={exec.reject}
                onAbort={exec.abort}
                plugins={plugs.plugins}
              />
            )}
            {dash.activeTab === "plugins" && (
              <PluginManagement
                plugins={plugs.plugins}
                onRegisterPlugin={plugs.register}
                onInstallZip={plugs.installZip}
                onInstallGit={plugs.installGit}
                onUpdatePlugin={plugs.updateConfig}
                onSyncPlugin={async (id) => {
                  await plugs.syncCatalog(id);
                }}
                onVerifyPlugin={plugs.verify}
                onUninstallPlugin={plugs.uninstall}
                onViewMcpConfig={dash.handleOpenPluginMcp}
              />
            )}
            {dash.activeTab === "knowledge" && (
              <KnowledgeAndRules
                chunks={dash.chunks}
                rules={dash.rules}
                plugins={plugs.plugins}
                onSaveDocs={async (chunkId, docText, skillsText) => {
                  await updateKnowledgeDocs(chunkId, docText, skillsText);
                  await dash.reloadChunks();
                }}
                onCreateRule={async (rule) => {
                  await createRule(rule);
                  await dash.reloadRules();
                }}
                onUpdateRule={async (id, rule) => {
                  await updateRule(id, rule);
                  await dash.reloadRules();
                }}
                onDeleteRule={async (id) => {
                  await deleteRule(id);
                  await dash.reloadRules();
                }}
              />
            )}
            {dash.activeTab === "logs" && (
              <AuditLogs executions={exec.executions} plugins={plugs.plugins} />
            )}
          </ErrorBoundary>
        </main>
      </div>
      <McpConfigModal
        isOpen={dash.showMcpModal}
        onClose={() => dash.setShowMcpModal(false)}
        title={dash.mcpModalTitle}
        subtitle={dash.mcpModalSubtitle}
        configData={dash.mcpModalData}
        isLoading={dash.isMcpLoading}
      />
      <UserGuideModal isOpen={dash.showGuideModal} onClose={() => dash.setShowGuideModal(false)} />
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
