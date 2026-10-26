"use client";

import React, { useState, useMemo } from "react";
import { Activity } from "lucide-react";
import { ExecutionResponse, PluginProfileResponse } from "@/types";
import { SessionFilterBar, SessionFilter } from "./SessionFilterBar";
import { SessionCardsList } from "./SessionCardsList";
import { QuerySimulatorPane } from "./QuerySimulatorPane";
import { DryRunExplainPane } from "./DryRunExplainPane";
import { GatekeeperControlsPane } from "./GatekeeperControlsPane";

export interface LiveExecutionMonitorProps {
  executions: ExecutionResponse[];
  selectedExecution: ExecutionResponse | null;
  onSelectExecution: (exec: ExecutionResponse) => void;
  onSubmitQuery: (
    targetId: string,
    query: string,
    reasoning: string
  ) => Promise<void | ExecutionResponse>;
  onApprove: (id: string) => Promise<void>;
  onReject: (id: string) => Promise<void>;
  onAbort: (id: string) => Promise<void>;
  plugins: PluginProfileResponse[];
  isSubmitting?: boolean;
}

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
  const [sessionFilter, setSessionFilter] = useState<SessionFilter>("ALL");

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
        (ex) => ex.status === "REJECTED" || ex.status === "TIMEOUT" || ex.status === "ABORTED"
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
  }, [
    sessionFilter,
    executions,
    pendingSessions,
    runningSessions,
    blockedSessions,
    completedSessions,
  ]);

  return (
    <div className="space-y-6">
      {/* Live Operational Session Hub */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 space-y-3.5 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-200 dark:border-slate-800">
          <div className="flex items-center space-x-2.5">
            <div className="p-1.5 rounded-lg bg-indigo-50 dark:bg-indigo-500/10 border border-indigo-200 dark:border-indigo-500/20 text-indigo-600 dark:text-indigo-400">
              <Activity className="h-4 w-4" />
            </div>
            <div>
              <h2 className="text-xs font-bold uppercase tracking-wider text-slate-900 dark:text-slate-100 flex items-center space-x-2">
                <span>Live Operational Sessions</span>
                <span className="text-[10px] font-normal text-slate-400 font-mono">
                  ({executions.length} total)
                </span>
              </h2>
              <p className="text-[11px] text-slate-500 dark:text-slate-400">
                Real-time operational cockpit for monitoring and intercepting active query sessions
              </p>
            </div>
          </div>

          <SessionFilterBar
            sessionFilter={sessionFilter}
            onFilterChange={setSessionFilter}
            totalCount={executions.length}
            pendingCount={pendingSessions.length}
            runningCount={runningSessions.length}
            blockedCount={blockedSessions.length}
            completedCount={completedSessions.length}
          />
        </div>

        <SessionCardsList
          executions={filteredExecutions}
          selectedExecution={selectedExecution}
          onSelectExecution={onSelectExecution}
          sessionFilter={sessionFilter}
        />
      </div>

      {/* 3-Column Balanced Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
        <QuerySimulatorPane
          plugins={plugins}
          onSubmitQuery={onSubmitQuery}
          isSubmitting={isSubmitting}
          selectedExecutionId={selectedExecution?.id}
        />
        <DryRunExplainPane selectedExecution={selectedExecution} />
        <GatekeeperControlsPane
          selectedExecution={selectedExecution}
          onApprove={onApprove}
          onReject={onReject}
          onAbort={onAbort}
        />
      </div>
    </div>
  );
};
