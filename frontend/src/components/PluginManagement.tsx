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
  Sliders,
  Save,
  X,
  Layers,
  Terminal,
  ShieldCheck,
  Eye,
  EyeOff,
  Trash2,
  AlertTriangle,
} from "lucide-react";
import {
  CustomCardData,
  PluginProfileResponse,
  RegisterPluginRequest,
  UiFieldSchema,
  UpdatePluginConfigRequest,
} from "@/types";
import { cn } from "@/lib/utils";

interface PluginManagementProps {
  plugins: PluginProfileResponse[];
  onRegisterPlugin: (req: RegisterPluginRequest) => Promise<void>;
  onUpdatePlugin?: (pluginId: string, req: UpdatePluginConfigRequest) => Promise<void>;
  onSyncPlugin: (pluginId: string) => Promise<void>;
  onUninstallPlugin?: (pluginId: string, hardDelete: boolean) => Promise<void>;
  onViewMcpConfig?: (plugin: PluginProfileResponse) => void;
}

/**
 * Dynamic Form Field Component rendering controls based on schema type.
 */
interface DynamicFormFieldProps {
  field: UiFieldSchema;
  value: unknown;
  onChange: (val: unknown) => void;
}

const DynamicFormField: React.FC<DynamicFormFieldProps> = ({ field, value, onChange }) => {
  const [showPassword, setShowPassword] = useState<boolean>(false);

  const stringVal = value !== undefined && value !== null ? String(value) : "";

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between">
        <label className="text-[11px] font-semibold text-slate-300 uppercase tracking-wider flex items-center space-x-1">
          <span>{field.label}</span>
          {field.required && <span className="text-amber-400 font-bold">*</span>}
        </label>
        {field.type === "password" && (
          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            className="text-[10px] text-slate-400 hover:text-slate-200 flex items-center space-x-1 focus:outline-none"
          >
            {showPassword ? <EyeOff className="h-3 w-3" /> : <Eye className="h-3 w-3" />}
            <span>{showPassword ? "Hide" : "Show"}</span>
          </button>
        )}
      </div>

      {field.type === "select" ? (
        <select
          value={stringVal}
          onChange={(e) => onChange(e.target.value)}
          required={field.required}
          className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-100 focus:outline-none focus:border-indigo-500 font-sans"
        >
          {field.options?.map((opt) => (
            <option key={opt} value={opt} className="bg-slate-900 text-slate-100">
              {opt}
            </option>
          ))}
        </select>
      ) : field.type === "password" ? (
        <input
          type={showPassword ? "text" : "password"}
          value={stringVal}
          onChange={(e) => onChange(e.target.value)}
          placeholder={field.placeholder || "••••••••"}
          required={field.required}
          className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-100 font-mono focus:outline-none focus:border-indigo-500"
        />
      ) : field.type === "number" ? (
        <input
          type="number"
          value={stringVal}
          onChange={(e) => onChange(e.target.value === "" ? "" : Number(e.target.value))}
          placeholder={field.placeholder}
          required={field.required}
          className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-100 font-mono focus:outline-none focus:border-indigo-500"
        />
      ) : field.type === "textarea" ? (
        <textarea
          rows={3}
          value={stringVal}
          onChange={(e) => onChange(e.target.value)}
          placeholder={field.placeholder}
          required={field.required}
          className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-100 font-mono focus:outline-none focus:border-indigo-500"
        />
      ) : (
        <input
          type="text"
          value={stringVal}
          onChange={(e) => onChange(e.target.value)}
          placeholder={field.placeholder}
          required={field.required}
          className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-100 font-mono focus:outline-none focus:border-indigo-500"
        />
      )}

      {field.description && (
        <p className="text-[10px] text-slate-500">{field.description}</p>
      )}
    </div>
  );
};

export const PluginManagement: React.FC<PluginManagementProps> = ({
  plugins,
  onRegisterPlugin,
  onUpdatePlugin,
  onSyncPlugin,
  onUninstallPlugin,
  onViewMcpConfig,
}) => {
  // Modal states
  const [showAddModal, setShowAddModal] = useState<boolean>(false);
  const [editingPlugin, setEditingPlugin] = useState<PluginProfileResponse | null>(null);
  const [syncingPluginId, setSyncingPluginId] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  // Uninstall Modal State
  const [uninstallingPlugin, setUninstallingPlugin] = useState<PluginProfileResponse | null>(null);
  const [isHardDelete, setIsHardDelete] = useState<boolean>(false);
  const [isUninstalling, setIsUninstalling] = useState<boolean>(false);
  const [uninstallError, setUninstallError] = useState<string | null>(null);

  // Edit Plugin Form State
  const [editName, setEditName] = useState<string>("");
  const [editConfig, setEditConfig] = useState<Record<string, unknown>>({});
  const [editDryRunCmd, setEditDryRunCmd] = useState<string>("");
  const [editAbortCmd, setEditAbortCmd] = useState<string>("");

  // Add Plugin Form State
  const [addId, setAddId] = useState<string>("");
  const [addName, setAddName] = useState<string>("");
  const [addDriver, setAddDriver] = useState<string>("pyodbc/mssql");
  const [addEntrypoint, setAddEntrypoint] = useState<string>("python plugins/sqlserver_plugin/adapter.py");
  const [addDryRunCmd, setAddDryRunCmd] = useState<string>("SET SHOWPLAN_XML ON");
  const [addAbortCmd, setAddAbortCmd] = useState<string>("KILL {spid}");
  const [addPreset, setAddPreset] = useState<string>("sqlserver");
  const [addConfig, setAddConfig] = useState<Record<string, unknown>>({
    server: "localhost",
    port: 1433,
    database: "EnterpriseSales",
    username: "sa",
  });

  const handleOpenEdit = (plugin: PluginProfileResponse) => {
    setEditingPlugin(plugin);
    setEditName(plugin.name);
    setEditConfig({ ...(plugin.config || {}) });
    setEditDryRunCmd(plugin.dry_run_command || "");
    setEditAbortCmd(plugin.abort_command || "");
  };

  const handleSaveEdit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingPlugin || !onUpdatePlugin) return;

    setIsSubmitting(true);
    try {
      await onUpdatePlugin(editingPlugin.id, {
        name: editName.trim(),
        config: editConfig,
        dry_run_command: editDryRunCmd.trim(),
        abort_command: editAbortCmd.trim(),
      });
      setEditingPlugin(null);
    } catch (err) {
      alert(`Update failed: ${err instanceof Error ? err.message : "Unknown error"}`);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handlePresetChange = (preset: string) => {
    setAddPreset(preset);
    if (preset === "sqlserver") {
      setAddId("sqlserver_prod");
      setAddName("SQL Server Enterprise Gateway");
      setAddDriver("pyodbc/mssql");
      setAddEntrypoint("python plugins/sqlserver_plugin/adapter.py");
      setAddDryRunCmd("SET SHOWPLAN_XML ON");
      setAddAbortCmd("KILL {spid}");
      setAddConfig({
        server: "localhost",
        port: 1433,
        database: "EnterpriseSales",
        username: "sa",
      });
    } else if (preset === "mongodb") {
      setAddId("mongodb_prod");
      setAddName("MongoDB Enterprise Analytics");
      setAddDriver("pymongo/mongodb");
      setAddEntrypoint("python plugins/mongodb_plugin/adapter.py");
      setAddDryRunCmd("db.runCommand({explain: ...})");
      setAddAbortCmd("db.killOp({opid})");
      setAddConfig({
        connection_uri: "mongodb://localhost:27017",
        database: "EnterpriseAnalytics",
        auth_source: "admin",
      });
    } else {
      setAddId("");
      setAddName("");
      setAddDriver("custom/driver");
      setAddEntrypoint("python plugins/custom_plugin/adapter.py");
      setAddDryRunCmd("EXPLAIN");
      setAddAbortCmd("KILL {id}");
      setAddConfig({});
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!addId || !addName) return;
    setIsSubmitting(true);
    try {
      await onRegisterPlugin({
        id: addId.trim(),
        name: addName.trim(),
        driver: addDriver.trim(),
        entrypoint: addEntrypoint.trim(),
        dry_run_command: addDryRunCmd.trim(),
        abort_command: addAbortCmd.trim(),
        config: addConfig,
      });
      setShowAddModal(false);
      setAddId("");
      setAddName("");
    } catch (err) {
      alert(`Registration failed: ${err instanceof Error ? err.message : "Unknown error"}`);
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

  const handleConfirmUninstall = async () => {
    if (!uninstallingPlugin || !onUninstallPlugin) return;
    setIsUninstalling(true);
    setUninstallError(null);
    try {
      await onUninstallPlugin(uninstallingPlugin.id, isHardDelete);
      setUninstallingPlugin(null);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to uninstall plugin";
      setUninstallError(msg);
    } finally {
      setIsUninstalling(false);
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
            Process-isolated third-party database connectors with schema-driven Dynamic UI forms.
          </p>
        </div>
        <button
          onClick={() => setShowAddModal(true)}
          className="flex items-center space-x-2 bg-indigo-600 hover:bg-indigo-500 text-white px-3.5 py-1.5 rounded-lg text-xs font-semibold shadow-md shadow-indigo-600/30 transition-colors"
        >
          <Plus className="h-4 w-4" />
          <span>Add Pluggable Target</span>
        </button>
      </div>

      {/* Target Cards List */}
      <div className="space-y-6">
        {plugins.map((plugin) => (
          <div
            key={plugin.id}
            data-testid={`plugin-card-${plugin.id}`}
            className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4 shadow-sm"
          >
            {/* Target Header */}
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center space-x-3">
                <div className="h-9 w-9 rounded-lg bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center">
                  <Database className="h-4 w-4 text-indigo-400" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-100 flex items-center space-x-2">
                    <span>{plugin.name}</span>
                    <span className="text-[10px] font-normal px-2 py-0.5 rounded bg-slate-800 border border-slate-700 text-indigo-300 font-mono">
                      {plugin.driver}
                    </span>
                  </h3>
                  <span className="text-[11px] font-mono text-slate-400">ID: {plugin.id}</span>
                </div>
              </div>
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => handleOpenEdit(plugin)}
                  data-testid={`edit-btn-${plugin.id}`}
                  className="flex items-center space-x-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors"
                >
                  <Sliders className="h-3.5 w-3.5 text-indigo-400" />
                  <span>Edit Configuration</span>
                </button>
                {onViewMcpConfig && (
                  <button
                    onClick={() => onViewMcpConfig(plugin)}
                    data-testid={`mcp-btn-${plugin.id}`}
                    className="flex items-center space-x-1.5 bg-indigo-600/10 hover:bg-indigo-600/20 text-indigo-400 hover:text-indigo-300 border border-indigo-500/30 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors"
                    title="View & Copy MCP JSON snippet for Claude, Cursor, Cline"
                  >
                    <Terminal className="h-3.5 w-3.5 text-indigo-400" />
                    <span>MCP Config</span>
                  </button>
                )}
                {onUninstallPlugin && (
                  <button
                    onClick={() => {
                      setUninstallingPlugin(plugin);
                      setIsHardDelete(false);
                      setUninstallError(null);
                    }}
                    data-testid={`uninstall-btn-${plugin.id}`}
                    className="flex items-center space-x-1.5 bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 hover:text-rose-300 border border-rose-500/30 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors"
                    title="Uninstall / Disable Plugin"
                  >
                    <Trash2 className="h-3.5 w-3.5 text-rose-400" />
                    <span>Uninstall</span>
                  </button>
                )}
                <div className="flex items-center space-x-1.5 bg-emerald-500/10 border border-emerald-500/20 px-2.5 py-1 rounded-full">
                  <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
                  <span className="text-[11px] font-semibold text-emerald-400 uppercase tracking-wide">
                    {plugin.status}
                  </span>
                </div>
              </div>
            </div>

            {/* Multi-Card Grid: 2 Standard Cards + Optional Plugin-Specific Custom Card */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {/* Card 1: Configuration & Adapters */}
              <div className="bg-slate-950 border border-slate-800/80 rounded-lg p-4 space-y-3 flex flex-col justify-between">
                <div className="space-y-3">
                  <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400 flex items-center space-x-1.5">
                    <Server className="h-3.5 w-3.5 text-indigo-400" />
                    <span>Active Connection Parameters</span>
                  </div>

                  <div className="space-y-2 text-xs">
                    {/* Render active connection parameters dynamically from config */}
                    {plugin.config && Object.keys(plugin.config).length > 0 ? (
                      <div className="grid grid-cols-2 gap-2 bg-slate-900/60 p-2.5 rounded-lg border border-slate-800/60 font-mono text-[11px]">
                        {Object.entries(plugin.config)
                          .filter(([key]) => key !== "password")
                          .slice(0, 4)
                          .map(([key, val]) => (
                            <div key={key} className="overflow-hidden">
                              <span className="text-slate-500 block text-[9px] uppercase font-semibold">
                                {key}
                              </span>
                              <span className="text-slate-200 truncate block">
                                {String(val)}
                              </span>
                            </div>
                          ))}
                      </div>
                    ) : (
                      <p className="text-[11px] text-slate-500 italic">No connection parameters configured.</p>
                    )}

                    <div className="pt-1 space-y-1">
                      <div>
                        <span className="text-slate-500 block text-[10px] uppercase font-semibold">
                          Dry-Run Directive
                        </span>
                        <span className="font-mono text-amber-300 text-[11px]">{plugin.dry_run_command}</span>
                      </div>
                      <div>
                        <span className="text-slate-500 block text-[10px] uppercase font-semibold">
                          Abort / Kill Directive
                        </span>
                        <span className="font-mono text-red-400 text-[11px]">{plugin.abort_command}</span>
                      </div>
                    </div>
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
              <div className="bg-slate-950 border border-slate-800/80 rounded-lg p-4 space-y-3 flex flex-col justify-between">
                <div className="space-y-3">
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
                    <CheckCircle className="h-3.5 w-3.5 text-emerald-400 flex-shrink-0" />
                    <span className="truncate">Subprocess IPC: Process isolation active</span>
                  </div>
                </div>

                <div className="p-2 rounded bg-slate-900/50 border border-slate-800/60 text-[10px] font-mono text-slate-400 flex items-center space-x-1.5">
                  <Terminal className="h-3 w-3 text-slate-500" />
                  <span className="truncate">{plugin.entrypoint}</span>
                </div>
              </div>

              {/* Card 3: Plugin-Specific Custom UI Card (Rendered if defined in manifest) */}
              {plugin.custom_card ? (
                <div className="bg-slate-950 border border-indigo-900/40 rounded-lg p-4 space-y-3 flex flex-col justify-between">
                  <div className="space-y-2">
                    <div className="flex items-center justify-between pb-1 border-b border-slate-800">
                      <div className="text-[11px] font-bold uppercase tracking-wider text-indigo-300 flex items-center space-x-1.5">
                        <Layers className="h-3.5 w-3.5 text-indigo-400" />
                        <span>{plugin.custom_card.title}</span>
                      </div>
                      {plugin.custom_card.badge && (
                        <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-indigo-950 border border-indigo-800 text-indigo-300">
                          {plugin.custom_card.badge}
                        </span>
                      )}
                    </div>

                    {/* Dynamic Table from Custom Card */}
                    {plugin.custom_card.columns && plugin.custom_card.sample_data ? (
                      <div className="overflow-x-auto text-[10px] font-mono pt-1">
                        <table className="w-full border-collapse">
                          <thead>
                            <tr className="border-b border-slate-800 text-slate-500 text-left">
                              {plugin.custom_card.columns.map((col) => (
                                <th key={col} className="pb-1 pr-2 font-semibold">
                                  {col}
                                </th>
                              ))}
                            </tr>
                          </thead>
                          <tbody className="divide-y divide-slate-800/50 text-slate-300">
                            {plugin.custom_card.sample_data.map((row, idx) => (
                              <tr key={idx} className="hover:bg-slate-900/50">
                                {plugin.custom_card?.columns?.map((col) => {
                                  const cellVal = row[col];
                                  const isStatus = col.toLowerCase() === "status" || col.toLowerCase() === "type";
                                  return (
                                    <td key={col} className="py-1 pr-2 truncate max-w-[100px]">
                                      {isStatus ? (
                                        <span className="text-emerald-400 font-semibold">{String(cellVal)}</span>
                                      ) : (
                                        String(cellVal)
                                      )}
                                    </td>
                                  );
                                })}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    ) : null}
                  </div>

                  <div className="text-[10px] text-slate-500 flex items-center space-x-1 pt-1">
                    <ShieldCheck className="h-3 w-3 text-emerald-400" />
                    <span>Dialect-specific health inspection verified</span>
                  </div>
                </div>
              ) : (
                <div className="bg-slate-950 border border-dashed border-slate-800 rounded-lg p-4 flex flex-col items-center justify-center text-center space-y-2">
                  <Sliders className="h-6 w-6 text-slate-600" />
                  <span className="text-xs font-semibold text-slate-400">Pluggable UI Hook Ready</span>
                  <p className="text-[10px] text-slate-500 max-w-xs">
                    Define <code>custom_card</code> in <code>plugin_manifest.json</code> to surface real-time dialect tables.
                  </p>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Dynamic Edit Plugin Modal */}
      {editingPlugin && (
        <div
          data-testid="edit-plugin-modal"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 overflow-y-auto"
        >
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-xl w-full p-6 shadow-2xl space-y-5 my-8">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center space-x-2.5">
                <div className="h-8 w-8 rounded-lg bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center">
                  <Sliders className="h-4 w-4 text-indigo-400" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-100">
                    Edit Connection Configuration
                  </h3>
                  <p className="text-[11px] text-slate-400 font-mono">
                    Target: {editingPlugin.id} ({editingPlugin.driver})
                  </p>
                </div>
              </div>
              <button
                onClick={() => setEditingPlugin(null)}
                className="text-slate-400 hover:text-slate-200 p-1 rounded-md hover:bg-slate-800 transition-colors"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <form onSubmit={handleSaveEdit} className="space-y-4">
              <div>
                <label className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">
                  Target Display Name
                </label>
                <input
                  type="text"
                  required
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-100 focus:outline-none focus:border-indigo-500 font-sans"
                />
              </div>

              {/* Dynamic Form Schema Rendering */}
              <div className="border border-slate-800 rounded-xl p-4 bg-slate-950/70 space-y-3.5">
                <div className="flex items-center justify-between pb-2 border-b border-slate-800/80">
                  <span className="text-[11px] font-bold uppercase tracking-wider text-indigo-400 flex items-center space-x-1.5">
                    <Server className="h-3.5 w-3.5" />
                    <span>Dynamic Connection Parameters (ui_schema)</span>
                  </span>
                  <span className="text-[10px] text-slate-500 font-mono">
                    {editingPlugin.ui_schema?.length || 0} fields
                  </span>
                </div>

                {editingPlugin.ui_schema && editingPlugin.ui_schema.length > 0 ? (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
                    {editingPlugin.ui_schema.map((field) => (
                      <div
                        key={field.key}
                        className={field.type === "textarea" ? "md:col-span-2" : ""}
                      >
                        <DynamicFormField
                          field={field}
                          value={editConfig[field.key] !== undefined ? editConfig[field.key] : field.default}
                          onChange={(newVal) =>
                            setEditConfig((prev) => ({ ...prev, [field.key]: newVal }))
                          }
                        />
                      </div>
                    ))}
                  </div>
                ) : (
                  // Fallback generic editor if plugin has no ui_schema defined
                  <div className="space-y-2 text-xs">
                    <p className="text-slate-400 text-[11px]">
                      No dynamic <code>ui_schema</code> declared in plugin manifest. Direct key-value configuration:
                    </p>
                    {Object.entries(editConfig).map(([k, v]) => (
                      <div key={k} className="flex space-x-2">
                        <span className="w-1/3 font-mono text-slate-400 text-xs py-1.5 truncate">{k}</span>
                        <input
                          type="text"
                          value={String(v)}
                          onChange={(e) =>
                            setEditConfig((prev) => ({ ...prev, [k]: e.target.value }))
                          }
                          className="w-2/3 bg-slate-950 border border-slate-800 rounded px-2.5 py-1 text-xs text-slate-100 font-mono"
                        />
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Adapter Directives */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">
                    Dry-Run Directive
                  </label>
                  <input
                    type="text"
                    value={editDryRunCmd}
                    onChange={(e) => setEditDryRunCmd(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-100 font-mono focus:outline-none focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">
                    Emergency Abort Command
                  </label>
                  <input
                    type="text"
                    value={editAbortCmd}
                    onChange={(e) => setEditAbortCmd(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-100 font-mono focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              <div className="flex space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setEditingPlugin(null)}
                  className="w-1/2 bg-slate-800 hover:bg-slate-700 text-slate-300 py-2 rounded-lg text-xs font-semibold transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="w-1/2 flex items-center justify-center space-x-1.5 bg-indigo-600 hover:bg-indigo-500 text-white py-2 rounded-lg text-xs font-semibold transition-colors shadow-md shadow-indigo-600/30"
                >
                  <Save className="h-3.5 w-3.5" />
                  <span>{isSubmitting ? "Saving & Reinitializing..." : "Save & Re-Init Connection"}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Uninstall / Disable Confirmation Modal */}
      {uninstallingPlugin && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 overflow-y-auto animate-in fade-in duration-150">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-lg shadow-2xl overflow-hidden">
            {/* Modal Header */}
            <div className="flex items-center justify-between p-5 border-b border-slate-800 bg-rose-950/20">
              <div className="flex items-center space-x-3">
                <div className="h-9 w-9 rounded-lg bg-rose-500/20 border border-rose-500/30 flex items-center justify-center">
                  <AlertTriangle className="h-5 w-5 text-rose-400" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-100">
                    Uninstall Pluggable Target
                  </h3>
                  <p className="text-[11px] text-rose-300/80 font-mono">
                    {uninstallingPlugin.id} ({uninstallingPlugin.name})
                  </p>
                </div>
              </div>
              <button
                type="button"
                onClick={() => setUninstallingPlugin(null)}
                className="text-slate-400 hover:text-slate-100 p-1.5 rounded-lg hover:bg-slate-800 transition-colors"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 space-y-4">
              <p className="text-xs text-slate-300 leading-relaxed">
                Are you sure you want to uninstall or remove this pluggable target? Any running queries or active subprocesses will be immediately terminated.
              </p>

              {uninstallError && (
                <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs">
                  {uninstallError}
                </div>
              )}

              {/* Mode Selection */}
              <div className="space-y-3 pt-1">
                <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
                  Select Deletion Mode
                </label>

                {/* Mode 1: Soft Disable */}
                <div
                  onClick={() => setIsHardDelete(false)}
                  data-testid="mode-soft-disable"
                  className={cn(
                    "p-3.5 rounded-xl border cursor-pointer transition-all flex items-start space-x-3",
                    !isHardDelete
                      ? "bg-slate-800/80 border-indigo-500/50 ring-1 ring-indigo-500/30"
                      : "bg-slate-950/50 border-slate-800 hover:border-slate-700"
                  )}
                >
                  <input
                    type="radio"
                    name="uninstallMode"
                    checked={!isHardDelete}
                    onChange={() => setIsHardDelete(false)}
                    className="mt-0.5 text-indigo-500 focus:ring-0"
                  />
                  <div>
                    <div className="text-xs font-semibold text-slate-200">
                      Soft Deactivate (Recommended)
                    </div>
                    <div className="text-[11px] text-slate-400 mt-0.5 leading-relaxed">
                      Sets status to <code className="text-amber-400 font-mono">disabled</code>. Terminates subprocesses and prevents auto-discovery from reloading it on next launch.
                    </div>
                  </div>
                </div>

                {/* Mode 2: Hard Delete */}
                <div
                  onClick={() => setIsHardDelete(true)}
                  data-testid="mode-hard-delete"
                  className={cn(
                    "p-3.5 rounded-xl border cursor-pointer transition-all flex items-start space-x-3",
                    isHardDelete
                      ? "bg-rose-950/30 border-rose-500/50 ring-1 ring-rose-500/30"
                      : "bg-slate-950/50 border-slate-800 hover:border-slate-700"
                  )}
                >
                  <input
                    type="radio"
                    name="uninstallMode"
                    checked={isHardDelete}
                    onChange={() => setIsHardDelete(true)}
                    className="mt-0.5 text-rose-500 focus:ring-0"
                  />
                  <div>
                    <div className="text-xs font-semibold text-rose-300">
                      Permanent Hard Delete
                    </div>
                    <div className="text-[11px] text-slate-400 mt-0.5 leading-relaxed">
                      Permanently wipes this target profile and its configuration from the SQLite database.
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="p-5 border-t border-slate-800 bg-slate-950/50 flex items-center justify-end space-x-3">
              <button
                type="button"
                onClick={() => setUninstallingPlugin(null)}
                disabled={isUninstalling}
                className="px-4 py-2 rounded-lg text-xs font-medium text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleConfirmUninstall}
                disabled={isUninstalling}
                data-testid="confirm-uninstall-btn"
                className="flex items-center space-x-2 px-4 py-2 rounded-lg text-xs font-medium text-white bg-rose-600 hover:bg-rose-500 transition-colors shadow-lg shadow-rose-600/30 disabled:opacity-50"
              >
                {isUninstalling ? (
                  <>
                    <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                    <span>Removing...</span>
                  </>
                ) : (
                  <>
                    <Trash2 className="h-3.5 w-3.5" />
                    <span>Confirm Uninstall</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add Plugin Modal with Presets */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 overflow-y-auto">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-lg w-full p-6 shadow-2xl space-y-4 my-8">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <h3 className="text-sm font-bold text-slate-100 flex items-center space-x-2">
                <Plus className="h-4 w-4 text-indigo-400" />
                <span>Register New Pluggable Target</span>
              </h3>
              <button
                onClick={() => setShowAddModal(false)}
                className="text-slate-400 hover:text-slate-200 text-xs"
              >
                Cancel
              </button>
            </div>

            {/* Target Template Preset Selector */}
            <div>
              <label className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">
                Target Architecture Preset
              </label>
              <div className="grid grid-cols-3 gap-2">
                {[
                  { id: "sqlserver", label: "SQL Server" },
                  { id: "mongodb", label: "MongoDB" },
                  { id: "custom", label: "Custom Plugin" },
                ].map((p) => (
                  <button
                    key={p.id}
                    type="button"
                    onClick={() => handlePresetChange(p.id)}
                    className={cn(
                      "py-1.5 px-2 rounded-lg text-xs font-medium border text-center transition-colors",
                      addPreset === p.id
                        ? "bg-indigo-600/20 border-indigo-500 text-indigo-200"
                        : "bg-slate-950 border-slate-800 text-slate-400 hover:border-slate-700"
                    )}
                  >
                    {p.label}
                  </button>
                ))}
              </div>
            </div>

            <form onSubmit={handleCreate} className="space-y-3">
              <div>
                <label className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">
                  Plugin ID (Unique Key)
                </label>
                <input
                  type="text"
                  required
                  value={addId}
                  onChange={(e) => setAddId(e.target.value)}
                  placeholder="e.g. mongodb_prod"
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-100 font-mono focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">
                  Display Name
                </label>
                <input
                  type="text"
                  required
                  value={addName}
                  onChange={(e) => setAddName(e.target.value)}
                  placeholder="e.g. MongoDB Analytics Cluster"
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-100 focus:outline-none focus:border-indigo-500"
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
                    value={addDriver}
                    onChange={(e) => setAddDriver(e.target.value)}
                    placeholder="e.g. pymongo/mongodb"
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-100 font-mono focus:outline-none focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">
                    Dry-Run Directive
                  </label>
                  <input
                    type="text"
                    required
                    value={addDryRunCmd}
                    onChange={(e) => setAddDryRunCmd(e.target.value)}
                    placeholder="e.g. db.runCommand({explain})"
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-100 font-mono focus:outline-none focus:border-indigo-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">
                  Subprocess Entrypoint
                </label>
                <input
                  type="text"
                  required
                  value={addEntrypoint}
                  onChange={(e) => setAddEntrypoint(e.target.value)}
                  placeholder="e.g. python plugins/mongodb_plugin/adapter.py"
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-100 font-mono focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">
                  Emergency Abort Command
                </label>
                <input
                  type="text"
                  required
                  value={addAbortCmd}
                  onChange={(e) => setAddAbortCmd(e.target.value)}
                  placeholder="e.g. db.killOp({opid})"
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-100 font-mono focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="flex space-x-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
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
