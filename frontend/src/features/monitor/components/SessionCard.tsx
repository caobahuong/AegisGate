"use client";

import React, { memo } from "react";
import { Clock, RotateCw, CheckCircle2, XCircle, AlertTriangle, StopCircle, AlertCircle } from "lucide-react";
import { ExecutionResponse } from "@/types";
import { cn } from "@/lib/utils";

export interface SessionCardProps {
  execution: ExecutionResponse;
  isSelected: boolean;
  onSelect: (ex: ExecutionResponse) => void;
}

const renderCompactStatus = (status: string) => {
  switch (status) {
    case "PAUSED_FOR_REVIEW":
    case "DRY_RUN":
      return (
        <span className="flex items-center text-amber-600 dark:text-amber-400 font-semibold text-[11px]">
          <Clock className="h-3 w-3 mr-1 animate-pulse" />
          Pending Review
        </span>
      );
    case "QUEUED":
      return (
        <span className="flex items-center text-indigo-600 dark:text-indigo-400 font-semibold text-[11px]">
          <Clock className="h-3 w-3 mr-1" />
          Queued
        </span>
      );
    case "EXECUTING":
      return (
        <span className="flex items-center text-indigo-600 dark:text-indigo-400 font-semibold text-[11px]">
          <RotateCw className="h-3 w-3 mr-1 animate-spin" />
          Running
        </span>
      );
    case "COMPLETED":
      return (
        <span className="flex items-center text-emerald-600 dark:text-emerald-400 font-semibold text-[11px]">
          <CheckCircle2 className="h-3 w-3 mr-1" />
          Completed
        </span>
      );
    case "REJECTED":
      return (
        <span className="flex items-center text-red-600 dark:text-red-400 font-semibold text-[11px]">
          <XCircle className="h-3 w-3 mr-1" />
          Rejected
        </span>
      );
    case "TIMEOUT":
      return (
        <span className="flex items-center text-red-600 dark:text-red-400 font-semibold text-[11px]">
          <AlertTriangle className="h-3 w-3 mr-1" />
          Timeout (Killed)
        </span>
      );
    case "ABORTED":
      return (
        <span className="flex items-center text-slate-600 dark:text-slate-400 font-semibold text-[11px]">
          <StopCircle className="h-3 w-3 mr-1" />
          Aborted
        </span>
      );
    case "FAILED":
      return (
        <span className="flex items-center text-red-600 dark:text-red-400 font-semibold text-[11px]">
          <AlertCircle className="h-3 w-3 mr-1" />
          Failed
        </span>
      );
    default:
      return (
        <span className="text-slate-600 dark:text-slate-400 text-[11px] font-mono">{status}</span>
      );
  }
};

export const SessionCard = memo<SessionCardProps>(({ execution, isSelected, onSelect }) => {
  const isPending =
    execution.status === "PAUSED_FOR_REVIEW" ||
    execution.status === "DRY_RUN" ||
    execution.status === "QUEUED";
  const isRunning = execution.status === "EXECUTING";
  const isBlocked =
    execution.status === "REJECTED" ||
    execution.status === "TIMEOUT" ||
    execution.status === "ABORTED" ||
    execution.status === "FAILED";
  const isCompleted = execution.status === "COMPLETED";

  return (
    <button
      onClick={() => onSelect(execution)}
      data-testid={`session-pill-${execution.id}`}
      className={cn(
        "flex-shrink-0 text-left rounded-xl border p-3 transition-all cursor-pointer min-w-[210px] max-w-[260px] flex flex-col justify-between space-y-2",
        isSelected
          ? "bg-white dark:bg-slate-900 border-indigo-500 ring-1 ring-indigo-500/50 shadow-md shadow-indigo-500/10"
          : "bg-slate-50 dark:bg-slate-950/70 border-slate-200 dark:border-slate-800/80 hover:border-slate-300 dark:hover:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-900/60",
        isPending &&
          !isSelected &&
          "border-amber-400/40 bg-amber-50/50 dark:border-amber-500/40 dark:bg-amber-500/[0.04]",
        isRunning &&
          !isSelected &&
          "border-indigo-400/40 bg-indigo-50/50 dark:border-indigo-500/40 dark:bg-indigo-500/[0.04]"
      )}
    >
      <div className="flex items-center justify-between w-full">
        <span className="font-mono text-xs font-bold text-slate-800 dark:text-slate-200">
          #{execution.id}
        </span>
        <span
          className={cn(
            "text-[10px] font-semibold px-1.5 py-0.5 rounded uppercase tracking-wider font-mono",
            execution.query_type === "WRITE"
              ? "bg-purple-100 text-purple-800 border border-purple-400 dark:bg-purple-500/20 dark:text-purple-300 dark:border-purple-500/30"
              : "bg-sky-100 text-sky-800 border border-sky-400 dark:bg-sky-500/20 dark:text-sky-300 dark:border-sky-500/30"
          )}
        >
          {execution.query_type}
        </span>
      </div>

      <div className="flex items-center space-x-1.5 text-xs">
        {renderCompactStatus(execution.status)}
      </div>

      <div className="flex items-center justify-between text-[10px] text-slate-500 dark:text-slate-400 pt-1.5 border-t border-slate-200 dark:border-slate-800/60 w-full">
        <span className="truncate max-w-[110px] font-medium" title={execution.target_id}>
          {execution.target_id}
        </span>
        {isPending && (
          <span className="text-amber-600 dark:text-amber-400 font-bold flex items-center animate-pulse">
            Action Required
          </span>
        )}
        {isRunning && (
          <span className="text-indigo-600 dark:text-indigo-400 font-mono font-semibold">
            SPID: {execution.spid ?? "..."}
          </span>
        )}
        {isCompleted && (
          <span className="font-mono text-emerald-600 dark:text-emerald-400/90 font-medium">
            {execution.execution_time_ms !== null ? `${execution.execution_time_ms}ms` : "OK"}
          </span>
        )}
        {isBlocked && (
          <span className="text-red-600 dark:text-red-400 font-medium">
            {execution.status === "TIMEOUT" ? "Timeout" : "Violation"}
          </span>
        )}
      </div>
    </button>
  );
});

SessionCard.displayName = "SessionCard";
