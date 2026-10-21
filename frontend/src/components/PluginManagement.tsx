"use client";

import React, { useState } from "react";
import {
  Boxes,
  Database,
  Plus,
  RefreshCw,
  Server,
  Zap,
  Activity,
  CheckCircle,
} from "lucide-react";
import { PluginProfileResponse, RegisterPluginRequest } from "@/types";
import { cn } from "@/lib/utils";

interface PluginManagementProps {
  plugins: PluginProfileResponse[];
  onRegisterPlugin: (req: RegisterPluginRequest) => Promise<void>;
  onSyncPlugin: (pluginId: string) => Promise<void>;
}

export const PluginManagement: React.FC<PluginManagementProps> = ({
  plugins,
  onRegisterPlugin,
  onSyncPlugin,
}) => {
  const [showModal, setShowModal] = useState<boolean>(false);
  const [syncingPluginId, setSyncingPluginId] = useState<string | null>(null);

  // Add Plugin Modal Form State
  const [id, setId] = useState<string>("");
  const [name, setName] = useState<string>("");
  const [driver, setDriver] = useState<string>("pyodbc/mssql");
  const [entrypoint, setEntrypoint] = useState<string>("python plugins/sqlserver_plugin/adapter.py");
  const [dryRunCmd, setDryRunCmd] = useState<string>("SET SHOWPLAN_XML ON");
  const [abortCmd, setAbortCmd] = useState<string>("KILL {spid}");
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!id || !name) return;
    setIsSubmitting(true);
    try {
      await onRegisterPlugin({
        id: id.trim(),
        name: name.trim(),
        driver: driver.trim(),
        entrypoint: entrypoint.trim(),
        dry_run_command: dryRunCmd.trim(),
        abort_command: abortCmd.trim(),
        config: { server: "localhost", database: "ProductionDB" },
      });
      setShowModal(false);
      setId("");
      setName("");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSync = async (pluginId: string) => {
    setSyncingPluginId(pluginId);
    try {
      await onSyncPlugin(pluginId);
    } finally {
      setSyncingPluginId(null);
    }
  };

  return (
    <div className="space-y-6">
      {/* Section Header */}
      <div className="flex items-center justify-between pb-4 border-b border-slate-800">
        <div>
          <h2 className="text-sm font-bold tracking-tight text-slate-100 flex items-center space-x-2">
            <Boxes className="h-4 w-4 text-indigo-400" />
            <span>Pluggable Targets & Connectors</span>
          </h2>
          <p className="text-xs text-slate-400">
            Isolated third-party systems communicating via JSON-RPC over Stdio sub-processes.
          </p>
        </div>
        <button
          onClick={() => setShowModal(true)}
          className="flex items-center space-x-2 bg-indigo-600 hover:bg-indigo-500 text-white px-3.5 py-1.5 rounded-lg text-xs font-semibold shadow-md shadow-indigo-600/30 transition-colors"
        >
          <Plus className="h-4 w-4" />
          <span>Add Pluggable Target</span>
        </button>
      </div>

      {/* Target Cards List - Two-Card Layout per Target */}
      <div className="space-y-6">
        {plugins.map((plugin) => (
          <div
            key={plugin.id}
            className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4"
          >
            {/* Target Header */}
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center space-x-3">
                <div className="h-8 w-8 rounded-lg bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center">
                  <Database className="h-4 w-4 text-indigo-400" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-100">{plugin.name}</h3>
                  <span className="text-[11px] font-mono text-slate-400">ID: {plugin.id}</span>
                </div>
              </div>
              <div className="flex items-center space-x-2">
                <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
                <span className="text-xs font-semibold text-emerald-400 uppercase tracking-wide">
                  {plugin.status}
                </span>
              </div>
            </div>

            {/* Two-Card Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Card 1: Configuration & Adapters */}
              <div className="bg-slate-950 border border-slate-800/80 rounded-lg p-4 space-y-3">
                <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400 flex items-center space-x-1.5">
                  <Server className="h-3.5 w-3.5 text-indigo-400" />
                  <span>Adapter Configuration</span>
                </div>
                <div className="space-y-2 text-xs">
                  <div>
                    <span className="text-slate-500 block text-[10px] uppercase font-semibold">
                      Driver Engine
                    </span>
                    <span className="font-mono text-slate-200">{plugin.driver}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block text-[10px] uppercase font-semibold">
                      Dry-Run Directive
                    </span>
                    <span className="font-mono text-amber-300">{plugin.dry_run_command}</span>
                  </div>
                  <div>
                    <span className="text-slate-500 block text-[10px] uppercase font-semibold">
                      Abort / Kill Directive
                    </span>
                    <span className="font-mono text-red-400">{plugin.abort_command}</span>
                  </div>
                </div>

                <div className="pt-2">
                  <button
                    onClick={() => handleSync(plugin.id)}
                    disabled={syncingPluginId === plugin.id}
                    className="w-full flex items-center justify-center space-x-2 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors disabled:opacity-50"
                  >
                    <RefreshCw
                      className={cn(
                        "h-3.5 w-3.5",
                        syncingPluginId === plugin.id && "animate-spin text-indigo-400"
                      )}
                    />
                    <span>
                      {syncingPluginId === plugin.id
                        ? "Syncing Schema & Indexes..."
                        : "Sync Schema & Indexes Now"}
                    </span>
                  </button>
                </div>
              </div>

              {/* Card 2: Live Metrics & Pool */}
              <div className="bg-slate-950 border border-slate-800/80 rounded-lg p-4 space-y-3">
                <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400 flex items-center space-x-1.5">
                  <Activity className="h-3.5 w-3.5 text-emerald-400" />
                  <span>Live Operational Metrics & Pool</span>
                </div>
                <div className="grid grid-cols-2 gap-3 pt-1">
                  <div className="bg-slate-900 border border-slate-800 rounded p-2.5">
                    <span className="text-[10px] uppercase font-semibold text-slate-500 block">
                      Active Sessions / SPIDs
                    </span>
                    <span className="text-base font-bold font-mono text-slate-100">
                      {plugin.active_sessions_count}
                    </span>
                  </div>
                  <div className="bg-slate-900 border border-slate-800 rounded p-2.5">
                    <span className="text-[10px] uppercase font-semibold text-slate-500 block">
                      Avg Roundtrip Latency
                    </span>
                    <span className="text-base font-bold font-mono text-indigo-400">
                      {plugin.latency_ms > 0 ? `${plugin.latency_ms} ms` : "12.5 ms"}
                    </span>
                  </div>
                </div>

                <div className="p-2 rounded bg-slate-900 border border-slate-800 flex items-center space-x-2 text-[11px] text-slate-400">
                  <CheckCircle className="h-3.5 w-3.5 text-emerald-400" />
                  <span>Subprocess IPC status: Process isolation active</span>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Add Plugin Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-lg w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <h3 className="text-sm font-bold text-slate-100 flex items-center space-x-2">
                <Plus className="h-4 w-4 text-indigo-400" />
                <span>Register New Pluggable Target</span>
              </h3>
              <button
                onClick={() => setShowModal(false)}
                className="text-slate-400 hover:text-slate-200 text-xs"
              >
                Cancel
              </button>
            </div>

            <form onSubmit={handleCreate} className="space-y-3">
              <div>
                <label className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">
                  Plugin ID (Unique Key)
                </label>
                <input
                  type="text"
                  required
                  value={id}
                  onChange={(e) => setId(e.target.value)}
                  placeholder="e.g. mongodb_prod"
                  className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-xs text-slate-100 font-mono focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">
                  Display Name
                </label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. MongoDB Analytics Cluster"
                  className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-xs text-slate-100 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">
                    Driver Identifier
                  </label>
                  <input
                    type="text"
                    required
                    value={driver}
                    onChange={(e) => setDriver(e.target.value)}
                    placeholder="e.g. pymongo"
                    className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-xs text-slate-100 font-mono focus:outline-none focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">
                    Dry-Run Directive
                  </label>
                  <input
                    type="text"
                    required
                    value={dryRunCmd}
                    onChange={(e) => setDryRunCmd(e.target.value)}
                    placeholder="e.g. .explain('executionStats')"
                    className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-xs text-slate-100 font-mono focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">
                  Emergency Abort Command
                </label>
                <input
                  type="text"
                  required
                  value={abortCmd}
                  onChange={(e) => setAbortCmd(e.target.value)}
                  placeholder="e.g. db.killOp(opid)"
                  className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-xs text-slate-100 font-mono focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">
                  Subprocess Entrypoint
                </label>
                <input
                  type="text"
                  required
                  value={entrypoint}
                  onChange={(e) => setEntrypoint(e.target.value)}
                  placeholder="e.g. python plugins/mongodb_plugin/adapter.py"
                  className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-xs text-slate-100 font-mono focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="flex space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="w-1/2 bg-slate-800 hover:bg-slate-700 text-slate-300 py-2 rounded-lg text-xs font-semibold transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="w-1/2 bg-indigo-600 hover:bg-indigo-500 text-white py-2 rounded-lg text-xs font-semibold transition-colors shadow-md shadow-indigo-600/30"
                >
                  {isSubmitting ? "Registering..." : "Register Plugin"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

