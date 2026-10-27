"use client";

import React, { memo } from "react";
import {
  Database,
  Sliders,
  RefreshCw,
  Zap,
  Trash2,
  ShieldCheck,
  AlertTriangle,
  Server,
  Layers,
} from "lucide-react";
import { PluginProfileResponse } from "@/types";
import { cn } from "@/lib/utils";
import { Badge } from "@/shared/ui/Badge";

export interface PluginCardProps {
  plugin: PluginProfileResponse;
  verifyingId: string | null;
  syncingId: string | null;
  onRunSanityCheck: (id: string) => void;
  onOpenEdit: (plugin: PluginProfileResponse) => void;
  onSync: (id: string) => void;
  onViewMcpConfig?: (plugin: PluginProfileResponse) => void;
  onOpenUninstall: (plugin: PluginProfileResponse) => void;
  onInspectCert: (plugin: PluginProfileResponse) => void;
}

export const PluginCard = memo<PluginCardProps>(function PluginCard({
  plugin,
  verifyingId,
  syncingId,
  onRunSanityCheck,
  onOpenEdit,
  onSync,
  onViewMcpConfig,
  onOpenUninstall,
  onInspectCert,
}) {
  const isVerifying = verifyingId === plugin.id;
  const isSyncing = syncingId === plugin.id;

  return (
    <div
      data-testid={`plugin-card-${plugin.id}`}
      className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 shadow-sm space-y-4 hover:border-slate-300 dark:hover:border-slate-700 transition-all"
    >
      {/* Plugin Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-start space-x-3">
          <div className="h-10 w-10 rounded-xl bg-indigo-50 dark:bg-indigo-600/10 border border-indigo-200 dark:border-indigo-500/20 flex items-center justify-center flex-shrink-0 mt-0.5">
            <Database className="h-5 w-5 text-indigo-600 dark:text-indigo-400" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100">
                {plugin.name}
              </h3>
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 font-semibold">
                #{plugin.id}
              </span>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5 font-mono">
              Driver: {plugin.driver}
            </p>
          </div>
        </div>

        {/* Live Status Badge */}
        <Badge variant={plugin.status === "active" ? "success" : "neutral"} size="sm" dot>
          {plugin.status === "active" ? "ACTIVE" : plugin.status.toUpperCase()}
        </Badge>
      </div>

      {/* Certification Pill */}
      <div className="flex items-center justify-between text-xs pt-1">
        <button
          type="button"
          data-testid={`cert-badge-${plugin.id}`}
          onClick={() => onInspectCert(plugin)}
          className={cn(
            "flex items-center space-x-1.5 px-2.5 py-1 rounded-lg border text-xs font-semibold transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500",
            plugin.is_certified
              ? "bg-emerald-50 dark:bg-emerald-500/10 text-emerald-800 dark:text-emerald-400 border-emerald-300 dark:border-emerald-500/30 hover:bg-emerald-100"
              : "bg-amber-50 dark:bg-amber-500/10 text-amber-800 dark:text-amber-400 border-amber-300 dark:border-amber-500/30 hover:bg-amber-100"
          )}
          title="Click to view 4-stage sanity linter checklist details"
        >
          {plugin.is_certified ? (
            <ShieldCheck className="h-3.5 w-3.5" />
          ) : (
            <AlertTriangle className="h-3.5 w-3.5" />
          )}
          <span>{plugin.is_certified ? "Certified & Ready" : "Uncertified"}</span>
        </button>

        <span className="text-[11px] text-slate-500 dark:text-slate-400 font-mono">
          Pool: {plugin.active_sessions_count} SPIDs
        </span>
      </div>

      {/* Configuration Summary */}
      <div className="bg-slate-50 dark:bg-slate-950/60 border border-slate-200 dark:border-slate-800 rounded-lg p-3 space-y-1.5 text-xs font-mono">
        <div className="flex justify-between">
          <span className="text-slate-500 dark:text-slate-400">Server:</span>
          <span className="text-slate-800 dark:text-slate-200 font-semibold truncate max-w-[200px]">
            {String(plugin.config?.server || "localhost")}
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-500 dark:text-slate-400">Database:</span>
          <span className="text-slate-800 dark:text-slate-200 font-semibold truncate max-w-[200px]">
            {String(plugin.config?.database || "master")}
          </span>
        </div>
        <div className="flex justify-between">
          <span className="text-slate-500 dark:text-slate-400">Latency:</span>
          <span className="text-emerald-700 dark:text-emerald-400 font-semibold">
            {plugin.latency_ms} ms
          </span>
        </div>
      </div>

      {/* Optional Dialect-Specific Custom Card */}
      {plugin.custom_card && (
        <div className="bg-slate-50 dark:bg-slate-950/60 border border-slate-200 dark:border-slate-800 rounded-lg p-3 space-y-2">
          <div className="flex items-center justify-between pb-1.5 border-b border-slate-200 dark:border-slate-800">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300">
              {plugin.custom_card.title}
            </span>
            <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border border-indigo-500/20 font-semibold">
              {plugin.custom_card.badge}
            </span>
          </div>

          {plugin.custom_card.sample_data && plugin.custom_card.sample_data.length > 0 && (
            <div className="overflow-x-auto max-h-28">
              <table className="w-full text-left text-[10px] border-collapse">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-slate-800 text-slate-500 dark:text-slate-400">
                    {(
                      plugin.custom_card.columns ||
                      Object.keys(plugin.custom_card.sample_data[0] || {})
                    ).map((col) => (
                      <th key={col} className="py-1 px-1.5 font-semibold">
                        {col}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 dark:divide-slate-800/60 font-mono text-slate-700 dark:text-slate-300">
                  {plugin.custom_card.sample_data.map((row, idx) => (
                    <tr key={idx}>
                      {Object.values(row).map((val, cellIdx) => (
                        <td key={cellIdx} className="py-1 px-1.5">
                          {String(val)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Action Buttons */}
      <div className="pt-2 border-t border-slate-200 dark:border-slate-800/80 space-y-2">
        <div className="grid grid-cols-2 gap-2">
          {/* Sanity Check */}
          <button
            type="button"
            data-testid={`sanity-check-btn-${plugin.id}`}
            onClick={() => onRunSanityCheck(plugin.id)}
            disabled={isVerifying}
            className="flex items-center justify-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-100 hover:bg-slate-200 text-slate-800 dark:bg-slate-800 dark:hover:bg-slate-750 dark:text-slate-100 border border-slate-300 dark:border-slate-700 transition-colors disabled:opacity-50 shadow-xs focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
          >
            <RefreshCw
              className={cn("h-3.5 w-3.5", isVerifying && "animate-spin text-indigo-500")}
            />
            <span>{isVerifying ? "Testing..." : "Sanity Check"}</span>
          </button>

          {/* Edit Configuration */}
          <button
            type="button"
            data-testid={`edit-btn-${plugin.id}`}
            onClick={() => onOpenEdit(plugin)}
            className="flex items-center justify-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-indigo-50 hover:bg-indigo-100 text-indigo-700 border border-indigo-200 dark:bg-indigo-600/20 dark:hover:bg-indigo-600/30 dark:text-indigo-300 dark:border-indigo-500/30 transition-colors shadow-xs focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
          >
            <Sliders className="h-3.5 w-3.5" />
            <span>Edit Configuration</span>
          </button>
        </div>

        <div className="grid grid-cols-3 gap-2">
          {/* Sync Schema */}
          <button
            type="button"
            onClick={() => onSync(plugin.id)}
            disabled={isSyncing}
            className="flex items-center justify-center space-x-1 bg-slate-100 hover:bg-slate-200 text-slate-800 dark:bg-slate-800 dark:hover:bg-slate-750 dark:text-slate-100 border border-slate-300 dark:border-slate-700 px-2 py-1.5 rounded-lg text-[11px] font-semibold transition-colors disabled:opacity-50 shadow-xs focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
          >
            <RefreshCw className={cn("h-3 w-3", isSyncing && "animate-spin text-indigo-500")} />
            <span>{isSyncing ? "Syncing..." : "Sync Schema"}</span>
          </button>

          {/* MCP Config Snippet */}
          <button
            type="button"
            data-testid={`mcp-btn-${plugin.id}`}
            onClick={() => onViewMcpConfig?.(plugin)}
            className="flex items-center justify-center space-x-1 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 border border-indigo-200 dark:bg-indigo-950/60 dark:hover:bg-indigo-900/60 dark:text-indigo-300 dark:border-indigo-800/80 px-2 py-1.5 rounded-lg text-[11px] font-semibold transition-colors shadow-xs focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
          >
            <Zap className="h-3 w-3" />
            <span>MCP Config</span>
          </button>

          {/* Uninstall */}
          <button
            type="button"
            data-testid={`uninstall-btn-${plugin.id}`}
            onClick={() => onOpenUninstall(plugin)}
            className="flex items-center justify-center space-x-1 bg-slate-100 hover:bg-rose-50 text-slate-700 hover:text-rose-700 border border-slate-300 hover:border-rose-300 dark:bg-slate-800 dark:hover:bg-rose-500/10 dark:text-slate-300 dark:hover:text-rose-400 dark:border-slate-700 dark:hover:border-rose-500/30 px-2 py-1.5 rounded-lg text-[11px] font-semibold transition-colors shadow-xs focus:outline-none focus-visible:ring-2 focus-visible:ring-rose-500"
          >
            <Trash2 className="h-3 w-3" />
            <span>Uninstall</span>
          </button>
        </div>
      </div>
    </div>
  );
});
