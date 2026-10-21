"use client";

import React, { useState } from "react";
import {
  FileText,
  Search,
  CheckCircle2,
  Clock,
  XCircle,
  AlertTriangle,
  StopCircle,
  RotateCw,
  ExternalLink,
} from "lucide-react";
import { ExecutionResponse } from "@/types";
import { cn } from "@/lib/utils";

interface AuditLogsProps {
  logs: ExecutionResponse[];
}

export const AuditLogs: React.FC<AuditLogsProps> = ({ logs }) => {
  const [searchTerm, setSearchTerm] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [selectedLog, setSelectedLog] = useState<ExecutionResponse | null>(null);

  const filteredLogs = logs.filter((log) => {
    const matchesSearch =
      log.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      log.query.toLowerCase().includes(searchTerm.toLowerCase()) ||
      log.target_id.toLowerCase().includes(searchTerm.toLowerCase());

    const matchesStatus = statusFilter === "ALL" || log.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "COMPLETED":
        return (
          <span className="inline-flex items-center text-[10px] font-semibold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
            <CheckCircle2 className="h-3 w-3 mr-1" /> COMPLETED
          </span>
        );
      case "PAUSED_FOR_REVIEW":
        return (
          <span className="inline-flex items-center text-[10px] font-semibold text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">
            <Clock className="h-3 w-3 mr-1" /> PAUSED
          </span>
        );
      case "EXECUTING":
        return (
          <span className="inline-flex items-center text-[10px] font-semibold text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded border border-indigo-500/20 animate-pulse">
            <RotateCw className="h-3 w-3 mr-1 animate-spin" /> EXECUTING
          </span>
        );
      case "REJECTED":
        return (
          <span className="inline-flex items-center text-[10px] font-semibold text-red-400 bg-red-500/10 px-2 py-0.5 rounded border border-red-500/20">
            <XCircle className="h-3 w-3 mr-1" /> REJECTED
          </span>
        );
      case "TIMEOUT":
        return (
          <span className="inline-flex items-center text-[10px] font-semibold text-red-400 bg-red-500/10 px-2 py-0.5 rounded border border-red-500/20">
            <AlertTriangle className="h-3 w-3 mr-1" /> TIMEOUT
          </span>
        );
      case "ABORTED":
        return (
          <span className="inline-flex items-center text-[10px] font-semibold text-slate-400 bg-slate-800 px-2 py-0.5 rounded border border-slate-700">
            <StopCircle className="h-3 w-3 mr-1" /> ABORTED
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center text-[10px] font-semibold text-slate-300 bg-slate-800 px-2 py-0.5 rounded">
            {status}
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Search & Filter Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h2 className="text-sm font-bold tracking-tight text-slate-100 flex items-center space-x-2">
            <FileText className="h-4 w-4 text-indigo-400" />
            <span>Audit & Compliance Logs</span>
          </h2>
          <p className="text-xs text-slate-400">
            Comprehensive historical ledger of all AI queries, dry-run analyses, decisions, and durations.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          {/* Search Input */}
          <div className="relative">
            <Search className="h-3.5 w-3.5 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search by ID or query..."
              className="bg-slate-900 border border-slate-800 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-indigo-500 w-56 font-mono"
            />
          </div>

          {/* Status Filter */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-slate-900 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-indigo-500"
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

      {/* Logs Table */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950/80 border-b border-slate-800 text-[10px] font-bold uppercase tracking-wider text-slate-400">
              <tr>
                <th className="py-3 px-4">Session ID</th>
                <th className="py-3 px-4">Target Plugin</th>
                <th className="py-3 px-4">Query Type</th>
                <th className="py-3 px-4">Statement Snippet</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4">Duration</th>
                <th className="py-3 px-4">Timestamp</th>
                <th className="py-3 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/80">
              {filteredLogs.length === 0 ? (
                <tr>
                  <td colSpan={8} className="py-12 text-center text-slate-500 italic">
                    No matching execution logs found.
                  </td>
                </tr>
              ) : (
                filteredLogs.map((log) => (
                  <tr
                    key={log.id}
                    className="hover:bg-slate-800/40 transition-colors cursor-pointer"
                    onClick={() => setSelectedLog(log)}
                  >
                    <td className="py-3 px-4 font-mono font-bold text-indigo-400">
                      #{log.id}
                    </td>
                    <td className="py-3 px-4 font-medium text-slate-300">
                      {log.target_id}
                    </td>
                    <td className="py-3 px-4">
                      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-950 text-slate-400 border border-slate-800">
                        {log.query_type}
                      </span>
                    </td>
                    <td className="py-3 px-4 font-mono text-slate-400 max-w-xs truncate">
                      {log.query.replace(/\s+/g, " ")}
                    </td>
                    <td className="py-3 px-4">{getStatusBadge(log.status)}</td>
                    <td className="py-3 px-4 font-mono text-slate-300">
                      {log.execution_time_ms !== null ? `${log.execution_time_ms}ms` : "-"}
                    </td>
                    <td className="py-3 px-4 text-slate-500 font-mono text-[11px]">
                      {new Date(log.created_at).toLocaleTimeString()}
                    </td>
                    <td className="py-3 px-4 text-right">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedLog(log);
                        }}
                        className="text-indigo-400 hover:text-indigo-300 font-semibold text-[11px] inline-flex items-center space-x-1"
                      >
                        <span>Inspect</span>
                        <ExternalLink className="h-3 w-3" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Log Detail Drawer Modal */}
      {selectedLog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-2xl w-full p-6 shadow-2xl space-y-4 max-h-[85vh] overflow-y-auto">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center space-x-2">
                <FileText className="h-4 w-4 text-indigo-400" />
                <h3 className="text-sm font-bold text-slate-100">
                  Execution Audit Detail: #{selectedLog.id}
                </h3>
              </div>
              <button
                onClick={() => setSelectedLog(null)}
                className="text-slate-400 hover:text-slate-200 text-xs"
              >
                Close
              </button>
            </div>

            <div className="space-y-4 text-xs">
              {/* Meta Grid */}
              <div className="grid grid-cols-2 gap-3 bg-slate-950 p-3 rounded-lg border border-slate-800">
                <div>
                  <span className="text-slate-500 block text-[10px] uppercase font-semibold">
                    Target Plugin
                  </span>
                  <span className="font-mono text-slate-200">{selectedLog.target_id}</span>
                </div>
                <div>
                  <span className="text-slate-500 block text-[10px] uppercase font-semibold">
                    Final Status
                  </span>
                  <div>{getStatusBadge(selectedLog.status)}</div>
                </div>
                <div>
                  <span className="text-slate-500 block text-[10px] uppercase font-semibold">
                    Duration
                  </span>
                  <span className="font-mono text-indigo-400 font-bold">
                    {selectedLog.execution_time_ms ? `${selectedLog.execution_time_ms} ms` : "N/A"}
                  </span>
                </div>
                <div>
                  <span className="text-slate-500 block text-[10px] uppercase font-semibold">
                    Database SPID
                  </span>
                  <span className="font-mono text-slate-200">{selectedLog.spid || "None"}</span>
                </div>
              </div>

              {/* Full Query */}
              <div className="space-y-1">
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                  Full Statement
                </span>
                <div className="bg-slate-950 border border-slate-800 rounded p-3 font-mono text-[11px] text-slate-200 max-h-40 overflow-y-auto whitespace-pre-wrap">
                  {selectedLog.query}
                </div>
              </div>

              {/* AI Reasoning */}
              {selectedLog.reasoning && (
                <div className="space-y-1">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                    AI Intent & Reasoning
                  </span>
                  <p className="p-2.5 rounded bg-slate-950 border border-slate-800 text-slate-300 text-[11px]">
                    {selectedLog.reasoning}
                  </p>
                </div>
              )}

              {/* Explain Plan */}
              {selectedLog.explain_plan && (
                <div className="space-y-1">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                    Explain Plan Data
                  </span>
                  <div className="bg-slate-950 border border-slate-800 rounded p-3 font-mono text-[11px] text-slate-300 max-h-44 overflow-y-auto">
                    <pre className="whitespace-pre-wrap">
                      {JSON.stringify(selectedLog.explain_plan, null, 2)}
                    </pre>
                  </div>
                </div>
              )}

              {/* Result Summary */}
              {selectedLog.result_summary && (
                <div className="space-y-1">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                    Returned Data Summary
                  </span>
                  <div className="bg-slate-950 border border-slate-800 rounded p-3 font-mono text-[11px] text-slate-300 max-h-44 overflow-y-auto">
                    <pre className="whitespace-pre-wrap">
                      {JSON.stringify(selectedLog.result_summary, null, 2)}
                    </pre>
                  </div>
                </div>
              )}

              {/* Error Message */}
              {selectedLog.error_message && (
                <div className="p-3 rounded bg-red-500/10 border border-red-500/20 text-red-400 space-y-1">
                  <span className="font-bold block text-[11px]">Termination Error</span>
                  <p className="font-mono text-[11px]">{selectedLog.error_message}</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

