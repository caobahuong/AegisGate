"use client";

import React, { useState } from "react";
import {
  CheckCircle2,
  Code2,
  Copy,
  Database,
  FileText,
  Layers,
  ShieldAlert,
  Sparkles,
} from "lucide-react";
import { ExecutionResponse } from "@/types";
import { Modal } from "@/shared/ui/Modal";
import { cn } from "@/lib/utils";
import { parseResultSummary } from "../lib/parseResult";
import { AuditDetailOutputTab } from "./AuditDetailOutputTab";

export interface AuditDetailDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  log: ExecutionResponse | null;
  pluginName: string;
  onCopy: (text: string, label: string) => void;
}

export const AuditDetailDrawer: React.FC<AuditDetailDrawerProps> = ({
  isOpen,
  onClose,
  log,
  pluginName,
  onCopy,
}) => {
  const [modalTab, setModalTab] = useState<"output" | "input" | "governance">("output");
  const [outputViewMode, setOutputViewMode] = useState<"table" | "json">("table");

  if (!log) return null;
  const res = parseResultSummary(log.result_summary);

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Execution Audit Detail: #${log.id}`}
      subtitle={`${pluginName} • ${new Date(log.created_at).toLocaleString()}`}
      icon={<FileText className="h-5 w-5" />}
      maxWidth="3xl"
    >
      <div className="space-y-4">
        {/* Quick KPI Overview Bar */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-slate-50 dark:bg-slate-950 p-3.5 rounded-xl border border-slate-200 dark:border-slate-800 text-xs">
          <div>
            <span className="text-slate-500 block text-[10px] uppercase font-semibold">Query Type</span>
            <span className="font-mono text-slate-900 dark:text-slate-200 font-bold">{log.query_type}</span>
          </div>
          <div>
            <span className="text-slate-500 block text-[10px] uppercase font-semibold">Execution Latency</span>
            <span className="font-mono text-emerald-600 dark:text-emerald-400 font-bold">
              {log.execution_time_ms !== null ? `${log.execution_time_ms} ms` : "N/A"}
            </span>
          </div>
          <div>
            <span className="text-slate-500 block text-[10px] uppercase font-semibold">Result Records</span>
            <span className="font-mono text-indigo-600 dark:text-indigo-400 font-bold">
              {res.dataRows
                ? `${res.dataRows.length} rows`
                : res.rowsAffected !== null
                  ? `${res.rowsAffected} affected`
                  : "0 rows"}
            </span>
          </div>
          <div>
            <span className="text-slate-500 block text-[10px] uppercase font-semibold">Database SPID</span>
            <span className="font-mono text-slate-800 dark:text-slate-200">{log.spid || "Session clean"}</span>
          </div>
        </div>

        {/* Sub-tab Navigation */}
        <div className="flex items-center space-x-2 border-b border-slate-200 dark:border-slate-800 pb-2">
          {(["output", "input", "governance"] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setModalTab(tab)}
              className={cn(
                "flex items-center space-x-1.5 text-xs font-semibold px-3 py-1.5 rounded-lg transition-colors",
                modalTab === tab
                  ? "bg-indigo-50 text-indigo-700 border border-indigo-200 dark:bg-indigo-600/20 dark:text-indigo-300 dark:border-indigo-500/30 shadow-xs"
                  : "text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-200"
              )}
            >
              {tab === "output" && <Database className="h-3.5 w-3.5" />}
              {tab === "input" && <Code2 className="h-3.5 w-3.5" />}
              {tab === "governance" && <Layers className="h-3.5 w-3.5" />}
              <span className="capitalize">{tab === "output" ? "Output & Results" : tab === "input" ? "Input Statement" : "Dry-Run Plan"}</span>
            </button>
          ))}
        </div>

        {/* Output Tab */}
        {modalTab === "output" && (
          <AuditDetailOutputTab
            log={log}
            res={res}
            outputViewMode={outputViewMode}
            setOutputViewMode={setOutputViewMode}
            onCopy={onCopy}
          />
        )}

        {/* Input Tab */}
        {modalTab === "input" && (
          <div className="space-y-4">
            <div className="p-3.5 rounded-xl bg-indigo-50 dark:bg-indigo-600/10 border border-indigo-200 dark:border-indigo-500/20 space-y-1">
              <div className="flex items-center space-x-2 text-xs font-bold text-indigo-700 dark:text-indigo-400">
                <Sparkles className="h-4 w-4" />
                <span>AI Intent &amp; Purpose Reasoning</span>
              </div>
              <p className="text-xs text-slate-700 dark:text-slate-200 leading-relaxed pl-6">
                {log.reasoning || "Direct database execution requested without specific reasoning context."}
              </p>
            </div>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wider flex items-center space-x-2">
                  <Code2 className="h-3.5 w-3.5 text-indigo-500" />
                  <span>Full SQL Statement</span>
                </span>
                <button
                  onClick={() => onCopy(log.query, "SQL query")}
                  className="flex items-center space-x-1 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 px-2.5 py-1 rounded-lg text-[11px] border border-slate-300 dark:border-slate-700 transition-colors"
                >
                  <Copy className="h-3 w-3" />
                  <span>Copy SQL</span>
                </button>
              </div>
              <div className="bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl p-4 font-mono text-xs text-slate-800 dark:text-slate-200 max-h-56 overflow-y-auto whitespace-pre-wrap leading-relaxed">
                {log.query}
              </div>
            </div>
          </div>
        )}

        {/* Governance Tab */}
        {modalTab === "governance" && (
          <div className="space-y-4">
            {log.violations && log.violations.length > 0 ? (
              <div className="p-3.5 rounded-xl bg-red-500/10 border border-red-500/20 text-red-600 dark:text-red-400 space-y-1.5">
                <div className="flex items-center space-x-2 text-xs font-bold">
                  <ShieldAlert className="h-4 w-4" />
                  <span>Governance Violations ({log.violations.length})</span>
                </div>
                <ul className="list-disc list-inside text-xs space-y-1 pl-4 text-red-600 dark:text-red-300">
                  {log.violations.map((v, i) => (
                    <li key={i}>{v}</li>
                  ))}
                </ul>
              </div>
            ) : (
              <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-600 dark:text-emerald-400 flex items-center space-x-2 text-xs font-medium">
                <CheckCircle2 className="h-4 w-4" />
                <span>Passed all active governance policies.</span>
              </div>
            )}
            <div className="space-y-2">
              <span className="text-xs font-bold text-slate-700 dark:text-slate-300 uppercase tracking-wider block">
                Showplan &amp; Optimizer Metadata
              </span>
              <div className="bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-xl p-3.5 font-mono text-xs text-slate-800 dark:text-slate-300 max-h-64 overflow-y-auto">
                <pre className="whitespace-pre-wrap">
                  {log.explain_plan ? JSON.stringify(log.explain_plan, null, 2) : "No explain plan generated"}
                </pre>
              </div>
            </div>
          </div>
        )}
      </div>
    </Modal>
  );
};
