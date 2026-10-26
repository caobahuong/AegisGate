"use client";

import React from "react";
import { Layers, Database, Shield, Activity } from "lucide-react";

export const GuideOverviewSection: React.FC = () => {
  return (
    <div className="space-y-4 animate-in fade-in duration-150">
      <div>
        <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center space-x-2">
          <Layers className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />
          <span>1. Zero-Trust Database Gateway Architecture</span>
        </h3>
        <p className="text-slate-500 dark:text-slate-400 mt-1">
          AegisGate is an intermediate security and governance layer between AI Agents (Claude Code, Cursor, Cline) and
          Production Databases (SQL Server, MongoDB, PostgreSQL).
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 space-y-1.5">
          <div className="flex items-center space-x-1.5 text-indigo-600 dark:text-indigo-400 font-bold text-xs">
            <Database className="h-3.5 w-3.5" />
            <span>Port 1: Structural Cache</span>
          </div>
          <p className="text-[11px] text-slate-600 dark:text-slate-400">
            AI Agents read table schemas, columns, primary keys, and business docs from AegisGate&apos;s cache{" "}
            <strong>without touching the live DB</strong>.
          </p>
        </div>

        <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 space-y-1.5">
          <div className="flex items-center space-x-1.5 text-amber-600 dark:text-amber-400 font-bold text-xs">
            <Shield className="h-3.5 w-3.5" />
            <span>Port 2: Dry-Run Inspection</span>
          </div>
          <p className="text-[11px] text-slate-600 dark:text-slate-400">
            Before execution, queries undergo Showplan XML / Explain inspection, cost calculation, and Governance Rules
            verification.
          </p>
        </div>

        <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 space-y-1.5">
          <div className="flex items-center space-x-1.5 text-emerald-600 dark:text-emerald-400 font-bold text-xs">
            <Activity className="h-3.5 w-3.5" />
            <span>Port 3: Guarded Execution</span>
          </div>
          <p className="text-[11px] text-slate-600 dark:text-slate-400">
            Executes queries under strict timeout guards, tracks live session SPIDs, and provides an instant Emergency
            Kill switch.
          </p>
        </div>
      </div>

      <div className="p-4 rounded-xl bg-slate-50/80 dark:bg-slate-950/80 border border-slate-200 dark:border-slate-800 space-y-2">
        <h4 className="font-bold text-slate-800 dark:text-slate-200">Query Execution Lifecycle</h4>
        <ol className="list-decimal list-inside space-y-1.5 text-[11px] text-slate-700 dark:text-slate-300">
          <li>
            <strong className="text-indigo-600 dark:text-indigo-400">AI Submission:</strong> AI submits a query along
            with its intent (Reasoning) via MCP or REST API.
          </li>
          <li>
            <strong className="text-amber-600 dark:text-amber-400">Dry-Run &amp; Rule Check:</strong> Gateway inspects for
            violations (Full Table Scan, Forbidden Joins). If violated -&gt; immediately <strong>REJECTED</strong>.
          </li>
          <li>
            <strong className="text-indigo-600 dark:text-indigo-400">Human Approval / Auto:</strong> If Auto Mode is ON
            -&gt; Executes immediately. If OFF -&gt; Pauses in <strong>PAUSED_FOR_REVIEW</strong> awaiting human approval.
          </li>
          <li>
            <strong className="text-emerald-600 dark:text-emerald-400">Guarded Run:</strong> Safely executes under
            Timeout Guard and records full Input/Output in the Audit Log.
          </li>
        </ol>
      </div>
    </div>
  );
};
