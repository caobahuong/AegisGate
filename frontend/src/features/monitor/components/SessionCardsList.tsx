"use client";

import React, { memo } from "react";
import { Activity, CheckCircle2, Database, ShieldAlert } from "lucide-react";
import { ExecutionResponse } from "@/types";
import { SessionCard } from "./SessionCard";
import { SessionFilter } from "./SessionFilterBar";

export interface SessionCardsListProps {
  executions: ExecutionResponse[];
  selectedExecution: ExecutionResponse | null;
  onSelectExecution: (ex: ExecutionResponse) => void;
  sessionFilter: SessionFilter;
}

export const SessionCardsList = memo<SessionCardsListProps>(
  ({ executions, selectedExecution, onSelectExecution, sessionFilter }) => {
    if (executions.length === 0) {
      return (
        <div className="p-5 rounded-lg border border-slate-200 dark:border-slate-800/80 bg-slate-50 dark:bg-slate-950/40 text-center py-6 text-xs text-slate-500 dark:text-slate-400">
          {sessionFilter === "PENDING" && (
            <div className="flex flex-col items-center space-y-1">
              <CheckCircle2 className="h-5 w-5 text-emerald-500 mb-1" />
              <span className="font-semibold text-slate-800 dark:text-slate-200">No queries awaiting review</span>
              <span className="text-[11px] text-slate-500">
                All AI queries have been processed or the gateway is currently idle.
              </span>
            </div>
          )}
          {sessionFilter === "RUNNING" && (
            <div className="flex flex-col items-center space-y-1">
              <Activity className="h-5 w-5 text-slate-500 mb-1" />
              <span className="font-semibold text-slate-800 dark:text-slate-200">
                No active sessions running in background
              </span>
              <span className="text-[11px] text-slate-500">
                Gateway is ready to accept incoming queries from AI Clients via FastMCP.
              </span>
            </div>
          )}
          {sessionFilter === "BLOCKED" && (
            <div className="flex flex-col items-center space-y-1">
              <ShieldAlert className="h-5 w-5 text-emerald-500 mb-1" />
              <span className="font-semibold text-slate-800 dark:text-slate-200">No blocked or rejected queries</span>
              <span className="text-[11px] text-slate-500">
                Zero governance policy violations or execution timeouts recorded.
              </span>
            </div>
          )}
          {sessionFilter === "COMPLETED" && (
            <div className="flex flex-col items-center space-y-1">
              <Database className="h-5 w-5 text-slate-500 mb-1" />
              <span className="font-semibold text-slate-800 dark:text-slate-200">No completed sessions yet</span>
              <span className="text-[11px] text-slate-500">
                Submit a test query below to verify the full execution lifecycle.
              </span>
            </div>
          )}
          {sessionFilter === "ALL" && (
            <div className="flex flex-col items-center space-y-1">
              <Activity className="h-5 w-5 text-slate-500 mb-1" />
              <span className="font-semibold text-slate-800 dark:text-slate-200">No execution sessions recorded</span>
              <span className="text-[11px] text-slate-500">
                Submit a query from the simulator below or connect an AI agent (Claude, Cursor, Cline) via MCP.
              </span>
            </div>
          )}
        </div>
      );
    }

    return (
      <div className="flex items-stretch space-x-3 overflow-x-auto pb-2 scrollbar-thin scrollbar-thumb-slate-300 dark:scrollbar-thumb-slate-800">
        {executions.map((ex) => (
          <SessionCard
            key={ex.id}
            execution={ex}
            isSelected={selectedExecution?.id === ex.id}
            onSelect={onSelectExecution}
          />
        ))}
      </div>
    );
  }
);

SessionCardsList.displayName = "SessionCardsList";
