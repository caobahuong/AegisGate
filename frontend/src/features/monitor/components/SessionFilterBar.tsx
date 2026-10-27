"use client";

import React from "react";
import { Clock, Database, RotateCw, ShieldAlert, CheckCircle2 } from "lucide-react";
import { cn } from "@/lib/utils";

export type SessionFilter = "ALL" | "PENDING" | "RUNNING" | "BLOCKED" | "COMPLETED";

export interface SessionFilterBarProps {
  sessionFilter: SessionFilter;
  onFilterChange: (filter: SessionFilter) => void;
  totalCount: number;
  pendingCount: number;
  runningCount: number;
  blockedCount: number;
  completedCount: number;
}

export const SessionFilterBar: React.FC<SessionFilterBarProps> = ({
  sessionFilter,
  onFilterChange,
  totalCount,
  pendingCount,
  runningCount,
  blockedCount,
  completedCount,
}) => {
  return (
    <div className="flex items-center space-x-1.5 overflow-x-auto pb-1 sm:pb-0">
      {/* Filter: All */}
      <button
        type="button"
        onClick={() => onFilterChange("ALL")}
        data-testid="filter-all-btn"
        className={cn(
          "px-2.5 py-1 rounded-lg text-xs font-medium transition-all flex items-center space-x-1.5 border",
          sessionFilter === "ALL"
            ? "bg-slate-200 dark:bg-slate-800 text-slate-900 dark:text-slate-100 border-slate-300 dark:border-slate-700 shadow-sm"
            : "bg-slate-50 dark:bg-slate-950/60 text-slate-600 dark:text-slate-400 border-slate-200 dark:border-slate-800/80 hover:text-slate-900 dark:hover:text-slate-200"
        )}
      >
        <Database className="h-3 w-3" />
        <span>All</span>
        <span className="ml-1 px-1.5 py-0.2 rounded-full text-[10px] bg-slate-200 dark:bg-slate-700 text-slate-800 dark:text-slate-100 font-mono">
          {totalCount}
        </span>
      </button>

      {/* Filter: Pending Review */}
      <button
        type="button"
        onClick={() => onFilterChange("PENDING")}
        data-testid="filter-pending-btn"
        className={cn(
          "px-2.5 py-1 rounded-lg text-xs font-medium transition-all flex items-center space-x-1.5 border",
          sessionFilter === "PENDING"
            ? "bg-amber-500/20 text-amber-700 dark:text-amber-300 border-amber-500/50 shadow-sm shadow-amber-500/10"
            : pendingCount > 0
              ? "bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-500/30 hover:bg-amber-500/15"
              : "bg-slate-50 dark:bg-slate-950/60 text-slate-600 dark:text-slate-400 border-slate-200 dark:border-slate-800/80 hover:text-slate-900 dark:hover:text-slate-200"
        )}
      >
        <Clock
          className={cn(
            "h-3 w-3",
            pendingCount > 0 && "animate-pulse text-amber-500 dark:text-amber-400"
          )}
        />
        <span>Pending Review</span>
        <span
          className={cn(
            "ml-1 px-1.5 py-0.2 rounded-full text-[10px] font-mono",
            pendingCount > 0
              ? "bg-amber-600 text-white font-bold animate-pulse dark:bg-amber-500/30 dark:text-amber-300"
              : "bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-400"
          )}
        >
          {pendingCount}
        </span>
      </button>

      {/* Filter: Running */}
      <button
        type="button"
        onClick={() => onFilterChange("RUNNING")}
        data-testid="filter-running-btn"
        className={cn(
          "px-2.5 py-1 rounded-lg text-xs font-medium transition-all flex items-center space-x-1.5 border",
          sessionFilter === "RUNNING"
            ? "bg-indigo-50 text-indigo-700 border-indigo-300 dark:bg-indigo-500/20 dark:text-indigo-300 dark:border-indigo-500/50 shadow-xs"
            : runningCount > 0
              ? "bg-indigo-50/80 text-indigo-700 border-indigo-200 hover:bg-indigo-100 dark:bg-indigo-500/10 dark:text-indigo-400 dark:border-indigo-500/30 dark:hover:bg-indigo-500/15"
              : "bg-slate-50 dark:bg-slate-950/60 text-slate-600 dark:text-slate-400 border-slate-200 dark:border-slate-800/80 hover:text-slate-900 dark:hover:text-slate-200"
        )}
      >
        <RotateCw
          className={cn(
            "h-3 w-3",
            runningCount > 0 && "animate-spin text-indigo-600 dark:text-indigo-400"
          )}
        />
        <span>Running</span>
        <span
          className={cn(
            "ml-1 px-1.5 py-0.2 rounded-full text-[10px] font-mono",
            runningCount > 0
              ? "bg-indigo-600 text-white font-bold dark:bg-indigo-500/30 dark:text-indigo-300"
              : "bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-400"
          )}
        >
          {runningCount}
        </span>
      </button>

      {/* Filter: Blocked */}
      <button
        type="button"
        onClick={() => onFilterChange("BLOCKED")}
        data-testid="filter-blocked-btn"
        className={cn(
          "px-2.5 py-1 rounded-lg text-xs font-medium transition-all flex items-center space-x-1.5 border",
          sessionFilter === "BLOCKED"
            ? "bg-red-500/20 text-red-700 dark:text-red-300 border-red-500/50 shadow-sm shadow-red-500/10"
            : blockedCount > 0
              ? "bg-red-500/10 text-red-700 dark:text-red-400 border-red-500/30 hover:bg-red-500/15"
              : "bg-slate-50 dark:bg-slate-950/60 text-slate-600 dark:text-slate-400 border-slate-200 dark:border-slate-800/80 hover:text-slate-900 dark:hover:text-slate-200"
        )}
      >
        <ShieldAlert className="h-3 w-3" />
        <span>Blocked / Failed</span>
        <span
          className={cn(
            "ml-1 px-1.5 py-0.2 rounded-full text-[10px] font-mono",
            blockedCount > 0
              ? "bg-red-600 text-white font-bold dark:bg-red-500/30 dark:text-red-300"
              : "bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-400"
          )}
        >
          {blockedCount}
        </span>
      </button>

      {/* Filter: Completed */}
      <button
        type="button"
        onClick={() => onFilterChange("COMPLETED")}
        data-testid="filter-completed-btn"
        className={cn(
          "px-2.5 py-1 rounded-lg text-xs font-medium transition-all flex items-center space-x-1.5 border",
          sessionFilter === "COMPLETED"
            ? "bg-emerald-500/20 text-emerald-700 dark:text-emerald-300 border-emerald-500/50 shadow-sm shadow-emerald-500/10"
            : completedCount > 0
              ? "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/30 hover:bg-emerald-500/15"
              : "bg-slate-50 dark:bg-slate-950/60 text-slate-600 dark:text-slate-400 border-slate-200 dark:border-slate-800/80 hover:text-slate-900 dark:hover:text-slate-200"
        )}
      >
        <CheckCircle2 className="h-3 w-3" />
        <span>Completed</span>
        <span
          className={cn(
            "ml-1 px-1.5 py-0.2 rounded-full text-[10px] font-mono",
            completedCount > 0
              ? "bg-emerald-600 text-white font-bold dark:bg-emerald-500/30 dark:text-emerald-300"
              : "bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-400"
          )}
        >
          {completedCount}
        </span>
      </button>
    </div>
  );
};
