"use client";

import React, { useEffect, useState, useCallback } from "react";
import { Header } from "@/components/Header";
import { Sidebar } from "@/components/Sidebar";
import { LiveExecutionMonitor } from "@/components/LiveExecutionMonitor";
import { PluginManagement } from "@/components/PluginManagement";
import { KnowledgeAndRules } from "@/components/KnowledgeAndRules";
import { AuditLogs } from "@/components/AuditLogs";
import {
  ActiveTab,
  CreateRuleRequest,
  ExecutionResponse,
  KnowledgeChunkResponse,
  PluginProfileResponse,
  RegisterPluginRequest,
  RuleResponse,
} from "@/types";
import {
  abortExecution,
  approveExecution,
  createRule,
  deleteRule,
  fetchAutoMode,
  fetchExecutions,
  fetchKnowledgeChunks,
  fetchPlugins,
  fetchRules,
  registerPlugin,
  rejectExecution,
  setAutoMode,
  submitExecution,
  syncPluginCatalog,
  updateKnowledgeDocs,
} from "@/lib/api";

const SSE_URL = process.env.NEXT_PUBLIC_SSE_URL || "http://127.0.0.1:8000/api/monitor/events";

export default function DashboardPage() {
  const [activeTab, setActiveTab] = useState<ActiveTab>("monitor");
  const [autoMode, setAutoModeState] = useState<boolean>(false);
  const [plugins, setPlugins] = useState<PluginProfileResponse[]>([]);
  const [executions, setExecutions] = useState<ExecutionResponse[]>([]);
  const [selectedExecution, setSelectedExecution] = useState<ExecutionResponse | null>(null);
  const [chunks, setChunks] = useState<KnowledgeChunkResponse[]>([]);
  const [rules, setRules] = useState<RuleResponse[]>([]);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [mcpOnline, setMcpOnline] = useState<boolean>(true);

  // Initial Data Fetching
  const loadInitialData = useCallback(async () => {
    try {
      const [fetchedPlugins, fetchedAutoMode, fetchedExecs, fetchedChunks, fetchedRules] =
        await Promise.allSettled([
          fetchPlugins(),
          fetchAutoMode(),
          fetchExecutions(),
          fetchKnowledgeChunks(),
          fetchRules(),
        ]);

      if (fetchedPlugins.status === "fulfilled") setPlugins(fetchedPlugins.value);
      if (fetchedAutoMode.status === "fulfilled") setAutoModeState(fetchedAutoMode.value);
      if (fetchedExecs.status === "fulfilled") {
        setExecutions(fetchedExecs.value);
        if (fetchedExecs.value.length > 0) {
          setSelectedExecution(fetchedExecs.value[0]);
        }
      }
      if (fetchedChunks.status === "fulfilled") setChunks(fetchedChunks.value);
      if (fetchedRules.status === "fulfilled") setRules(fetchedRules.value);
    } catch (err) {
      console.error("Initial data load error:", err);
    }
  }, []);

  useEffect(() => {
    loadInitialData();
  }, [loadInitialData]);

  // Clean Server-Sent Events Lifecycle per typescript_clean_code.md
  useEffect(() => {
    let eventSource: EventSource | null = null;
    let reconnectTimer: NodeJS.Timeout | null = null;

    const setupSSE = () => {
      try {
        eventSource = new EventSource(SSE_URL);

        eventSource.onopen = () => {
          setMcpOnline(true);
        };

        eventSource.onmessage = (event) => {
          try {
            const parsed = JSON.parse(event.data);
            const { event: eventType, data } = parsed;

            // When an execution state changes, re-fetch executions or update state immutably
            if (eventType.startsWith("execution_")) {
              fetchExecutions().then((updatedList) => {
                setExecutions(updatedList);
                if (data?.execution_id) {
                  const currentSelected = updatedList.find(
                    (e) => e.id === data.execution_id
                  );
                  if (currentSelected) {
                    setSelectedExecution(currentSelected);
                  }
                }
              });
            }
          } catch (err) {
            console.error("Failed to parse SSE payload:", err);
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

    // Mandatory cleanup per typescript_clean_code.md to prevent memory leaks
    return () => {
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
      const updated = await approveExecution(id);
      setExecutions((prev) => prev.map((e) => (e.id === id ? updated : e)));
      setSelectedExecution(updated);
    } catch (err) {
      alert(`Approval error: ${err instanceof Error ? err.message : "Unknown error"}`);
    }
  };

  const handleReject = async (id: string) => {
    try {
      const updated = await rejectExecution(id);
      setExecutions((prev) => prev.map((e) => (e.id === id ? updated : e)));
      setSelectedExecution(updated);
    } catch (err) {
      alert(`Rejection error: ${err instanceof Error ? err.message : "Unknown error"}`);
    }
  };

  const handleAbort = async (id: string) => {
    try {
      const updated = await abortExecution(id);
      setExecutions((prev) => prev.map((e) => (e.id === id ? updated : e)));
      setSelectedExecution(updated);
    } catch (err) {
      alert(`Abort error: ${err instanceof Error ? err.message : "Unknown error"}`);
    }
  };

  const handleRegisterPlugin = async (req: RegisterPluginRequest) => {
    const newPlugin = await registerPlugin(req);
    setPlugins((prev) => [...prev.filter((p) => p.id !== newPlugin.id), newPlugin]);
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

  const handleDeleteRule = async (ruleId: string) => {
    await deleteRule(ruleId);
    setRules((prev) => prev.filter((r) => r.id !== ruleId));
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      {/* Top Header */}
      <Header
        autoMode={autoMode}
        onToggleAutoMode={handleToggleAutoMode}
        mcpOnline={mcpOnline}
      />

      {/* Main Workspace: Sidebar + Dynamic Content */}
      <div className="flex flex-1 overflow-hidden">
        <Sidebar
          activeTab={activeTab}
          onTabChange={setActiveTab}
          plugins={plugins}
        />

        <main className="flex-1 p-6 overflow-y-auto max-h-[calc(100vh-4rem)]">
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
              onSyncPlugin={handleSyncPlugin}
            />
          )}

          {activeTab === "knowledge" && (
            <KnowledgeAndRules
              chunks={chunks}
              rules={rules}
              onSaveDocs={handleSaveDocs}
              onCreateRule={handleCreateRule}
              onDeleteRule={handleDeleteRule}
            />
          )}

          {activeTab === "logs" && <AuditLogs logs={executions} />}
        </main>
      </div>
    </div>
  );
}

