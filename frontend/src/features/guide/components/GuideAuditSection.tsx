"use client";

import React from "react";
import { FileText } from "lucide-react";

export const GuideAuditSection: React.FC = () => {
  return (
    <div className="space-y-4 animate-in fade-in duration-150">
      <div>
        <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center space-x-2">
          <FileText className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />
          <span>6. Audit Logs &amp; Detailed Input / Output Inspection</span>
        </h3>
        <p className="text-slate-500 dark:text-slate-400 mt-1">
          Complete immutable compliance trail separating query Input and database Output.
        </p>
      </div>

      <div className="space-y-2">
        <h4 className="font-bold text-slate-800 dark:text-slate-200">
          Two Core Views in Audit Inspector:
        </h4>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-[11px]">
          <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 space-y-1">
            <strong className="text-indigo-600 dark:text-indigo-400 block font-bold text-xs">
              Input Details:
            </strong>
            <p className="text-slate-600 dark:text-slate-400">
              • Full SQL Statement / Database Command.
            </p>
            <p className="text-slate-600 dark:text-slate-400">
              • AI Intent &amp; Reasoning context.
            </p>
            <p className="text-slate-600 dark:text-slate-400">
              • Target Database &amp; Operation Type (READ/WRITE).
            </p>
          </div>

          <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 space-y-1">
            <strong className="text-emerald-600 dark:text-emerald-400 block font-bold text-xs">
              Output Details:
            </strong>
            <p className="text-slate-600 dark:text-slate-400">
              • Interactive Data Table of returned rows.
            </p>
            <p className="text-slate-600 dark:text-slate-400">
              • Total Rows Returned / Rows Affected.
            </p>
            <p className="text-slate-600 dark:text-slate-400">
              • Actual execution latency in milliseconds (ms).
            </p>
            <p className="text-slate-600 dark:text-slate-400">
              • Raw JSON viewer and 1-click result copy.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
