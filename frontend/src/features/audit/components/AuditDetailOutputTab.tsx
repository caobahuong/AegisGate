"use client";

import React from "react";
import { Code2, Copy, ShieldAlert, Table as TableIcon } from "lucide-react";
import { ExecutionResponse } from "@/types";
import { cn } from "@/lib/utils";
import { ExtractedResult } from "../lib/parseResult";

export interface AuditDetailOutputTabProps {
  log: ExecutionResponse;
  res: ExtractedResult;
  outputViewMode: "table" | "json";
  setOutputViewMode: (mode: "table" | "json") => void;
  onCopy: (text: string, label: string) => void;
}

export const AuditDetailOutputTab: React.FC<AuditDetailOutputTabProps> = ({
  log,
  res,
  outputViewMode,
  setOutputViewMode,
  onCopy,
}) => {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <span className="text-xs font-bold text-slate-800 dark:text-slate-200">
          Returned Dataset &amp; Execution Payload
        </span>
        <div className="flex items-center space-x-2">
          <div className="flex items-center bg-slate-100 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg p-0.5">
            <button
              onClick={() => setOutputViewMode("table")}
              className={cn(
                "flex items-center space-x-1 text-[11px] px-2.5 py-1 rounded-md transition-colors",
                outputViewMode === "table"
                  ? "bg-indigo-600 text-white font-semibold shadow-sm"
                  : "text-slate-600 dark:text-slate-400"
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
                  : "text-slate-600 dark:text-slate-400"
              )}
            >
              <Code2 className="h-3 w-3" />
              <span>Raw JSON</span>
            </button>
          </div>
          {log.result_summary && (
            <button
              onClick={() => onCopy(JSON.stringify(log.result_summary, null, 2), "Output payload")}
              className="flex items-center space-x-1 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 px-2.5 py-1 rounded-lg text-[11px] border border-slate-300 dark:border-slate-700 transition-colors"
            >
              <Copy className="h-3 w-3" />
              <span>Copy Output</span>
            </button>
          )}
        </div>
      </div>

      {log.error_message && (
        <div className="p-3.5 rounded-xl bg-red-500/10 border border-red-500/20 text-red-600 dark:text-red-400 space-y-1">
          <div className="flex items-center space-x-2 text-xs font-bold">
            <ShieldAlert className="h-4 w-4" />
            <span>Execution Rejection / Error Output</span>
          </div>
          <p className="font-mono text-xs pl-6">{log.error_message}</p>
        </div>
      )}

      {outputViewMode === "table" ? (
        <div className="bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden">
          {res.dataRows && res.dataRows.length > 0 ? (
            <div className="overflow-x-auto max-h-72">
              <table className="w-full text-left text-xs border-collapse">
                <thead className="bg-slate-100 dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 sticky top-0">
                  <tr>
                    <th className="py-2.5 px-3 font-mono w-10">#</th>
                    {res.columns.map((col) => (
                      <th
                        key={col}
                        className="py-2.5 px-3 font-mono font-bold text-slate-800 dark:text-slate-200 whitespace-nowrap"
                      >
                        {col}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 dark:divide-slate-800/60 font-mono text-[11px]">
                  {res.dataRows.map((row, idx) => (
                    <tr key={idx} className="hover:bg-slate-100/50 dark:hover:bg-slate-900/40">
                      <td className="py-2.5 px-3 text-slate-400">{idx + 1}</td>
                      {res.columns.map((col) => (
                        <td
                          key={col}
                          className="py-2.5 px-3 text-slate-700 dark:text-slate-300 whitespace-nowrap"
                        >
                          {row[col] !== null && row[col] !== undefined ? (
                            String(row[col])
                          ) : (
                            <span className="text-slate-400 italic">null</span>
                          )}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div className="p-8 text-center text-slate-500 text-xs italic">
              No output dataset available.
            </div>
          )}
        </div>
      ) : (
        <div className="bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl p-3.5 font-mono text-xs text-slate-800 dark:text-slate-300 max-h-72 overflow-y-auto">
          <pre className="whitespace-pre-wrap">
            {JSON.stringify(log.result_summary || { status: log.status }, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
};
