"use client";

import React from "react";
import { Boxes } from "lucide-react";

export const GuidePluginsSection: React.FC = () => {
  return (
    <div className="space-y-4 animate-in fade-in duration-150">
      <div>
        <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center space-x-2">
          <Boxes className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />
          <span>3. Managing Pluggable Targets (Database Connectors)</span>
        </h3>
        <p className="text-slate-500 dark:text-slate-400 mt-1">
          Each database runs as an isolated Stdio subprocess defining its own Dynamic UI Schema and custom telemetry
          card.
        </p>
      </div>

      <div className="space-y-2">
        <h4 className="font-bold text-slate-800 dark:text-slate-200">Key Capabilities on Pluggable Targets Tab:</h4>
        <ul className="space-y-2 text-[11px]">
          <li className="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800">
            <strong className="text-indigo-600 dark:text-indigo-400 block mb-0.5">Edit Configuration:</strong>
            Click <strong>&quot;Edit Configuration&quot;</strong> on any plugin card to modify Server, Port, Database
            Name, Username, or Password. Saving automatically dispatches a{" "}
            <code className="text-indigo-600 dark:text-indigo-300 font-mono">re-init</code> signal to the adapter
            subprocess.
          </li>
          <li className="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800">
            <strong className="text-indigo-600 dark:text-indigo-400 block mb-0.5">Sync Schema &amp; Indexes Now:</strong>
            Scans live table structures and indexes from the target database and updates the AI structural cache.
          </li>
          <li className="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800">
            <strong className="text-rose-600 dark:text-rose-400 block mb-0.5">Uninstall Plugin:</strong>
            Click the red trash icon to either Soft Deactivate or permanently Hard Delete the plugin from the database.
          </li>
        </ul>
      </div>
    </div>
  );
};
