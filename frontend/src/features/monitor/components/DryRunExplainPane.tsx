"use client";

import React from "react";
import { CheckCircle2, Layers, ShieldAlert } from "lucide-react";
import { ExecutionResponse } from "@/types";

export interface DryRunExplainPaneProps {
  selectedExecution: ExecutionResponse | null;
}

export const DryRunExplainPane: React.FC<DryRunExplainPaneProps> = ({ selectedExecution }) => {
  return (
    <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 space-y-4 shadow-sm">
      <div className="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-slate-800">
        <div className="flex items-center space-x-2">
          <Layers className="h-4 w-4 text-indigo-500 dark:text-indigo-400" />
          <h2 className="text-xs font-bold uppercase tracking-wider text-slate-800 dark:text-slate-200">
            2. Dry-Run &amp; Explain Plan
          </h2>
        </div>
        {selectedExecution && (
          <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
            {selectedExecution.query_type} Query
          </span>
        )}
      </div>

      {!selectedExecution ? (
        <div className="py-16 text-center text-slate-400 dark:text-slate-500 text-xs">
          Select an execution session or submit a query to view Dry-Run analysis.
        </div>
      ) : (
        <div className="space-y-4">
          {/* Violations Warning Banner */}
          {selectedExecution.violations && selectedExecution.violations.length > 0 ? (
            <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-600 dark:text-red-400 space-y-1">
              <div className="flex items-center space-x-2 text-xs font-bold">
                <ShieldAlert className="h-4 w-4 text-red-600 dark:text-red-400" />
                <span>Rule Violations Detected ({selectedExecution.violations.length})</span>
              </div>
              <ul className="list-disc list-inside text-xs space-y-1 pt-1 text-red-700 dark:text-red-300">
                {selectedExecution.violations.map((violation, i) => (
                  <li key={i} className="leading-snug">
                    {violation}
                  </li>
                ))}
              </ul>
            </div>
          ) : (
            <div className="p-2.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-600 dark:text-emerald-400 flex items-center space-x-2 text-xs font-medium">
              <CheckCircle2 className="h-4 w-4 flex-shrink-0" />
              <span>Zero rule violations. Query meets governance criteria.</span>
            </div>
          )}

          {/* Explain Plan Structured Viewer */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-[11px] font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wider">
                Execution Plan (SHOWPLAN)
              </span>
              <span className="text-[10px] font-mono text-slate-400 dark:text-slate-500">
                Target: {selectedExecution.target_id}
              </span>
            </div>
            <div className="font-mono text-xs bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded p-3 text-slate-800 dark:text-slate-300 max-h-64 overflow-y-auto leading-relaxed">
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
  );
};
