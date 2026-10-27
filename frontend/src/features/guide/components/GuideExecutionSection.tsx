"use client";

import React from "react";
import { Activity, Clock, CheckCircle2, AlertTriangle } from "lucide-react";

export const GuideExecutionSection: React.FC = () => {
  return (
    <div className="space-y-4 animate-in fade-in duration-150">
      <div>
        <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center space-x-2">
          <Activity className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />
          <span>5. Live Execution Monitor &amp; Approval Gatekeeper</span>
        </h3>
        <p className="text-slate-500 dark:text-slate-400 mt-1">
          Monitor real-time query execution streams via Server-Sent Events (SSE).
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 space-y-1.5">
          <div className="flex items-center space-x-1.5 text-amber-600 dark:text-amber-400 font-bold text-xs">
            <Clock className="h-3.5 w-3.5" />
            <span>Manual Review Mode (Default)</span>
          </div>
          <p className="text-[11px] text-slate-600 dark:text-slate-400">
            When Header toggle is{" "}
            <strong className="text-slate-800 dark:text-slate-200">OFF</strong>: After passing
            Dry-Run, queries pause at{" "}
            <code className="text-amber-600 dark:text-amber-400 font-mono">PAUSED_FOR_REVIEW</code>.
            Click <strong>&quot;Approve &amp; Run&quot;</strong> to execute or{" "}
            <strong>&quot;Reject&quot;</strong> to cancel.
          </p>
        </div>

        <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 space-y-1.5">
          <div className="flex items-center space-x-1.5 text-emerald-600 dark:text-emerald-400 font-bold text-xs">
            <CheckCircle2 className="h-3.5 w-3.5" />
            <span>Auto Approval Mode</span>
          </div>
          <p className="text-[11px] text-slate-600 dark:text-slate-400">
            Switch Header toggle to{" "}
            <strong className="text-emerald-600 dark:text-emerald-400">ON</strong>: Any safe query
            (0 policy violations) is automatically approved and executed immediately, returning data
            to the AI in milliseconds.
          </p>
        </div>
      </div>

      <div className="p-3.5 rounded-xl bg-rose-50 dark:bg-rose-500/10 border border-rose-200 dark:border-rose-500/20 text-rose-800 dark:text-rose-300 text-[11px] space-y-1">
        <div className="flex items-center space-x-1.5 font-bold text-rose-700 dark:text-rose-400">
          <AlertTriangle className="h-4 w-4" />
          <span>Emergency Kill Switch (KILL SPID):</span>
        </div>
        <p>
          If a running query hangs or consumes excessive resources, clicking{" "}
          <strong>&quot;Stop &amp; KILL Session Now&quot;</strong> dispatches an immediate native
          kill command to terminate the database session.
        </p>
      </div>
    </div>
  );
};
