"use client";

import React, { useState } from "react";
import { Send, Terminal } from "lucide-react";
import { ExecutionResponse, PluginProfileResponse } from "@/types";
import { Button } from "@/shared/ui/Button";

export interface QuerySimulatorPaneProps {
  plugins: PluginProfileResponse[];
  onSubmitQuery: (targetId: string, query: string, reasoning: string) => Promise<void | ExecutionResponse>;
  isSubmitting?: boolean;
  selectedExecutionId?: string | null;
}

export const QuerySimulatorPane: React.FC<QuerySimulatorPaneProps> = ({
  plugins,
  onSubmitQuery,
  isSubmitting = false,
  selectedExecutionId,
}) => {
  const [targetId, setTargetId] = useState<string>(plugins[0]?.id || "sqlserver_prod");
  const [query, setQuery] = useState<string>(
    "SELECT o.OrderID, o.OrderDate, o.TotalAmount\nFROM dbo.Orders o\nWHERE o.Status = 'Completed';"
  );
  const [reasoning, setReasoning] = useState<string>(
    "AI Agent retrieving latest completed customer orders for dashboard KPI computation."
  );

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim() || isSubmitting) return;
    await onSubmitQuery(targetId, query, reasoning);
  };

  return (
    <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 space-y-4 shadow-sm">
      <div className="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-slate-800">
        <div className="flex items-center space-x-2">
          <Terminal className="h-4 w-4 text-indigo-500 dark:text-indigo-400" />
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-800 dark:text-slate-200">
            1. AI Query &amp; Reasoning
          </h2>
        </div>
        {selectedExecutionId && (
          <span className="text-[10px] font-mono text-slate-500 dark:text-slate-400">#{selectedExecutionId}</span>
        )}
      </div>

      <form onSubmit={handleSubmit} className="space-y-3">
        <div>
          <label className="block text-[11px] font-semibold text-slate-700 dark:text-slate-400 uppercase tracking-wider mb-1">
            Target Plugin
          </label>
          <select
            value={targetId}
            onChange={(e) => setTargetId(e.target.value)}
            className="w-full bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-800 rounded px-2.5 py-1.5 text-xs text-slate-900 dark:text-slate-200 focus:outline-none focus:border-indigo-500"
          >
            {plugins.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name} ({p.id})
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-[11px] font-semibold text-slate-700 dark:text-slate-400 uppercase tracking-wider mb-1">
            Raw Query Statement (SQL / Command)
          </label>
          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            rows={5}
            className="w-full font-mono text-xs bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-800 rounded p-2.5 text-slate-900 dark:text-slate-100 focus:outline-none focus:border-indigo-500 leading-relaxed resize-y"
            placeholder="Enter SQL or database statement..."
          />
        </div>

        <div>
          <label className="block text-[11px] font-semibold text-slate-700 dark:text-slate-400 uppercase tracking-wider mb-1">
            AI Intent / Reasoning
          </label>
          <textarea
            value={reasoning}
            onChange={(e) => setReasoning(e.target.value)}
            rows={2}
            className="w-full text-xs bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-800 rounded p-2.5 text-slate-800 dark:text-slate-300 focus:outline-none focus:border-indigo-500 leading-normal resize-none"
            placeholder="Explain the AI's intent..."
          />
        </div>

        <Button
          type="submit"
          disabled={isSubmitting}
          isLoading={isSubmitting}
          className="w-full"
        >
          <Send className="h-3.5 w-3.5 mr-1.5" />
          <span>{isSubmitting ? "Submitting..." : "Send Query to AegisGate"}</span>
        </Button>
      </form>

      {/* Preset Rule-Testing Queries */}
      <div className="pt-2 border-t border-slate-200 dark:border-slate-800 space-y-1.5">
        <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
          Quick Rule Violation Tests:
        </span>
        <div className="flex flex-wrap gap-1.5">
          <button
            type="button"
            onClick={() => {
              setQuery("SELECT o.OrderID, a.Action\nFROM dbo.Orders o\nINNER JOIN dbo.AuditLogs a ON o.OrderID = a.LogID;");
              setReasoning("Test query triggering FORBID_JOIN rule between Orders and AuditLogs.");
            }}
            className="px-2 py-1 rounded bg-slate-100 hover:bg-slate-200 dark:bg-slate-950 dark:hover:bg-slate-800 border border-slate-300 dark:border-slate-800 text-[10px] text-amber-700 dark:text-amber-400 font-mono transition-colors"
          >
            Forbidden JOIN Test
          </button>
          <button
            type="button"
            onClick={() => {
              setQuery("SELECT * FROM dbo.Orders;");
              setReasoning("Test query triggering Table Scan rule due to missing WHERE filter.");
            }}
            className="px-2 py-1 rounded bg-slate-100 hover:bg-slate-200 dark:bg-slate-950 dark:hover:bg-slate-800 border border-slate-300 dark:border-slate-800 text-[10px] text-red-700 dark:text-red-400 font-mono transition-colors"
          >
            Table Scan Test
          </button>
        </div>
      </div>
    </div>
  );
};
