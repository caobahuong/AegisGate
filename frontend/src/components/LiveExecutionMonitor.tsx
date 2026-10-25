"use client";

import React, { useState, useMemo } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  Clock,
  Play,
  RotateCw,
  Send,
  StopCircle,
  XCircle,
  Layers,
  Terminal,
  ShieldAlert,
  Activity,
  Database,
} from "lucide-react";
import { ExecutionResponse, PluginProfileResponse } from "@/types";
import { cn } from "@/lib/utils";

interface LiveExecutionMonitorProps {
  executions: ExecutionResponse[];
  selectedExecution: ExecutionResponse | null;
  onSelectExecution: (exec: ExecutionResponse) => void;
  onSubmitQuery: (targetId: string, query: string, reasoning: string) => Promise<void>;
  onApprove: (id: string) => Promise<void>;
  onReject: (id: string) => Promise<void>;
  onAbort: (id: string) => Promise<void>;
  plugins: PluginProfileResponse[];
  isSubmitting?: boolean;
}

type SessionFilter = "ALL" | "PENDING" | "RUNNING" | "BLOCKED" | "COMPLETED";

export const LiveExecutionMonitor: React.FC<LiveExecutionMonitorProps> = ({
  executions,
  selectedExecution,
  onSelectExecution,
  onSubmitQuery,
  onApprove,
  onReject,
  onAbort,
  plugins,
  isSubmitting = false,
}) => {
  // Query Form State
  const [targetId, setTargetId] = useState<string>(
    plugins[0]?.id || "sqlserver_prod"
  );
  const [query, setQuery] = useState<string>(
    "SELECT o.OrderID, o.OrderDate, o.TotalAmount\nFROM dbo.Orders o\nWHERE o.Status = 'Completed';"
  );
  const [reasoning, setReasoning] = useState<string>(
    "AI Agent retrieving latest completed customer orders for dashboard KPI computation."
  );
  const [actionLoading, setActionLoading] = useState<boolean>(false);

  // Operational Session Category Filter
  const [sessionFilter, setSessionFilter] = useState<SessionFilter>("ALL");

  // Filtered session cohorts
  const pendingSessions = useMemo(
    () => executions.filter((ex) => ex.status === "PAUSED_FOR_REVIEW" || ex.status === "DRY_RUN"),
    [executions]
  );
  const runningSessions = useMemo(
    () => executions.filter((ex) => ex.status === "EXECUTING"),
    [executions]
  );
  const blockedSessions = useMemo(
    () =>
      executions.filter(
        (ex) =>
          ex.status === "REJECTED" ||
          ex.status === "TIMEOUT" ||
          ex.status === "ABORTED"
      ),
    [executions]
  );
  const completedSessions = useMemo(
    () => executions.filter((ex) => ex.status === "COMPLETED"),
    [executions]
  );

  const filteredExecutions = useMemo(() => {
    switch (sessionFilter) {
      case "PENDING":
        return pendingSessions;
      case "RUNNING":
        return runningSessions;
      case "BLOCKED":
        return blockedSessions;
      case "COMPLETED":
        return completedSessions;
      case "ALL":
      default:
        return executions;
    }
  }, [sessionFilter, executions, pendingSessions, runningSessions, blockedSessions, completedSessions]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || isSubmitting) return;
    await onSubmitQuery(targetId, query, reasoning);
  };

  const handleApprove = async () => {
    if (!selectedExecution) return;
    setActionLoading(true);
    try {
      await onApprove(selectedExecution.id);
    } finally {
      setActionLoading(false);
    }
  };

  const handleReject = async () => {
    if (!selectedExecution) return;
    setActionLoading(true);
    try {
      await onReject(selectedExecution.id);
    } finally {
      setActionLoading(false);
    }
  };

  const handleAbort = async () => {
    if (!selectedExecution) return;
    setActionLoading(true);
    try {
      await onAbort(selectedExecution.id);
    } finally {
      setActionLoading(false);
    }
  };

  // Status badge for detailed Gatekeeper panel
  const renderStatusBadge = (status: string) => {
    switch (status) {
      case "PAUSED_FOR_REVIEW":
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded text-xs font-semibold bg-amber-500/15 text-amber-400 border border-amber-500/30 animate-pulse">
            <Clock className="h-3 w-3 mr-1" /> PAUSED FOR REVIEW
          </span>
        );
      case "EXECUTING":
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded text-xs font-semibold bg-indigo-500/15 text-indigo-400 border border-indigo-500/30 animate-pulse">
            <RotateCw className="h-3 w-3 mr-1 animate-spin" /> EXECUTING
          </span>
        );
      case "COMPLETED":
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded text-xs font-semibold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
            <CheckCircle2 className="h-3 w-3 mr-1" /> COMPLETED
          </span>
        );
      case "REJECTED":
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded text-xs font-semibold bg-red-500/15 text-red-400 border border-red-500/30">
            <XCircle className="h-3 w-3 mr-1" /> REJECTED
          </span>
        );
      case "TIMEOUT":
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded text-xs font-semibold bg-red-500/15 text-red-400 border border-red-500/30">
            <AlertTriangle className="h-3 w-3 mr-1" /> TIMEOUT (KILLED)
          </span>
        );
      case "ABORTED":
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded text-xs font-semibold bg-slate-800 text-slate-400 border border-slate-700">
            <StopCircle className="h-3 w-3 mr-1" /> ABORTED
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded text-xs font-semibold bg-slate-800 text-slate-300">
            {status}
          </span>
        );
    }
  };

  // Compact status badge for operational session cards
  const renderCompactStatus = (status: string) => {
    switch (status) {
      case "PAUSED_FOR_REVIEW":
      case "DRY_RUN":
        return (
          <span className="flex items-center text-amber-400 font-semibold text-[11px]">
            <Clock className="h-3 w-3 mr-1 animate-pulse" />
            Pending Review
          </span>
        );
      case "EXECUTING":
        return (
          <span className="flex items-center text-indigo-400 font-semibold text-[11px]">
            <RotateCw className="h-3 w-3 mr-1 animate-spin" />
            Running
          </span>
        );
      case "COMPLETED":
        return (
          <span className="flex items-center text-emerald-400 font-semibold text-[11px]">
            <CheckCircle2 className="h-3 w-3 mr-1" />
            Completed
          </span>
        );
      case "REJECTED":
        return (
          <span className="flex items-center text-red-400 font-semibold text-[11px]">
            <XCircle className="h-3 w-3 mr-1" />
            Rejected
          </span>
        );
      case "TIMEOUT":
        return (
          <span className="flex items-center text-red-400 font-semibold text-[11px]">
            <AlertTriangle className="h-3 w-3 mr-1" />
            Timeout (Killed)
          </span>
        );
      case "ABORTED":
        return (
          <span className="flex items-center text-slate-400 font-semibold text-[11px]">
            <StopCircle className="h-3 w-3 mr-1" />
            Aborted
          </span>
        );
      default:
        return (
          <span className="text-slate-400 text-[11px] font-mono">
            {status}
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* ========================================================
          LIVE OPERATIONAL SESSION HUB (State-based Cockpit)
         ======================================================== */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3.5 shadow-sm">
        {/* Header & Filter Controls */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-800">
          <div className="flex items-center space-x-2.5">
            <div className="p-1.5 rounded-lg bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
              <Activity className="h-4 w-4" />
            </div>
            <div>
              <h2 className="text-xs font-bold uppercase tracking-wider text-slate-100 flex items-center space-x-2">
                <span>Live Operational Sessions</span>
                <span className="text-[10px] font-normal text-slate-400 font-mono">
                  ({executions.length} total)
                </span>
              </h2>
              <p className="text-[11px] text-slate-400">
                Real-time operational cockpit for monitoring and intercepting active query sessions
              </p>
            </div>
          </div>

          {/* Lifecycle State Category Tabs */}
          <div className="flex items-center space-x-1.5 overflow-x-auto pb-1 sm:pb-0">
            {/* Filter: All */}
            <button
              type="button"
              onClick={() => setSessionFilter("ALL")}
              data-testid="filter-all-btn"
              className={cn(
                "px-2.5 py-1 rounded-lg text-xs font-medium transition-all flex items-center space-x-1.5 border",
                sessionFilter === "ALL"
                  ? "bg-slate-800 text-slate-100 border-slate-700 shadow-sm"
                  : "bg-slate-950/60 text-slate-400 border-slate-800/80 hover:text-slate-200 hover:border-slate-700"
              )}
            >
              <Database className="h-3 w-3" />
              <span>All</span>
              <span className="ml-1 px-1.5 py-0.2 rounded-full text-[10px] bg-slate-700 text-slate-100 font-mono">
                {executions.length}
              </span>
            </button>

            {/* Filter: Pending Review */}
            <button
              type="button"
              onClick={() => setSessionFilter("PENDING")}
              data-testid="filter-pending-btn"
              className={cn(
                "px-2.5 py-1 rounded-lg text-xs font-medium transition-all flex items-center space-x-1.5 border",
                sessionFilter === "PENDING"
                  ? "bg-amber-500/20 text-amber-300 border-amber-500/50 shadow-sm shadow-amber-500/10"
                  : pendingSessions.length > 0
                  ? "bg-amber-500/10 text-amber-400 border-amber-500/30 hover:bg-amber-500/15"
                  : "bg-slate-950/60 text-slate-400 border-slate-800/80 hover:text-slate-200"
              )}
            >
              <Clock className={cn("h-3 w-3", pendingSessions.length > 0 && "animate-pulse text-amber-400")} />
              <span>Pending Review</span>
              <span
                className={cn(
                  "ml-1 px-1.5 py-0.2 rounded-full text-[10px] font-mono",
                  pendingSessions.length > 0
                    ? "bg-amber-600 text-white font-bold animate-pulse dark:bg-amber-500/30 dark:text-amber-300"
                    : "bg-slate-800 text-slate-400"
                )}
              >
                {pendingSessions.length}
              </span>
            </button>

            {/* Filter: Running */}
            <button
              type="button"
              onClick={() => setSessionFilter("RUNNING")}
              data-testid="filter-running-btn"
              className={cn(
                "px-2.5 py-1 rounded-lg text-xs font-medium transition-all flex items-center space-x-1.5 border",
                sessionFilter === "RUNNING"
                  ? "bg-indigo-50 text-indigo-700 border-indigo-300 dark:bg-indigo-500/20 dark:text-indigo-300 dark:border-indigo-500/50 shadow-xs"
                  : runningSessions.length > 0
                  ? "bg-indigo-50/80 text-indigo-700 border-indigo-200 hover:bg-indigo-100 dark:bg-indigo-500/10 dark:text-indigo-400 dark:border-indigo-500/30 dark:hover:bg-indigo-500/15"
                  : "bg-slate-850 text-slate-400 border border-slate-800 hover:text-slate-100"
              )}
            >
              <RotateCw className={cn("h-3 w-3", runningSessions.length > 0 && "animate-spin text-indigo-600 dark:text-indigo-400")} />
              <span>Running</span>
              <span
                className={cn(
                  "ml-1 px-1.5 py-0.2 rounded-full text-[10px] font-mono",
                  runningSessions.length > 0
                    ? "bg-indigo-600 text-white font-bold dark:bg-indigo-500/30 dark:text-indigo-300"
                    : "bg-slate-200 text-slate-700 dark:bg-slate-800 dark:text-slate-400"
                )}
              >
                {runningSessions.length}
              </span>
            </button>

            {/* Filter: Blocked */}
            <button
              type="button"
              onClick={() => setSessionFilter("BLOCKED")}
              data-testid="filter-blocked-btn"
              className={cn(
                "px-2.5 py-1 rounded-lg text-xs font-medium transition-all flex items-center space-x-1.5 border",
                sessionFilter === "BLOCKED"
                  ? "bg-red-500/20 text-red-300 border-red-500/50 shadow-sm shadow-red-500/10"
                  : blockedSessions.length > 0
                  ? "bg-red-500/10 text-red-400 border-red-500/30 hover:bg-red-500/15"
                  : "bg-slate-950/60 text-slate-400 border-slate-800/80 hover:text-slate-200"
              )}
            >
              <ShieldAlert className="h-3 w-3" />
              <span>Blocked / Failed</span>
              <span
                className={cn(
                  "ml-1 px-1.5 py-0.2 rounded-full text-[10px] font-mono",
                  blockedSessions.length > 0
                    ? "bg-red-600 text-white font-bold dark:bg-red-500/30 dark:text-red-300"
                    : "bg-slate-800 text-slate-400"
                )}
              >
                {blockedSessions.length}
              </span>
            </button>

            {/* Filter: Completed */}
            <button
              type="button"
              onClick={() => setSessionFilter("COMPLETED")}
              data-testid="filter-completed-btn"
              className={cn(
                "px-2.5 py-1 rounded-lg text-xs font-medium transition-all flex items-center space-x-1.5 border",
                sessionFilter === "COMPLETED"
                  ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/50 shadow-sm shadow-emerald-500/10"
                  : completedSessions.length > 0
                  ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30 hover:bg-emerald-500/15"
                  : "bg-slate-950/60 text-slate-400 border-slate-800/80 hover:text-slate-200"
              )}
            >
              <CheckCircle2 className="h-3 w-3" />
              <span>Completed</span>
              <span
                className={cn(
                  "ml-1 px-1.5 py-0.2 rounded-full text-[10px] font-mono",
                  completedSessions.length > 0
                    ? "bg-emerald-600 text-white font-bold dark:bg-emerald-500/30 dark:text-emerald-300"
                    : "bg-slate-800 text-slate-400"
                )}
              >
                {completedSessions.length}
              </span>
            </button>
          </div>
        </div>

        {/* Operational Sessions Carousel / Cards Strip */}
        <div>
          {filteredExecutions.length === 0 ? (
            <div className="p-5 rounded-lg border border-slate-800/80 bg-slate-950/40 text-center py-6 text-xs text-slate-400">
              {sessionFilter === "PENDING" && (
                <div className="flex flex-col items-center space-y-1">
                  <CheckCircle2 className="h-5 w-5 text-emerald-400/80 mb-1" />
                  <span className="font-semibold text-slate-200">No queries awaiting review</span>
                  <span className="text-[11px] text-slate-500">
                    All AI queries have been processed or the gateway is currently idle.
                  </span>
                </div>
              )}
              {sessionFilter === "RUNNING" && (
                <div className="flex flex-col items-center space-y-1">
                  <Activity className="h-5 w-5 text-slate-500 mb-1" />
                  <span className="font-semibold text-slate-200">No active sessions running in background</span>
                  <span className="text-[11px] text-slate-500">
                    Gateway is ready to accept incoming queries from AI Clients via FastMCP.
                  </span>
                </div>
              )}
              {sessionFilter === "BLOCKED" && (
                <div className="flex flex-col items-center space-y-1">
                  <ShieldAlert className="h-5 w-5 text-emerald-400/80 mb-1" />
                  <span className="font-semibold text-slate-200">No blocked or rejected queries</span>
                  <span className="text-[11px] text-slate-500">
                    Zero governance policy violations or execution timeouts recorded.
                  </span>
                </div>
              )}
              {sessionFilter === "COMPLETED" && (
                <div className="flex flex-col items-center space-y-1">
                  <Database className="h-5 w-5 text-slate-500 mb-1" />
                  <span className="font-semibold text-slate-200">No completed sessions yet</span>
                  <span className="text-[11px] text-slate-500">
                    Submit a test query below to verify the full execution lifecycle.
                  </span>
                </div>
              )}
              {sessionFilter === "ALL" && (
                <div className="flex flex-col items-center space-y-1">
                  <Activity className="h-5 w-5 text-slate-500 mb-1" />
                  <span className="font-semibold text-slate-200">No execution sessions recorded</span>
                  <span className="text-[11px] text-slate-500">
                    Submit a query from the simulator below or connect an AI agent (Claude, Cursor, Cline) via MCP.
                  </span>
                </div>
              )}
            </div>
          ) : (
            <div className="flex items-stretch space-x-3 overflow-x-auto pb-2 scrollbar-thin scrollbar-thumb-slate-800">
              {filteredExecutions.slice(0, 15).map((ex) => {
                const isSelected = selectedExecution?.id === ex.id;
                const isPending = ex.status === "PAUSED_FOR_REVIEW" || ex.status === "DRY_RUN";
                const isRunning = ex.status === "EXECUTING";
                const isBlocked =
                  ex.status === "REJECTED" ||
                  ex.status === "TIMEOUT" ||
                  ex.status === "ABORTED";
                const isCompleted = ex.status === "COMPLETED";

                return (
                  <button
                    key={ex.id}
                    onClick={() => onSelectExecution(ex)}
                    data-testid={`session-pill-${ex.id}`}
                    className={cn(
                      "flex-shrink-0 text-left rounded-xl border p-3 transition-all cursor-pointer min-w-[210px] max-w-[260px] flex flex-col justify-between space-y-2",
                      isSelected
                        ? "bg-slate-900 border-indigo-500 ring-1 ring-indigo-500/50 shadow-md shadow-indigo-500/10"
                        : "bg-slate-950/70 border-slate-800/80 hover:border-slate-700 hover:bg-slate-900/60",
                      isPending && !isSelected && "border-amber-500/40 bg-amber-500/[0.04]",
                      isRunning && !isSelected && "border-indigo-500/40 bg-indigo-500/[0.04]"
                    )}
                  >
                    <div className="flex items-center justify-between w-full">
                      <span className="font-mono text-xs font-bold text-slate-200">
                        #{ex.id}
                      </span>
                      <span
                        className={cn(
                          "text-[10px] font-semibold px-1.5 py-0.5 rounded uppercase tracking-wider font-mono",
                          ex.query_type === "WRITE"
                            ? "bg-purple-100 text-purple-800 border border-purple-400 dark:bg-purple-500/20 dark:text-purple-300 dark:border-purple-500/30"
                            : "bg-sky-100 text-sky-800 border border-sky-400 dark:bg-sky-500/20 dark:text-sky-300 dark:border-sky-500/30"
                        )}
                      >
                        {ex.query_type}
                      </span>
                    </div>

                    <div className="flex items-center space-x-1.5 text-xs">
                      {renderCompactStatus(ex.status)}
                    </div>

                    <div className="flex items-center justify-between text-[10px] text-slate-400 pt-1.5 border-t border-slate-800/60 w-full">
                      <span
                        className="truncate max-w-[110px] font-medium text-slate-400"
                        title={ex.target_id}
                      >
                        {ex.target_id}
                      </span>
                      {isPending && (
                        <span className="text-amber-400 font-bold flex items-center animate-pulse">
                          Action Required
                        </span>
                      )}
                      {isRunning && (
                        <span className="text-indigo-400 font-mono font-semibold">
                          SPID: {ex.spid ?? "..."}
                        </span>
                      )}
                      {isCompleted && (
                        <span className="font-mono text-emerald-400/90 font-medium">
                          {ex.execution_time_ms !== null ? `${ex.execution_time_ms}ms` : "OK"}
                        </span>
                      )}
                      {isBlocked && (
                        <span className="text-red-400 font-medium">
                          {ex.status === "TIMEOUT" ? "Timeout" : "Violation"}
                        </span>
                      )}
                    </div>
                  </button>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* 3-Column Balanced Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
        {/* ========================================================
            COLUMN 1: AI Query & Reasoning
           ======================================================== */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4 shadow-sm">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <div className="flex items-center space-x-2">
              <Terminal className="h-4 w-4 text-indigo-400" />
              <h2 className="text-xs font-bold uppercase tracking-wider text-slate-200">
                1. AI Query & Reasoning
              </h2>
            </div>
            {selectedExecution && (
              <span className="text-[10px] font-mono text-slate-400">
                #{selectedExecution.id}
              </span>
            )}
          </div>

          {/* Quick Submit Form */}
          <form onSubmit={handleSubmit} className="space-y-3">
            <div>
              <label className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">
                Target Plugin
              </label>
              <select
                value={targetId}
                onChange={(e) => setTargetId(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500"
              >
                {plugins.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} ({p.id})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">
                Raw Query Statement (SQL / Command)
              </label>
              <textarea
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                rows={5}
                className="w-full font-mono text-xs bg-slate-950 border border-slate-800 rounded p-2.5 text-slate-100 focus:outline-none focus:border-indigo-500 leading-relaxed resize-y"
                placeholder="Enter SQL or database statement..."
              />
            </div>

            <div>
              <label className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">
                AI Intent / Reasoning
              </label>
              <textarea
                value={reasoning}
                onChange={(e) => setReasoning(e.target.value)}
                rows={2}
                className="w-full text-xs bg-slate-950 border border-slate-800 rounded p-2.5 text-slate-300 focus:outline-none focus:border-indigo-500 leading-normal resize-none"
                placeholder="Explain the AI's intent..."
              />
            </div>

            <div className="flex space-x-2 pt-1">
              <button
                type="submit"
                disabled={isSubmitting}
                className="flex-1 flex items-center justify-center space-x-2 bg-indigo-600 hover:bg-indigo-500 text-white px-3 py-2 rounded-lg text-xs font-semibold shadow-md shadow-indigo-600/30 transition-colors disabled:opacity-50"
              >
                <Send className="h-3.5 w-3.5" />
                <span>{isSubmitting ? "Submitting..." : "Send Query to AegisGate"}</span>
              </button>
            </div>
          </form>

          {/* Preset Rule-Testing Queries */}
          <div className="pt-2 border-t border-slate-800 space-y-1.5">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
              Quick Rule Violation Tests:
            </span>
            <div className="flex flex-wrap gap-1.5">
              <button
                type="button"
                onClick={() => {
                  setQuery(
                    "SELECT o.OrderID, a.Action\nFROM dbo.Orders o\nINNER JOIN dbo.AuditLogs a ON o.OrderID = a.LogID;"
                  );
                  setReasoning("Test query triggering FORBID_JOIN rule between Orders and AuditLogs.");
                }}
                className="px-2 py-1 rounded bg-slate-950 hover:bg-slate-800 border border-slate-800 text-[10px] text-amber-400 font-mono transition-colors"
              >
                Forbidden JOIN Test
              </button>
              <button
                type="button"
                onClick={() => {
                  setQuery("SELECT * FROM dbo.Orders;");
                  setReasoning("Test query triggering Table Scan rule due to missing WHERE filter.");
                }}
                className="px-2 py-1 rounded bg-slate-950 hover:bg-slate-800 border border-slate-800 text-[10px] text-red-400 font-mono transition-colors"
              >
                Table Scan Test
              </button>
            </div>
          </div>
        </div>

        {/* ========================================================
            COLUMN 2: Plugin Dry-Run & Explain Plan
           ======================================================== */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4 shadow-sm">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <div className="flex items-center space-x-2">
              <Layers className="h-4 w-4 text-indigo-400" />
              <h2 className="text-xs font-bold uppercase tracking-wider text-slate-200">
                2. Dry-Run & Explain Plan
              </h2>
            </div>
            {selectedExecution && (
              <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                {selectedExecution.query_type} Query
              </span>
            )}
          </div>

          {!selectedExecution ? (
            <div className="py-16 text-center text-slate-500 text-xs">
              Select an execution session or submit a query to view Dry-Run analysis.
            </div>
          ) : (
            <div className="space-y-4">
              {/* Violations Warning Banner */}
              {selectedExecution.violations && selectedExecution.violations.length > 0 ? (
                <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 space-y-1">
                  <div className="flex items-center space-x-2 text-xs font-bold">
                    <ShieldAlert className="h-4 w-4 text-red-400" />
                    <span>Rule Violations Detected ({selectedExecution.violations.length})</span>
                  </div>
                  <ul className="list-disc list-inside text-xs space-y-1 pt-1 text-red-300">
                    {selectedExecution.violations.map((violation, i) => (
                      <li key={i} className="leading-snug">{violation}</li>
                    ))}
                  </ul>
                </div>
              ) : (
                <div className="p-2.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center space-x-2 text-xs font-medium">
                  <CheckCircle2 className="h-4 w-4 text-emerald-400 flex-shrink-0" />
                  <span>Zero rule violations. Query meets governance criteria.</span>
                </div>
              )}

              {/* Explain Plan Structured Viewer */}
              <div>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
                    Execution Plan (SHOWPLAN)
                  </span>
                  <span className="text-[10px] font-mono text-slate-500">
                    Target: {selectedExecution.target_id}
                  </span>
                </div>
                <div className="font-mono text-xs bg-slate-950 border border-slate-800 rounded p-3 text-slate-300 max-h-64 overflow-y-auto leading-relaxed">
                  <pre className="whitespace-pre-wrap break-all">
                    {selectedExecution.explain_plan
                      ? JSON.stringify(selectedExecution.explain_plan, null, 2)
                      : "No explain plan data."}
                  </pre>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* ========================================================
            COLUMN 3: Gatekeeper & Interactive Controls
           ======================================================== */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-5 shadow-sm">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-200">
              3. Gatekeeper Controls
            </h2>
            {selectedExecution && renderStatusBadge(selectedExecution.status)}
          </div>

          {!selectedExecution ? (
            <div className="py-16 text-center text-slate-500 text-xs">
              No active session selected.
            </div>
          ) : (
            <div className="space-y-5">
              {/* Session Meta Card */}
              <div className="bg-slate-950 border border-slate-800 rounded-lg p-3 space-y-2 text-xs">
                <div className="flex justify-between">
                  <span className="text-slate-400">Execution ID:</span>
                  <span className="font-mono text-slate-200 font-bold">#{selectedExecution.id}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Mode:</span>
                  <span className="text-slate-200 font-medium">
                    {selectedExecution.auto_approved ? "Auto Approval ON" : "Manual Approval"}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Database SPID:</span>
                  <span className="font-mono text-slate-200">
                    {selectedExecution.spid ? selectedExecution.spid : "None allocated"}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-slate-400">Duration:</span>
                  <span className="font-mono text-indigo-400 font-bold">
                    {selectedExecution.execution_time_ms !== null
                      ? `${selectedExecution.execution_time_ms} ms`
                      : "Pending"}
                  </span>
                </div>
              </div>

              {/* Interactive Control Buttons */}
              <div className="space-y-2.5">
                {selectedExecution.status === "PAUSED_FOR_REVIEW" && (
                  <div className="space-y-2">
                    <p className="text-xs text-amber-300 font-medium leading-snug">
                      Plan verified. Query is paused awaiting human approval.
                    </p>
                    <div className="grid grid-cols-2 gap-2">
                      <button
                        onClick={handleApprove}
                        disabled={actionLoading}
                        className="flex items-center justify-center space-x-1.5 bg-emerald-600 hover:bg-emerald-500 text-white px-3 py-2 rounded-lg text-xs font-semibold shadow-md shadow-emerald-600/20 transition-colors disabled:opacity-50"
                      >
                        <Play className="h-3.5 w-3.5" />
                        <span>Approve & Run</span>
                      </button>
                      <button
                        onClick={handleReject}
                        disabled={actionLoading}
                        className="flex items-center justify-center space-x-1.5 bg-slate-800 hover:bg-red-900/60 text-slate-200 hover:text-red-300 border border-slate-700 px-3 py-2 rounded-lg text-xs font-semibold transition-colors disabled:opacity-50"
                      >
                        <XCircle className="h-3.5 w-3.5" />
                        <span>Reject</span>
                      </button>
                    </div>
                  </div>
                )}

                {selectedExecution.status === "EXECUTING" && (
                  <div className="space-y-2">
                    <div className="flex items-center space-x-2 text-indigo-400 text-xs">
                      <RotateCw className="h-4 w-4 animate-spin" />
                      <span>Query running on target database with timeout guard...</span>
                    </div>
                    <button
                      onClick={handleAbort}
                      disabled={actionLoading}
                      className="w-full flex items-center justify-center space-x-1.5 bg-red-600 hover:bg-red-500 text-white px-3 py-2 rounded-lg text-xs font-semibold shadow-md shadow-red-600/30 transition-colors disabled:opacity-50"
                    >
                      <StopCircle className="h-3.5 w-3.5" />
                      <span>Stop & KILL Session Now</span>
                    </button>
                  </div>
                )}

                {selectedExecution.status === "COMPLETED" && (
                  <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 space-y-2">
                    <div className="flex items-center space-x-1.5 text-emerald-400 text-xs font-bold">
                      <CheckCircle2 className="h-4 w-4" />
                      <span>Execution Successful</span>
                    </div>
                    <div className="font-mono text-[11px] bg-slate-950 p-2 rounded text-slate-300 max-h-36 overflow-y-auto">
                      <pre className="whitespace-pre-wrap">
                        {selectedExecution.result_summary
                          ? JSON.stringify(selectedExecution.result_summary, null, 2)
                          : "No result payload"}
                      </pre>
                    </div>
                  </div>
                )}

                {(selectedExecution.status === "REJECTED" ||
                  selectedExecution.status === "TIMEOUT" ||
                  selectedExecution.status === "ABORTED") && (
                  <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-xs text-red-300 space-y-1">
                    <div className="font-bold flex items-center space-x-1 text-red-400">
                      <AlertTriangle className="h-3.5 w-3.5" />
                      <span>Execution Terminated</span>
                    </div>
                    <p className="text-[11px] leading-relaxed">
                      {selectedExecution.error_message || "No error details reported."}
                    </p>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
