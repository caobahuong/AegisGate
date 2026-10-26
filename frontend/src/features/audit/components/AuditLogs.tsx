"use client";

import React from "react";
import { FileText, Search } from "lucide-react";
import { ExecutionResponse, PluginProfileResponse } from "@/types";
import { useAuditLogs } from "../hooks/useAuditLogs";
import { AuditLogsTable } from "./AuditLogsTable";
import { AuditDetailDrawer } from "./AuditDetailDrawer";

export interface AuditLogsProps {
  logs?: ExecutionResponse[];
  executions?: ExecutionResponse[];
  plugins?: PluginProfileResponse[];
}

export const AuditLogs: React.FC<AuditLogsProps> = (props) => {
  const {
    searchTerm,
    setSearchTerm,
    statusFilter,
    setStatusFilter,
    selectedLog,
    setSelectedLog,
    visibleLogs,
    hasMore,
    loadMore,
    totalCount,
    getPluginName,
    copyToClipboard,
  } = useAuditLogs(props);

  return (
    <div className="space-y-6">
      {/* Search & Filter Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
        <div>
          <h2 className="text-sm font-bold tracking-tight text-slate-900 dark:text-slate-100 flex items-center space-x-2">
            <FileText className="h-4 w-4 text-indigo-500 dark:text-indigo-400" />
            <span>Audit &amp; Compliance Logs</span>
          </h2>
          <p className="text-xs text-slate-600 dark:text-slate-400">
            Comprehensive ledger tracking detailed Input parameters, AI intent, governance checks, and concrete Output datasets.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          {/* Search Input */}
          <div className="relative">
            <Search className="h-3.5 w-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search by ID or query..."
              className="bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-800 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-900 dark:text-slate-200 focus:outline-none focus:border-indigo-500 w-56 font-mono"
            />
          </div>

          {/* Status Filter */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-900 dark:text-slate-300 focus:outline-none focus:border-indigo-500"
          >
            <option value="ALL">All Statuses</option>
            <option value="COMPLETED">COMPLETED</option>
            <option value="PAUSED_FOR_REVIEW">PAUSED</option>
            <option value="EXECUTING">EXECUTING</option>
            <option value="REJECTED">REJECTED</option>
            <option value="TIMEOUT">TIMEOUT</option>
            <option value="ABORTED">ABORTED</option>
          </select>
        </div>
      </div>

      {/* Logs Table with Explicit Input & Output Columns */}
      <AuditLogsTable
        logs={visibleLogs}
        totalCount={totalCount}
        hasMore={hasMore}
        onLoadMore={loadMore}
        getPluginName={getPluginName}
        onSelectLog={setSelectedLog}
      />

      {/* Comprehensive Log Detail Drawer / Modal */}
      <AuditDetailDrawer
        isOpen={Boolean(selectedLog)}
        onClose={() => setSelectedLog(null)}
        log={selectedLog}
        pluginName={selectedLog ? getPluginName(selectedLog.target_id) : ""}
        onCopy={copyToClipboard}
      />
    </div>
  );
};
