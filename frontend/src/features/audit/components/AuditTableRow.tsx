"use client";

import React, { memo } from "react";
import {
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Database,
  ExternalLink,
  RotateCw,
  ShieldAlert,
  Sparkles,
  StopCircle,
  XCircle,
} from "lucide-react";
import { ExecutionResponse } from "@/types";
import { cn } from "@/lib/utils";
import { parseResultSummary } from "../lib/parseResult";

export interface AuditTableRowProps {
  log: ExecutionResponse;
  pluginName: string;
  onSelect: (log: ExecutionResponse) => void;
}

const renderOutputSummary = (log: ExecutionResponse) => {
  if (log.status === "COMPLETED") {
    const res = parseResultSummary(log.result_summary);
    if (res.dataRows && res.dataRows.length > 0) {
      return (
        <span className="inline-flex items-center text-[10px] font-semibold text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
          <Database className="h-2.5 w-2.5 mr-1 text-emerald-500 dark:text-emerald-400 flex-shrink-0" />
          <span>{res.dataRows.length} rows returned</span>
        </span>
      );
    }
    if (res.rowsAffected !== null) {
      return (
        <span className="inline-flex items-center text-[10px] font-semibold text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
          <CheckCircle2 className="h-2.5 w-2.5 mr-1 text-emerald-500 dark:text-emerald-400 flex-shrink-0" />
          <span>{res.rowsAffected} rows affected</span>
        </span>
      );
    }
    return (
      <span className="inline-flex items-center text-[10px] text-emerald-600 dark:text-emerald-400">
        Success (0 rows)
      </span>
    );
  }
  if (log.status === "FAILED") {
    return (
      <span className="inline-flex items-center text-[10px] font-semibold text-red-600 dark:text-red-400 bg-red-500/10 px-2 py-0.5 rounded border border-red-500/20">
        <AlertCircle className="h-2.5 w-2.5 mr-1 text-red-500 dark:text-red-400 flex-shrink-0" />
        <span>Execution Failed</span>
      </span>
    );
  }
  if (log.status === "QUEUED") {
    return (
      <span className="inline-flex items-center text-[10px] font-semibold text-indigo-600 dark:text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded border border-indigo-500/20">
        <Clock className="h-2.5 w-2.5 mr-1 text-indigo-500 dark:text-indigo-400 flex-shrink-0" />
        <span>Queued</span>
      </span>
    );
  }
  if (log.status === "REJECTED") {
    return (
      <span className="inline-flex items-center text-[10px] font-semibold text-red-600 dark:text-red-400 bg-red-500/10 px-2 py-0.5 rounded border border-red-500/20">
        <ShieldAlert className="h-2.5 w-2.5 mr-1 text-red-500 dark:text-red-400 flex-shrink-0" />
        <span>Rule Blocked</span>
      </span>
    );
  }
  if (log.status === "PAUSED_FOR_REVIEW") {
    return (
      <span className="inline-flex items-center text-[10px] font-semibold text-amber-600 dark:text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">
        <Clock className="h-2.5 w-2.5 mr-1 text-amber-500 dark:text-amber-400 flex-shrink-0" />
        <span>Awaiting Review</span>
      </span>
    );
  }
  if (log.status === "TIMEOUT" || log.status === "ABORTED") {
    return (
      <span className="inline-flex items-center text-[10px] font-semibold text-red-600 dark:text-red-400 bg-red-500/10 px-2 py-0.5 rounded border border-red-500/20">
        <AlertTriangle className="h-2.5 w-2.5 mr-1 text-red-500 dark:text-red-400 flex-shrink-0" />
        <span>{log.status === "TIMEOUT" ? "Timeout Exceeded" : "Aborted"}</span>
      </span>
    );
  }
  return <span className="text-[10px] text-slate-500 font-mono">Pending...</span>;
};

const getStatusBadge = (status: string) => {
  switch (status) {
    case "COMPLETED":
      return (
        <span className="inline-flex items-center text-[10px] font-semibold text-emerald-600 dark:text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
          <CheckCircle2 className="h-3 w-3 mr-1" /> COMPLETED
        </span>
      );
    case "PAUSED_FOR_REVIEW":
      return (
        <span className="inline-flex items-center text-[10px] font-semibold text-amber-600 dark:text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">
          <Clock className="h-3 w-3 mr-1" /> PAUSED
        </span>
      );
    case "QUEUED":
      return (
        <span className="inline-flex items-center text-[10px] font-semibold text-indigo-600 dark:text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded border border-indigo-500/20">
          <Clock className="h-3 w-3 mr-1" /> QUEUED
        </span>
      );
    case "EXECUTING":
      return (
        <span className="inline-flex items-center text-[10px] font-semibold text-indigo-600 dark:text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded border border-indigo-500/20 animate-pulse">
          <RotateCw className="h-3 w-3 mr-1 animate-spin" /> EXECUTING
        </span>
      );
    case "REJECTED":
      return (
        <span className="inline-flex items-center text-[10px] font-semibold text-red-600 dark:text-red-400 bg-red-500/10 px-2 py-0.5 rounded border border-red-500/20">
          <XCircle className="h-3 w-3 mr-1" /> REJECTED
        </span>
      );
    case "TIMEOUT":
      return (
        <span className="inline-flex items-center text-[10px] font-semibold text-red-600 dark:text-red-400 bg-red-500/10 px-2 py-0.5 rounded border border-red-500/20">
          <AlertTriangle className="h-3 w-3 mr-1" /> TIMEOUT
        </span>
      );
    case "ABORTED":
      return (
        <span className="inline-flex items-center text-[10px] font-semibold text-slate-600 dark:text-slate-400 bg-slate-100 dark:bg-slate-800 px-2 py-0.5 rounded border border-slate-300 dark:border-slate-700">
          <StopCircle className="h-3 w-3 mr-1" /> ABORTED
        </span>
      );
    case "FAILED":
      return (
        <span className="inline-flex items-center text-[10px] font-semibold text-red-600 dark:text-red-400 bg-red-500/10 px-2 py-0.5 rounded border border-red-500/20">
          <AlertCircle className="h-3 w-3 mr-1" /> FAILED
        </span>
      );
    default:
      return (
        <span className="inline-flex items-center text-[10px] font-semibold text-slate-700 dark:text-slate-300 bg-slate-100 dark:bg-slate-800 px-2 py-0.5 rounded">
          {status}
        </span>
      );
  }
};

export const AuditTableRow = memo<AuditTableRowProps>(({ log, pluginName, onSelect }) => {
  return (
    <tr
      className="hover:bg-slate-50 dark:hover:bg-slate-800/40 transition-colors cursor-pointer"
      onClick={() => onSelect(log)}
    >
      <td className="py-3 px-4 font-mono font-bold text-indigo-600 dark:text-indigo-400 whitespace-nowrap">
        #{log.id}
      </td>
      <td className="py-3 px-4 font-medium text-slate-700 dark:text-slate-300 whitespace-nowrap">
        <div className="flex items-center space-x-1.5">
          <Database className="h-3 w-3 text-indigo-500 dark:text-indigo-400 flex-shrink-0" />
          <span className="truncate max-w-[120px]">{pluginName}</span>
        </div>
      </td>
      <td className="py-3 px-4 max-w-sm">
        <div className="space-y-1">
          <div className="flex items-center space-x-2">
            <span
              className={cn(
                "text-[9px] font-mono px-1.5 py-0.2 rounded font-bold",
                log.query_type === "WRITE"
                  ? "bg-amber-500/20 text-amber-600 dark:text-amber-300 border border-amber-500/30"
                  : "bg-slate-100 dark:bg-slate-950 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-800"
              )}
            >
              {log.query_type}
            </span>
            <span className="font-mono text-slate-800 dark:text-slate-300 truncate text-[11px] block max-w-xs">
              {log.query.replace(/\s+/g, " ")}
            </span>
          </div>
          {log.reasoning && (
            <div className="flex items-center space-x-1 text-[10px] text-slate-500 truncate max-w-xs">
              <Sparkles className="h-2.5 w-2.5 text-indigo-500 dark:text-indigo-400 flex-shrink-0" />
              <span className="truncate">{log.reasoning}</span>
            </div>
          )}
        </div>
      </td>
      <td className="py-3 px-4 whitespace-nowrap">{renderOutputSummary(log)}</td>
      <td className="py-3 px-4 whitespace-nowrap">{getStatusBadge(log.status)}</td>
      <td className="py-3 px-4 font-mono text-slate-700 dark:text-slate-300 whitespace-nowrap">
        {log.execution_time_ms !== null ? `${log.execution_time_ms} ms` : "-"}
      </td>
      <td className="py-3 px-4 text-slate-500 font-mono text-[11px] whitespace-nowrap">
        {new Date(log.created_at).toLocaleTimeString()}
      </td>
      <td className="py-3 px-4 text-right whitespace-nowrap">
        <button
          onClick={(e) => {
            e.stopPropagation();
            onSelect(log);
          }}
          aria-label={`Inspect session #${log.id}`}
          className="text-indigo-600 dark:text-indigo-400 hover:text-indigo-500 dark:hover:text-indigo-300 font-semibold text-[11px] inline-flex items-center space-x-1 bg-indigo-500/10 hover:bg-indigo-500/20 px-2 py-1 rounded border border-indigo-500/20 transition-colors"
        >
          <span>Inspect</span>
          <ExternalLink className="h-3 w-3" />
        </button>
      </td>
    </tr>
  );
});

AuditTableRow.displayName = "AuditTableRow";
