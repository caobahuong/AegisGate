"use client";

import React from "react";
import { Shield } from "lucide-react";

export const GuideRulesSection: React.FC = () => {
  return (
    <div className="space-y-4 animate-in fade-in duration-150">
      <div>
        <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center space-x-2">
          <Shield className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />
          <span>4. Governance Rules &amp; Target Scoping</span>
        </h3>
        <p className="text-slate-500 dark:text-slate-400 mt-1">
          Configure automated query guardrails to prevent costly or destructive AI-generated queries.
        </p>
      </div>

      <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 space-y-2">
        <h4 className="font-bold text-slate-800 dark:text-slate-200">Creating &amp; Editing Rules:</h4>
        <p className="text-slate-500 dark:text-slate-400 text-[11px]">
          In the <strong>&quot;Governance Rules&quot;</strong> sub-tab, click <strong>&quot;Create Rule&quot;</strong> to add
          a new policy, or click the pencil <strong>&quot;Edit&quot;</strong> icon on any existing rule card:
        </p>
        <ul className="list-disc list-inside space-y-1 text-[11px] pl-2 text-slate-700 dark:text-slate-300">
          <li>
            <strong className="text-indigo-600 dark:text-indigo-400">Target Scope:</strong> Choose{" "}
            <code className="text-indigo-600 dark:text-indigo-300 font-mono">Global Scope</code> to enforce across all
            databases, or assign to a specific plugin (e.g.,{" "}
            <code className="text-emerald-600 dark:text-emerald-300 font-mono">sqlserver_prod</code>).
          </li>
          <li>
            <strong className="text-indigo-600 dark:text-indigo-400">Rule Type:</strong>
            <ul className="list-circle list-inside pl-4 pt-1 space-y-1">
              <li>
                <code className="text-indigo-600 dark:text-indigo-300 font-mono">FORBID_JOIN</code>: Block joining sensitive
                tables (e.g., <code className="text-slate-800 dark:text-slate-200 font-mono">Orders,AuditLogs</code>).
              </li>
              <li>
                <code className="text-indigo-600 dark:text-indigo-300 font-mono">FORBID_TABLE_SCAN</code>: Reject queries
                missing indexed WHERE clauses that cause full table scans.
              </li>
              <li>
                <code className="text-indigo-600 dark:text-indigo-300 font-mono">MAX_EXECUTION_TIME</code>: Cap maximum
                allowed execution duration in seconds (e.g., 15s).
              </li>
              <li>
                <code className="text-indigo-600 dark:text-indigo-300 font-mono">CUSTOM</code>: Custom regular expression
                matching for domain-specific policies.
              </li>
              <li>
                <code className="text-indigo-600 dark:text-indigo-300 font-mono">REDACT_FIELD</code>: Output masking. Listed
                fields (e.g., <code className="text-slate-800 dark:text-slate-200 font-mono">Password,SSN</code>) stay in
                result but their value becomes <code className="text-slate-800 dark:text-slate-200 font-mono">null</code>.
              </li>
              <li>
                <code className="text-indigo-600 dark:text-indigo-300 font-mono">REMOVE_FIELD</code>: Output masking. Listed
                fields are deleted from the result entirely before storage.
              </li>
            </ul>
          </li>
        </ul>
      </div>

      <div className="p-3 rounded-lg bg-indigo-50 dark:bg-indigo-600/10 border border-indigo-200 dark:border-indigo-500/20 text-[11px] space-y-1">
        <span className="font-bold text-indigo-700 dark:text-indigo-400 block">Target Scope Filter:</span>
        <p className="text-slate-600 dark:text-slate-300">
          Use the Target selector dropdown at the top of the Knowledge &amp; Rules tab to filter between{" "}
          <em>All Pluggable Targets</em>, <em>Global Scope Only</em>, or a specific Plugin.
        </p>
      </div>
    </div>
  );
};
