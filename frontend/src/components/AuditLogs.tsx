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
  Database,
  Copy,
  Check,
  Table as TableIcon,
  Code2,
  Sparkles,
  ShieldAlert,
  Layers,
} from "lucide-react";
import { ExecutionResponse, PluginProfileResponse } from "@/types";
import { cn } from "@/lib/utils";

interface AuditLogsProps {
  logs?: ExecutionResponse[];
  executions?: ExecutionResponse[];
  plugins?: PluginProfileResponse[];
}

interface ExtractedResult {
  dataRows: Record<string, unknown>[] | null;
  rowsAffected: number | null;
  columns: string[];
  raw: unknown;
}

const parseResultSummary = (summary: Record<string, unknown> | string | null): ExtractedResult => {
  if (!summary) return { dataRows: null, rowsAffected: null, columns: [], raw: null };
  let parsed: unknown = summary;
  if (typeof summary === "string") {
    try {
      parsed = JSON.parse(summary);
    } catch {
      return { dataRows: null, rowsAffected: null, columns: [], raw: summary };
    }
  }
  if (!parsed || typeof parsed !== "object") {
    return { dataRows: null, rowsAffected: null, columns: [], raw: parsed };
  }

  const pObj = parsed as Record<string, unknown>;
  const data = Array.isArray(pObj.data)
    ? (pObj.data as Record<string, unknown>[])
    : Array.isArray(parsed)
    ? (parsed as Record<string, unknown>[])
    : null;

  const rows = typeof pObj.rows_affected === "number" ? pObj.rows_affected : data?.length ?? null;
  const cols = data && data.length > 0 && typeof data[0] === "object" ? Object.keys(data[0]) : [];

  return {
    dataRows: data,
    rowsAffected: rows,
    columns: cols,
    raw: parsed,
  };
};

export const AuditLogs: React.FC<AuditLogsProps> = ({ logs, executions, plugins = [] }) => {
  const logList = logs || executions || [];
  const [searchTerm, setSearchTerm] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [selectedLog, setSelectedLog] = useState<ExecutionResponse | null>(null);
  const [modalTab, setModalTab] = useState<"output" | "input" | "governance">("output");
  const [outputViewMode, setOutputViewMode] = useState<"table" | "json">("table");
  const [copiedQuery, setCopiedQuery] = useState<boolean>(false);
  const [copiedResult, setCopiedResult] = useState<boolean>(false);

  const filteredLogs = logList.filter((log) => {
    const matchesSearch =
      log.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      log.query.toLowerCase().includes(searchTerm.toLowerCase()) ||
      log.target_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (log.reasoning && log.reasoning.toLowerCase().includes(searchTerm.toLowerCase()));

    const matchesStatus = statusFilter === "ALL" || log.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const getPluginName = (targetId: string): string => {
    const found = plugins.find((p) => p.id === targetId);
    return found ? found.name : targetId;
  };

  const handleCopy = (text: string, type: "query" | "result") => {
    if (typeof navigator !== "undefined" && navigator.clipboard) {
      navigator.clipboard.writeText(text);
    } else {
      const textarea = document.createElement("textarea");
      textarea.value = text;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      document.body.removeChild(textarea);
    }
    if (type === "query") {
      setCopiedQuery(true);
      setTimeout(() => setCopiedQuery(false), 2000);
    } else {
      setCopiedResult(true);
      setTimeout(() => setCopiedResult(false), 2000);
    }
  };

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

  const renderOutputSummary = (log: ExecutionResponse) => {
    if (log.status === "COMPLETED") {
      const res = parseResultSummary(log.result_summary);
      if (res.dataRows && res.dataRows.length > 0) {
        return (
          <span className="inline-flex items-center text-[10px] font-semibold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
            <Database className="h-2.5 w-2.5 mr-1 text-emerald-400 flex-shrink-0" />
            <span>{res.dataRows.length} rows returned</span>
          </span>
        );
      }
      if (res.rowsAffected !== null) {
        return (
          <span className="inline-flex items-center text-[10px] font-semibold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
            <CheckCircle2 className="h-2.5 w-2.5 mr-1 text-emerald-400 flex-shrink-0" />
            <span>{res.rowsAffected} rows affected</span>
          </span>
        );
      }
      return (
        <span className="inline-flex items-center text-[10px] text-emerald-400">
          Success (0 rows)
        </span>
      );
    }
    if (log.status === "REJECTED") {
      return (
        <span className="inline-flex items-center text-[10px] font-semibold text-red-400 bg-red-500/10 px-2 py-0.5 rounded border border-red-500/20">
          <ShieldAlert className="h-2.5 w-2.5 mr-1 text-red-400 flex-shrink-0" />
          <span>Rule Blocked</span>
        </span>
      );
    }
    if (log.status === "PAUSED_FOR_REVIEW") {
      return (
        <span className="inline-flex items-center text-[10px] font-semibold text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">
          <Clock className="h-2.5 w-2.5 mr-1 text-amber-400 flex-shrink-0" />
          <span>Awaiting Review</span>
        </span>
      );
    }
    if (log.status === "TIMEOUT" || log.status === "ABORTED") {
      return (
        <span className="inline-flex items-center text-[10px] font-semibold text-red-400 bg-red-500/10 px-2 py-0.5 rounded border border-red-500/20">
          <AlertTriangle className="h-2.5 w-2.5 mr-1 text-red-400 flex-shrink-0" />
          <span>{log.status === "TIMEOUT" ? "Timeout Exceeded" : "Aborted"}</span>
        </span>
      );
    }
    return <span className="text-[10px] text-slate-500 font-mono">Pending...</span>;
  };

  const selectedResult = selectedLog ? parseResultSummary(selectedLog.result_summary) : null;

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
            Comprehensive ledger tracking detailed Input parameters, AI intent, governance checks, and concrete Output datasets.
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

      {/* Logs Table with Explicit Input & Output Columns */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-950/80 border-b border-slate-800 text-[10px] font-bold uppercase tracking-wider text-slate-400">
              <tr>
                <th className="py-3 px-4">Session ID</th>
                <th className="py-3 px-4">Target Plugin</th>
                <th className="py-3 px-4">Input (Statement & Intent)</th>
                <th className="py-3 px-4">Output (Result)</th>
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
                    onClick={() => {
                      setSelectedLog(log);
                      setModalTab("output");
                    }}
                  >
                    <td className="py-3 px-4 font-mono font-bold text-indigo-400 whitespace-nowrap">
                      #{log.id}
                    </td>
                    <td className="py-3 px-4 font-medium text-slate-300 whitespace-nowrap">
                      <div className="flex items-center space-x-1.5">
                        <Database className="h-3 w-3 text-indigo-400 flex-shrink-0" />
                        <span className="truncate max-w-[120px]">{getPluginName(log.target_id)}</span>
                      </div>
                    </td>
                    <td className="py-3 px-4 max-w-sm">
                      <div className="space-y-1">
                        <div className="flex items-center space-x-2">
                          <span className={cn(
                            "text-[9px] font-mono px-1.5 py-0.2 rounded font-bold",
                            log.query_type === "WRITE" ? "bg-amber-500/20 text-amber-300 border border-amber-500/30" : "bg-slate-950 text-slate-400 border border-slate-800"
                          )}>
                            {log.query_type}
                          </span>
                          <span className="font-mono text-slate-300 truncate text-[11px] block max-w-xs">
                            {log.query.replace(/\s+/g, " ")}
                          </span>
                        </div>
                        {log.reasoning && (
                          <div className="flex items-center space-x-1 text-[10px] text-slate-500 truncate max-w-xs">
                            <Sparkles className="h-2.5 w-2.5 text-indigo-400 flex-shrink-0" />
                            <span className="truncate">{log.reasoning}</span>
                          </div>
                        )}
                      </div>
                    </td>
                    <td className="py-3 px-4 whitespace-nowrap">
                      {renderOutputSummary(log)}
                    </td>
                    <td className="py-3 px-4 whitespace-nowrap">{getStatusBadge(log.status)}</td>
                    <td className="py-3 px-4 font-mono text-slate-300 whitespace-nowrap">
                      {log.execution_time_ms !== null ? `${log.execution_time_ms} ms` : "-"}
                    </td>
                    <td className="py-3 px-4 text-slate-500 font-mono text-[11px] whitespace-nowrap">
                      {new Date(log.created_at).toLocaleTimeString()}
                    </td>
                    <td className="py-3 px-4 text-right whitespace-nowrap">
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setSelectedLog(log);
                          setModalTab("output");
                        }}
                        className="text-indigo-400 hover:text-indigo-300 font-semibold text-[11px] inline-flex items-center space-x-1 bg-indigo-500/10 hover:bg-indigo-500/20 px-2 py-1 rounded border border-indigo-500/20 transition-colors"
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

      {/* Comprehensive Log Detail Drawer / Modal */}
      {selectedLog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 animate-in fade-in duration-150">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-3xl w-full p-6 shadow-2xl space-y-5 max-h-[90vh] overflow-y-auto">
            
            {/* Modal Header */}
            <div className="flex items-center justify-between pb-4 border-b border-slate-800">
              <div className="flex items-center space-x-3">
                <div className="h-9 w-9 rounded-xl bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center">
                  <FileText className="h-5 w-5 text-indigo-400" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-100 flex items-center space-x-2">
                    <span>Execution Audit Detail: #{selectedLog.id}</span>
                  </h3>
                  <div className="flex items-center space-x-2 text-xs text-slate-400 pt-0.5">
                    <span className="font-mono text-indigo-300">{getPluginName(selectedLog.target_id)}</span>
                    <span>•</span>
                    <span>{new Date(selectedLog.created_at).toLocaleString()}</span>
                  </div>
                </div>
              </div>
              <div className="flex items-center space-x-2">
                {getStatusBadge(selectedLog.status)}
                <button
                  onClick={() => setSelectedLog(null)}
                  className="text-slate-400 hover:text-slate-200 text-xs px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 transition-colors"
                >
                  Close
                </button>
              </div>
            </div>

            {/* Quick KPI Overview Bar */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-slate-950 p-3.5 rounded-xl border border-slate-800 text-xs">
              <div>
                <span className="text-slate-500 block text-[10px] uppercase font-semibold">
                  Query Type
                </span>
                <span className="font-mono text-slate-200 font-bold">{selectedLog.query_type}</span>
              </div>
              <div>
                <span className="text-slate-500 block text-[10px] uppercase font-semibold">
                  Execution Latency
                </span>
                <span className="font-mono text-emerald-400 font-bold">
                  {selectedLog.execution_time_ms !== null ? `${selectedLog.execution_time_ms} ms` : "N/A"}
                </span>
              </div>
              <div>
                <span className="text-slate-500 block text-[10px] uppercase font-semibold">
                  Result Records
                </span>
                <span className="font-mono text-indigo-400 font-bold">
                  {selectedResult?.dataRows
                    ? `${selectedResult.dataRows.length} rows`
                    : selectedResult && selectedResult.rowsAffected !== null
                    ? `${selectedResult.rowsAffected} affected`
                    : "0 rows"}
                </span>
              </div>
              <div>
                <span className="text-slate-500 block text-[10px] uppercase font-semibold">
                  Database SPID
                </span>
                <span className="font-mono text-slate-200">{selectedLog.spid || "Session clean"}</span>
              </div>
            </div>

            {/* Sub-tab Navigation: Output vs Input vs Governance */}
            <div className="flex items-center space-x-2 border-b border-slate-800 pb-2">
              <button
                onClick={() => setModalTab("output")}
                className={cn(
                  "flex items-center space-x-1.5 text-xs font-semibold px-3 py-1.5 rounded-lg transition-colors",
                  modalTab === "output"
                    ? "bg-indigo-600/20 text-indigo-300 border border-indigo-500/30"
                    : "text-slate-400 hover:text-slate-200"
                )}
              >
                <Database className="h-3.5 w-3.5" />
                <span>Execution Output & Results</span>
              </button>
              <button
                onClick={() => setModalTab("input")}
                className={cn(
                  "flex items-center space-x-1.5 text-xs font-semibold px-3 py-1.5 rounded-lg transition-colors",
                  modalTab === "input"
                    ? "bg-indigo-600/20 text-indigo-300 border border-indigo-500/30"
                    : "text-slate-400 hover:text-slate-200"
                )}
              >
                <Code2 className="h-3.5 w-3.5" />
                <span>Input Statement & Intent</span>
              </button>
              <button
                onClick={() => setModalTab("governance")}
                className={cn(
                  "flex items-center space-x-1.5 text-xs font-semibold px-3 py-1.5 rounded-lg transition-colors",
                  modalTab === "governance"
                    ? "bg-indigo-600/20 text-indigo-300 border border-indigo-500/30"
                    : "text-slate-400 hover:text-slate-200"
                )}
              >
                <Layers className="h-3.5 w-3.5" />
                <span>Dry-Run & Governance Plan</span>
              </button>
            </div>

            {/* ========================================================
                SECTION 1: OUTPUT & RETURNED RESULT DATA
               ======================================================== */}
            {modalTab === "output" && (
              <div className="space-y-4">
                {/* Result header with view switcher */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <span className="text-xs font-bold text-slate-200">
                      Returned Dataset & Execution Payload
                    </span>
                    {selectedResult?.dataRows && (
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                        {selectedResult.dataRows.length} row{selectedResult.dataRows.length === 1 ? "" : "s"}
                      </span>
                    )}
                  </div>

                  <div className="flex items-center space-x-2">
                    <div className="flex items-center bg-slate-950 border border-slate-800 rounded-lg p-0.5">
                      <button
                        onClick={() => setOutputViewMode("table")}
                        className={cn(
                          "flex items-center space-x-1 text-[11px] px-2.5 py-1 rounded-md transition-colors",
                          outputViewMode === "table"
                            ? "bg-indigo-600 text-white font-semibold shadow-sm"
                            : "text-slate-400 hover:text-slate-200"
                        )}
                      >
                        <TableIcon className="h-3 w-3" />
                        <span>Table View</span>
                      </button>
                      <button
                        onClick={() => setOutputViewMode("json")}
                        className={cn(
                          "flex items-center space-x-1 text-[11px] px-2.5 py-1 rounded-md transition-colors",
                          outputViewMode === "json"
                            ? "bg-indigo-600 text-white font-semibold shadow-sm"
                            : "text-slate-400 hover:text-slate-200"
                        )}
                      >
                        <Code2 className="h-3 w-3" />
                        <span>Raw JSON</span>
                      </button>
                    </div>

                    {selectedLog.result_summary && (
                      <button
                        onClick={() => handleCopy(JSON.stringify(selectedLog.result_summary, null, 2), "result")}
                        className="flex items-center space-x-1 bg-slate-800 hover:bg-slate-700 text-slate-200 px-2.5 py-1 rounded-lg text-[11px] border border-slate-700 transition-colors"
                      >
                        {copiedResult ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
                        <span>{copiedResult ? "Copied!" : "Copy Output"}</span>
                      </button>
                    )}
                  </div>
                </div>

                {/* Termination Error Banner */}
                {selectedLog.error_message && (
                  <div className="p-3.5 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 space-y-1.5">
                    <div className="flex items-center space-x-2 text-xs font-bold">
                      <ShieldAlert className="h-4 w-4 text-red-400 flex-shrink-0" />
                      <span>Execution Rejection / Error Output</span>
                    </div>
                    <p className="font-mono text-xs text-red-300 leading-relaxed pl-6">
                      {selectedLog.error_message}
                    </p>
                  </div>
                )}

                {/* Table View of Returned Dataset */}
                {outputViewMode === "table" && (
                  <div className="bg-slate-950 border border-slate-800 rounded-xl overflow-hidden shadow-inner">
                    {selectedResult?.dataRows && selectedResult.dataRows.length > 0 ? (
                      <div className="overflow-x-auto max-h-72">
                        <table className="w-full text-left text-xs border-collapse">
                          <thead className="bg-slate-900 border-b border-slate-800 text-[10px] font-bold uppercase tracking-wider text-slate-400 sticky top-0 z-10">
                            <tr>
                              <th className="py-2.5 px-3 text-slate-500 font-mono w-10">#</th>
                              {selectedResult.columns.map((col) => (
                                <th key={col} className="py-2.5 px-3 font-mono font-bold text-slate-200 whitespace-nowrap">
                                  {col}
                                </th>
                              ))}
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-800/60 font-mono text-[11px]">
                            {selectedResult.dataRows.map((row, idx) => (
                              <tr key={idx} className="hover:bg-slate-900/40 transition-colors">
                                <td className="py-2.5 px-3 text-slate-500">{idx + 1}</td>
                                {selectedResult.columns.map((col) => (
                                  <td key={col} className="py-2.5 px-3 text-slate-300 whitespace-nowrap">
                                    {row[col] !== null && row[col] !== undefined ? String(row[col]) : <span className="text-slate-600 italic">null</span>}
                                  </td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ) : selectedLog.status === "COMPLETED" ? (
                      <div className="p-8 text-center text-slate-400 space-y-1">
                        <CheckCircle2 className="h-6 w-6 text-emerald-400 mx-auto" />
                        <p className="text-xs font-medium">Query executed successfully with no data rows returned.</p>
                        <p className="text-[11px] text-slate-500">
                          {selectedResult && selectedResult.rowsAffected !== null
                            ? `Affected ${selectedResult.rowsAffected} row(s) in target database.`
                            : "Command acknowledged by driver."}
                        </p>
                      </div>
                    ) : (
                      <div className="p-8 text-center text-slate-500 italic text-xs">
                        No output dataset available for this execution state ({selectedLog.status}).
                      </div>
                    )}
                  </div>
                )}

                {/* Raw JSON View */}
                {outputViewMode === "json" && (
                  <div className="bg-slate-950 border border-slate-800 rounded-xl p-3.5 font-mono text-xs text-slate-300 max-h-72 overflow-y-auto">
                    <pre className="whitespace-pre-wrap">
                      {selectedLog.result_summary
                        ? JSON.stringify(selectedLog.result_summary, null, 2)
                        : JSON.stringify({ message: "No result payload returned", status: selectedLog.status }, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            )}

            {/* ========================================================
                SECTION 2: INPUT STATEMENT & AI INTENT
               ======================================================== */}
            {modalTab === "input" && (
              <div className="space-y-4">
                {/* AI Intent & Reasoning Card */}
                <div className="p-3.5 rounded-xl bg-indigo-600/10 border border-indigo-500/20 space-y-1.5">
                  <div className="flex items-center space-x-2 text-xs font-bold text-indigo-400">
                    <Sparkles className="h-4 w-4 text-indigo-400" />
                    <span>AI Intent & Purpose Reasoning</span>
                  </div>
                  <p className="text-xs text-slate-200 leading-relaxed pl-6">
                    {selectedLog.reasoning || "Direct database execution requested without specific reasoning context."}
                  </p>
                </div>

                {/* SQL Statement with Copy */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center space-x-2">
                      <Code2 className="h-3.5 w-3.5 text-indigo-400" />
                      <span>Full SQL Statement / Command Input</span>
                    </span>
                    <button
                      onClick={() => handleCopy(selectedLog.query, "query")}
                      className="flex items-center space-x-1 bg-slate-800 hover:bg-slate-700 text-slate-200 px-2.5 py-1 rounded-lg text-[11px] border border-slate-700 transition-colors"
                    >
                      {copiedQuery ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
                      <span>{copiedQuery ? "Copied!" : "Copy SQL"}</span>
                    </button>
                  </div>

                  <div className="bg-slate-950 border border-slate-800 rounded-xl p-4 font-mono text-xs text-slate-200 max-h-56 overflow-y-auto whitespace-pre-wrap leading-relaxed shadow-inner">
                    {selectedLog.query}
                  </div>
                </div>

                {/* Input Details Grid */}
                <div className="grid grid-cols-2 gap-3 bg-slate-950 p-3 rounded-lg border border-slate-800 text-xs">
                  <div>
                    <span className="text-slate-500 block text-[10px] uppercase font-semibold">Target Identifier</span>
                    <span className="font-mono text-slate-200">{selectedLog.target_id}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block text-[10px] uppercase font-semibold">Approval Route</span>
                    <span className="font-mono text-slate-200">
                      {selectedLog.auto_approved ? "Auto Approval ON" : selectedLog.approved_by ? `Approved by ${selectedLog.approved_by}` : "Manual Approval Mode"}
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* ========================================================
                SECTION 3: DRY-RUN & GOVERNANCE PLAN
               ======================================================== */}
            {modalTab === "governance" && (
              <div className="space-y-4">
                {/* Violations Evaluation */}
                {selectedLog.violations && selectedLog.violations.length > 0 ? (
                  <div className="p-3.5 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 space-y-1.5">
                    <div className="flex items-center space-x-2 text-xs font-bold">
                      <ShieldAlert className="h-4 w-4 text-red-400" />
                      <span>Governance Rule Violations Detected ({selectedLog.violations.length})</span>
                    </div>
                    <ul className="list-disc list-inside text-xs space-y-1 pl-4 text-red-300">
                      {selectedLog.violations.map((v, i) => (
                        <li key={i}>{v}</li>
                      ))}
                    </ul>
                  </div>
                ) : (
                  <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center space-x-2 text-xs font-medium">
                    <CheckCircle2 className="h-4 w-4 flex-shrink-0" />
                    <span>Passed all active governance policies. No forbidden joins or full table scans.</span>
                  </div>
                )}

                {/* Dry-Run Explain Plan */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center space-x-2">
                      <Layers className="h-3.5 w-3.5 text-indigo-400" />
                      <span>Showplan & Optimizer Metadata</span>
                    </span>
                  </div>
                  <div className="bg-slate-950 border border-slate-800 rounded-xl p-3.5 font-mono text-xs text-slate-300 max-h-64 overflow-y-auto">
                    <pre className="whitespace-pre-wrap">
                      {selectedLog.explain_plan
                        ? JSON.stringify(selectedLog.explain_plan, null, 2)
                        : "No explain plan generated"}
                    </pre>
                  </div>
                </div>
              </div>
            )}

          </div>
        </div>
      )}
    </div>
  );
};
