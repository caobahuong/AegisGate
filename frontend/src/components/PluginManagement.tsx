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
  CheckCircle2,
  Sliders,
  Save,
  X,
  Layers,
  Terminal,
  ShieldCheck,
  ShieldAlert,
  Eye,
  EyeOff,
  Trash2,
  AlertTriangle,
  UploadCloud,
  GitBranch,
  FileArchive,
  Info,
} from "lucide-react";
import {
  CustomCardData,
  InstallGitPluginRequest,
  PluginCertificationReport,
  PluginCertificationResponse,
  PluginProfileResponse,
  RegisterPluginRequest,
  UiFieldSchema,
  UpdatePluginConfigRequest,
} from "@/types";
import { cn } from "@/lib/utils";

interface PluginManagementProps {
  plugins: PluginProfileResponse[];
  onRegisterPlugin: (req: RegisterPluginRequest) => Promise<void>;
  onInstallZip?: (file: File) => Promise<void>;
  onInstallGit?: (req: InstallGitPluginRequest) => Promise<void>;
  onVerifyPlugin?: (pluginId: string) => Promise<PluginCertificationResponse>;
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
          className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-100 font-mono focus:outline-none focus:border-indigo-500 resize-y"
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
        <p className="text-[10px] text-slate-500 leading-tight">{field.description}</p>
      )}
    </div>
  );
};

export const PluginManagement: React.FC<PluginManagementProps> = ({
  plugins,
  onRegisterPlugin,
  onInstallZip,
  onInstallGit,
  onVerifyPlugin,
  onUpdatePlugin,
  onSyncPlugin,
  onUninstallPlugin,
  onViewMcpConfig,
}) => {
  // Add Modal State
  const [showAddModal, setShowAddModal] = useState<boolean>(false);
  const [addTab, setAddTab] = useState<"preset" | "zip" | "git">("preset");

  // Preset Form State
  const [addPreset, setAddPreset] = useState<string>("sqlserver");
  const [addId, setAddId] = useState<string>("");
  const [addName, setAddName] = useState<string>("");
  const [addDriver, setAddDriver] = useState<string>("pyodbc/mssql");
  const [addEntrypoint, setAddEntrypoint] = useState<string>("python plugins/sqlserver_plugin/adapter.py");
  const [addDryRunCmd, setAddDryRunCmd] = useState<string>("SET SHOWPLAN_XML ON");
  const [addAbortCmd, setAddAbortCmd] = useState<string>("KILL {spid}");

  // ZIP Upload State
  const [selectedZipFile, setSelectedZipFile] = useState<File | null>(null);
  const [isUploadingZip, setIsUploadingZip] = useState<boolean>(false);
  const [zipMessage, setZipMessage] = useState<string>("");

  // Git Clone State
  const [gitUrl, setGitUrl] = useState<string>("");
  const [gitBranch, setGitBranch] = useState<string>("main");
  const [gitPluginId, setGitPluginId] = useState<string>("");
  const [isCloningGit, setIsCloningGit] = useState<boolean>(false);
  const [gitMessage, setGitMessage] = useState<string>("");

  // Inspect Certification Modal
  const [inspectCertPlugin, setInspectCertPlugin] = useState<PluginProfileResponse | null>(null);
  const [verifyingId, setVerifyingId] = useState<string | null>(null);

  // Edit Configuration Modal State
  const [editingPlugin, setEditingPlugin] = useState<PluginProfileResponse | null>(null);
  const [editConfigValues, setEditConfigValues] = useState<Record<string, unknown>>({});
  const [isSavingConfig, setIsSavingConfig] = useState<boolean>(false);

  // Uninstall State
  const [uninstallingPlugin, setUninstallingPlugin] = useState<PluginProfileResponse | null>(null);
  const [uninstallHardDelete, setUninstallHardDelete] = useState<boolean>(false);
  const [isUninstalling, setIsUninstalling] = useState<boolean>(false);

  // General Loading & Statuses
  const [syncingId, setSyncingId] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  const handlePresetChange = (preset: string) => {
    setAddPreset(preset);
    if (preset === "sqlserver") {
      setAddId("sqlserver_prod");
      setAddName("SQL Server Enterprise");
      setAddDriver("pyodbc/mssql");
      setAddEntrypoint("python plugins/sqlserver_plugin/adapter.py");
      setAddDryRunCmd("SET SHOWPLAN_XML ON");
      setAddAbortCmd("KILL {spid}");
    } else if (preset === "mongodb") {
      setAddId("mongodb_prod");
      setAddName("MongoDB Analytics Cluster");
      setAddDriver("pymongo/mongodb");
      setAddEntrypoint("python plugins/mongodb_plugin/adapter.py");
      setAddDryRunCmd("db.runCommand({explain})");
      setAddAbortCmd("db.killOp({opid})");
    } else {
      setAddId("custom_plugin");
      setAddName("Custom Data Target");
      setAddDriver("custom/driver");
      setAddEntrypoint("python adapter.py");
      setAddDryRunCmd("EXPLAIN {query}");
      setAddAbortCmd("KILL {spid}");
    }
  };

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!addId.trim() || !addName.trim() || isSubmitting) return;

    setIsSubmitting(true);
    try {
      await onRegisterPlugin({
        id: addId.trim(),
        name: addName.trim(),
        driver: addDriver.trim(),
        entrypoint: addEntrypoint.trim(),
        dry_run_command: addDryRunCmd.trim(),
        abort_command: addAbortCmd.trim(),
        config: {},
      });
      setShowAddModal(false);
      setAddId("");
      setAddName("");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleUploadZip = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedZipFile || !onInstallZip || isUploadingZip) return;

    setIsUploadingZip(true);
    setZipMessage("Extracting archive, setting up isolated venv, and running 4-stage linter...");
    try {
      await onInstallZip(selectedZipFile);
      setZipMessage("Plugin successfully installed and certified!");
      setTimeout(() => {
        setShowAddModal(false);
        setSelectedZipFile(null);
        setZipMessage("");
      }, 1000);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setZipMessage(`Install failed: ${msg}`);
    } finally {
      setIsUploadingZip(false);
    }
  };

  const handleCloneGit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!gitUrl.trim() || !onInstallGit || isCloningGit) return;

    setIsCloningGit(true);
    setGitMessage("Cloning Git repository, verifying manifest, and certifying...");
    try {
      await onInstallGit({
        git_url: gitUrl.trim(),
        branch: gitBranch.trim() || undefined,
        plugin_id: gitPluginId.trim() || undefined,
      });
      setGitMessage("Git Plugin successfully cloned and certified!");
      setTimeout(() => {
        setShowAddModal(false);
        setGitUrl("");
        setGitMessage("");
      }, 1000);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setGitMessage(`Git install failed: ${msg}`);
    } finally {
      setIsCloningGit(false);
    }
  };

  const handleRunSanityCheck = async (pluginId: string) => {
    if (!onVerifyPlugin || verifyingId) return;
    setVerifyingId(pluginId);
    try {
      const report = await onVerifyPlugin(pluginId);
      // Auto-open inspect report to let user view details
      const targetPlugin = plugins.find((p) => p.id === pluginId);
      if (targetPlugin) {
        setInspectCertPlugin({
          ...targetPlugin,
          is_certified: report.certified,
          certification_report: report as unknown as PluginCertificationReport,
        });
      }
    } finally {
      setVerifyingId(null);
    }
  };

  const handleOpenEdit = (p: PluginProfileResponse) => {
    setEditingPlugin(p);
    setEditConfigValues(p.config || {});
  };

  const handleSaveConfig = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingPlugin || !onUpdatePlugin || isSavingConfig) return;

    setIsSavingConfig(true);
    try {
      await onUpdatePlugin(editingPlugin.id, {
        config: editConfigValues,
      });
      setEditingPlugin(null);
    } finally {
      setIsSavingConfig(false);
    }
  };

  const handleSync = async (id: string) => {
    setSyncingId(id);
    try {
      await onSyncPlugin(id);
    } finally {
      setSyncingId(null);
    }
  };

  const handleConfirmUninstall = async () => {
    if (!uninstallingPlugin || !onUninstallPlugin) return;
    setIsUninstalling(true);
    try {
      await onUninstallPlugin(uninstallingPlugin.id, uninstallHardDelete);
      setUninstallingPlugin(null);
    } finally {
      setIsUninstalling(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header & Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h1 className="text-sm font-bold uppercase tracking-wider text-slate-100 flex items-center space-x-2">
            <Boxes className="h-4 w-4 text-indigo-400" />
            <span>Pluggable Targets & Connectors</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Manage database connectors via standardized JSON-RPC 2.0 Stdio protocol
          </p>
        </div>

        <button
          onClick={() => {
            handlePresetChange("sqlserver");
            setShowAddModal(true);
          }}
          className="flex items-center space-x-2 bg-indigo-600 hover:bg-indigo-500 text-white px-3.5 py-2 rounded-lg text-xs font-semibold shadow-md shadow-indigo-600/30 transition-colors"
        >
          <Plus className="h-4 w-4" />
          <span>Add Pluggable Target</span>
        </button>
      </div>

      {/* Target Plugins Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {plugins.map((plugin) => (
          <div
            key={plugin.id}
            data-testid={`plugin-card-${plugin.id}`}
            className="bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4 shadow-sm hover:border-slate-700 transition-all flex flex-col justify-between"
          >
            {/* Top Meta Area */}
            <div className="space-y-3">
              <div className="flex items-start justify-between">
                <div className="space-y-1">
                  <div className="flex items-center space-x-2">
                    <Database className="h-4 w-4 text-indigo-400" />
                    <h3 className="font-bold text-slate-100 text-sm tracking-wide">
                      {plugin.name}
                    </h3>
                  </div>
                  <span className="text-[11px] font-mono text-slate-400 block">
                    ID: {plugin.id}
                  </span>
                </div>

                {/* Status and Certification Badges */}
                <div className="flex flex-col items-end space-y-1.5">
                  <span
                    className={cn(
                      "px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider",
                      plugin.status === "active"
                        ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/30"
                        : "bg-slate-800 text-slate-400 border border-slate-700"
                    )}
                  >
                    {plugin.status === "active" ? "Connected" : "Disconnected"}
                  </span>

                  {/* Certification Badge */}
                  {plugin.is_certified ? (
                    <button
                      type="button"
                      data-testid={`cert-badge-${plugin.id}`}
                      onClick={() => setInspectCertPlugin(plugin)}
                      className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 hover:bg-emerald-500/25 transition-colors cursor-pointer"
                      title="Certified & Ready. Click to view 4-stage sanity test report."
                    >
                      <ShieldCheck className="h-3 w-3 text-emerald-400" />
                      <span>Certified &amp; Ready 🛡️</span>
                    </button>
                  ) : (
                    <button
                      type="button"
                      data-testid={`cert-badge-${plugin.id}`}
                      onClick={() => setInspectCertPlugin(plugin)}
                      className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-500/15 text-amber-400 border border-amber-500/30 hover:bg-amber-500/25 transition-colors cursor-pointer"
                      title="Certification pending or warning. Click to inspect report."
                    >
                      <ShieldAlert className="h-3 w-3 text-amber-400" />
                      <span>Verification Warning ⚠️</span>
                    </button>
                  )}
                </div>
              </div>

              {/* Dynamic Connection Parameter Summary */}
              <div className="bg-slate-950 border border-slate-800 rounded-lg p-3 space-y-1.5 text-xs">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block border-b border-slate-800/80 pb-1">
                  Active Connection Parameters
                </span>
                {Object.keys(plugin.config || {}).length === 0 ? (
                  <span className="text-slate-500 italic block py-0.5">No parameters configured.</span>
                ) : (
                  Object.entries(plugin.config).map(([k, v]) => (
                    <div key={k} className="flex justify-between items-center text-[11px]">
                      <span className="text-slate-400 capitalize">{k}:</span>
                      <span className="font-mono text-slate-200 truncate max-w-[200px]">
                        {k.toLowerCase().includes("password") ? "••••••••" : String(v)}
                      </span>
                    </div>
                  ))
                )}
              </div>

              {/* Custom Plugin Card Table */}
              {plugin.custom_card && (
                <div className="bg-slate-950/70 border border-slate-800/80 rounded-lg p-3 space-y-2">
                  <div className="flex items-center justify-between border-b border-slate-800/80 pb-1">
                    <span className="text-[10px] font-bold text-indigo-400 uppercase tracking-wider flex items-center space-x-1">
                      <Terminal className="h-3 w-3" />
                      <span>{plugin.custom_card.title}</span>
                    </span>
                    {plugin.custom_card.badge ? (
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                        {plugin.custom_card.badge}
                      </span>
                    ) : (
                      <span className="text-[9px] font-mono text-slate-500">custom_card</span>
                    )}
                  </div>

                  {plugin.custom_card.badges && (
                    <div className="flex flex-wrap gap-1.5 pt-0.5">
                      {plugin.custom_card.badges.map((b, i) => (
                        <span
                          key={i}
                          className="px-2 py-0.5 rounded text-[10px] font-medium bg-slate-900 border border-slate-800 text-slate-300"
                        >
                          <strong className="text-slate-400">{b.label}:</strong> {b.value}
                        </span>
                      ))}
                    </div>
                  )}

                  {plugin.custom_card.sample_data && plugin.custom_card.sample_data.length > 0 && (
                    <div className="overflow-x-auto pt-1">
                      <table className="w-full text-left text-[10px] border-collapse">
                        <thead>
                          <tr className="border-b border-slate-800 text-slate-400">
                            {(plugin.custom_card.columns || Object.keys(plugin.custom_card.sample_data[0] || {})).map(
                              (col) => (
                                <th key={col} className="py-1 px-1.5 font-semibold">
                                  {col}
                                </th>
                              )
                            )}
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-850">
                          {plugin.custom_card.sample_data.map((row, idx) => (
                            <tr key={idx} className="hover:bg-slate-900/50">
                              {(plugin.custom_card?.columns || Object.keys(row)).map((col) => (
                                <td key={col} className="py-1 px-1.5 font-mono text-slate-300">
                                  {String(row[col] ?? "")}
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

              {/* Operational Metrics */}
              <div className="bg-slate-950/40 border border-slate-800/50 rounded-lg p-3 space-y-1 text-xs">
                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block border-b border-slate-800/60 pb-1">
                  Live Operational Metrics &amp; Pool
                </span>
                <div className="flex justify-between text-[11px] pt-1">
                  <span className="text-slate-400">Driver Identifier:</span>
                  <span className="font-mono text-indigo-300">{plugin.driver}</span>
                </div>
                <div className="flex justify-between text-[11px]">
                  <span className="text-slate-400">Active SPID Pool:</span>
                  <span className="font-mono text-slate-200">
                    {plugin.active_sessions_count} sessions
                  </span>
                </div>
                <div className="flex justify-between text-[11px]">
                  <span className="text-slate-400">Roundtrip Latency:</span>
                  <span className="font-mono text-emerald-400">{plugin.latency_ms} ms</span>
                </div>
              </div>
            </div>

            {/* Bottom Actions Row */}
            <div className="pt-2 border-t border-slate-800/80 space-y-2">
              <div className="grid grid-cols-2 gap-2">
                {/* Run Sanity Check Button */}
                <button
                  type="button"
                  data-testid={`sanity-check-btn-${plugin.id}`}
                  onClick={() => handleRunSanityCheck(plugin.id)}
                  disabled={verifyingId === plugin.id}
                  className="flex items-center justify-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition-colors disabled:opacity-50"
                  title="Run 4-stage automated compatibility & sanity check"
                >
                  <RefreshCw
                    className={cn(
                      "h-3.5 w-3.5",
                      verifyingId === plugin.id && "animate-spin text-indigo-400"
                    )}
                  />
                  <span>{verifyingId === plugin.id ? "Testing..." : "Sanity Check"}</span>
                </button>

                {/* Edit Config Button */}
                <button
                  type="button"
                  data-testid={`edit-btn-${plugin.id}`}
                  onClick={() => handleOpenEdit(plugin)}
                  className="flex items-center justify-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border border-indigo-500/30 transition-colors"
                >
                  <Sliders className="h-3.5 w-3.5" />
                  <span>Edit Configuration</span>
                </button>
              </div>

              <div className="grid grid-cols-3 gap-2">
                {/* Sync Schema */}
                <button
                  type="button"
                  onClick={() => handleSync(plugin.id)}
                  disabled={syncingId === plugin.id}
                  className="flex items-center justify-center space-x-1 bg-slate-800 hover:bg-slate-750 text-slate-200 px-2 py-1.5 rounded-lg text-[11px] font-semibold border border-slate-700 transition-colors disabled:opacity-50"
                  title="Sync database tables and structural schema into Knowledge Store"
                >
                  <RefreshCw
                    className={cn(
                      "h-3 w-3",
                      syncingId === plugin.id && "animate-spin text-indigo-400"
                    )}
                  />
                  <span>{syncingId === plugin.id ? "Syncing..." : "Sync Schema"}</span>
                </button>

                {/* MCP Config Snippet */}
                <button
                  type="button"
                  data-testid={`mcp-btn-${plugin.id}`}
                  onClick={() => onViewMcpConfig && onViewMcpConfig(plugin)}
                  className="flex items-center justify-center space-x-1 bg-indigo-950/60 hover:bg-indigo-900/60 text-indigo-300 border border-indigo-800/80 px-2 py-1.5 rounded-lg text-[11px] font-semibold transition-colors"
                >
                  <Zap className="h-3 w-3 text-indigo-400" />
                  <span>MCP Config</span>
                </button>

                {/* Uninstall */}
                <button
                  type="button"
                  data-testid={`uninstall-btn-${plugin.id}`}
                  onClick={() => setUninstallingPlugin(plugin)}
                  className="flex items-center justify-center space-x-1 bg-slate-800/80 hover:bg-red-950/60 text-slate-400 hover:text-red-300 border border-slate-700 hover:border-red-800/80 px-2 py-1.5 rounded-lg text-[11px] font-semibold transition-colors"
                >
                  <Trash2 className="h-3 w-3" />
                  <span>Uninstall</span>
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* ========================================================
          INSPECT CERTIFICATION MODAL (4-Stage Sanity Checklist)
         ======================================================== */}
      {inspectCertPlugin && (
        <div
          data-testid="cert-inspect-modal"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 overflow-y-auto"
        >
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-lg w-full p-6 shadow-2xl space-y-4 my-8">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center space-x-2">
                <ShieldCheck className="h-5 w-5 text-indigo-400" />
                <div>
                  <h3 className="text-sm font-bold text-slate-100">
                    Plugin Sanity &amp; Certification Report
                  </h3>
                  <span className="text-[11px] font-mono text-slate-400">
                    Target: #{inspectCertPlugin.id} ({inspectCertPlugin.name})
                  </span>
                </div>
              </div>
              <button
                onClick={() => setInspectCertPlugin(null)}
                className="text-slate-400 hover:text-slate-200 p-1"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            {/* Overall Certification Status */}
            <div
              className={cn(
                "p-3 rounded-lg border flex items-center justify-between text-xs font-semibold",
                inspectCertPlugin.is_certified
                  ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400"
                  : "bg-amber-500/10 border-amber-500/30 text-amber-400"
              )}
            >
              <div className="flex items-center space-x-2">
                {inspectCertPlugin.is_certified ? (
                  <CheckCircle2 className="h-4 w-4" />
                ) : (
                  <AlertTriangle className="h-4 w-4" />
                )}
                <span>
                  {inspectCertPlugin.is_certified
                    ? "Passed 4-Stage Compatibility Checks (Certified & Ready)"
                    : "Compatibility Warning or Incomplete Sanity Checks"}
                </span>
              </div>
              <span className="font-mono text-[10px] text-slate-400">
                {inspectCertPlugin.certification_report?.verified_at
                  ? new Date(inspectCertPlugin.certification_report.verified_at).toLocaleTimeString()
                  : "Latest"}
              </span>
            </div>

            {/* 4-Stage Breakdown */}
            <div className="space-y-2.5">
              <span className="text-[11px] font-bold text-slate-400 uppercase tracking-wider block">
                Verification Pipeline Checklist:
              </span>

              {[
                {
                  key: "handshake",
                  name: "1. Handshake & RPC Ping",
                  desc: "Subprocess spawn and JSON-RPC 2.0 protocol responsiveness",
                },
                {
                  key: "sync_knowledge",
                  name: "2. Sync Knowledge Schema",
                  desc: "Catalog schema extraction (tables, columns, indexes)",
                },
                {
                  key: "dry_run",
                  name: "3. Dry-Run Analysis",
                  desc: "Execution plan generation (SHOWPLAN/EXPLAIN) and risk score",
                },
                {
                  key: "abort",
                  name: "4. Abort Hook Protocol",
                  desc: "Emergency kill protocol validation (KILL {spid})",
                },
              ].map((stage) => {
                const check = inspectCertPlugin.certification_report?.checks?.[stage.key];
                const isPassed = check?.status === "PASSED";

                return (
                  <div
                    key={stage.key}
                    className="p-3 rounded-lg bg-slate-950 border border-slate-800 space-y-1 text-xs"
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-slate-200">{stage.name}</span>
                      <span
                        className={cn(
                          "px-2 py-0.5 rounded text-[10px] font-bold uppercase",
                          isPassed
                            ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/30"
                            : "bg-red-500/15 text-red-400 border border-red-500/30"
                        )}
                      >
                        {isPassed ? "PASSED" : "FAILED / PENDING"}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-400">{stage.desc}</p>
                    {check && (
                      <div className="text-[10px] font-mono text-slate-500 pt-1 flex justify-between">
                        <span>Latency: {check.latency_ms ?? "N/A"} ms</span>
                        <span className="text-slate-400 truncate max-w-[200px]">
                          {check.details || check.error || "Verified"}
                        </span>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            <div className="pt-2 border-t border-slate-800 flex justify-end">
              <button
                type="button"
                onClick={() => setInspectCertPlugin(null)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-semibold transition-colors"
              >
                Close Report
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================
          ADD PLUGGABLE TARGET MODAL (3 TABS: Preset, ZIP, Git)
         ======================================================== */}
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

            {/* 3 Installation Tabs */}
            <div className="grid grid-cols-3 gap-1 bg-slate-950 p-1 rounded-lg border border-slate-800">
              <button
                type="button"
                data-testid="tab-add-preset"
                onClick={() => setAddTab("preset")}
                className={cn(
                  "py-1.5 text-xs font-semibold rounded-md transition-all flex items-center justify-center space-x-1.5",
                  addTab === "preset"
                    ? "bg-slate-800 text-slate-100 shadow-sm"
                    : "text-slate-400 hover:text-slate-200"
                )}
              >
                <Sliders className="h-3 w-3" />
                <span>Preset &amp; Form</span>
              </button>
              <button
                type="button"
                data-testid="tab-add-zip"
                onClick={() => setAddTab("zip")}
                className={cn(
                  "py-1.5 text-xs font-semibold rounded-md transition-all flex items-center justify-center space-x-1.5",
                  addTab === "zip"
                    ? "bg-slate-800 text-slate-100 shadow-sm"
                    : "text-slate-400 hover:text-slate-200"
                )}
              >
                <UploadCloud className="h-3 w-3" />
                <span>Upload ZIP</span>
              </button>
              <button
                type="button"
                data-testid="tab-add-git"
                onClick={() => setAddTab("git")}
                className={cn(
                  "py-1.5 text-xs font-semibold rounded-md transition-all flex items-center justify-center space-x-1.5",
                  addTab === "git"
                    ? "bg-slate-800 text-slate-100 shadow-sm"
                    : "text-slate-400 hover:text-slate-200"
                )}
              >
                <GitBranch className="h-3 w-3" />
                <span>Clone Git</span>
              </button>
            </div>

            {/* TAB 1: PRESET FORM */}
            {addTab === "preset" && (
              <form onSubmit={handleCreate} className="space-y-3">
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
            )}

            {/* TAB 2: UPLOAD ZIP PACKAGE */}
            {addTab === "zip" && (
              <form onSubmit={handleUploadZip} className="space-y-4">
                <div className="border-2 border-dashed border-slate-800 hover:border-indigo-500/50 rounded-xl p-6 text-center space-y-2 bg-slate-950/50 transition-colors">
                  <FileArchive className="h-8 w-8 text-indigo-400 mx-auto" />
                  <div>
                    <label
                      htmlFor="zip-upload-input"
                      className="cursor-pointer text-xs font-bold text-indigo-400 hover:text-indigo-300 underline"
                    >
                      Choose ZIP file
                    </label>
                    <span className="text-xs text-slate-400"> or drag and drop</span>
                    <input
                      id="zip-upload-input"
                      type="file"
                      accept=".zip"
                      onChange={(e) => {
                        const file = e.target.files?.[0];
                        if (file) setSelectedZipFile(file);
                      }}
                      className="hidden"
                    />
                  </div>
                  <p className="text-[11px] text-slate-500">
                    Package must contain manifest.json, adapter.py, and optional requirements.txt
                  </p>
                  {selectedZipFile && (
                    <div className="pt-2 text-xs font-mono text-emerald-400 bg-emerald-500/10 py-1 px-2 rounded border border-emerald-500/20 inline-block">
                      {selectedZipFile.name} ({(selectedZipFile.size / 1024).toFixed(1)} KB)
                    </div>
                  )}
                </div>

                {zipMessage && (
                  <p className="text-xs text-indigo-300 font-medium text-center animate-pulse">
                    {zipMessage}
                  </p>
                )}

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
                    data-testid="upload-zip-btn"
                    disabled={!selectedZipFile || isUploadingZip}
                    className="w-1/2 flex items-center justify-center space-x-2 bg-indigo-600 hover:bg-indigo-500 text-white py-2 rounded-lg text-xs font-semibold transition-colors shadow-md shadow-indigo-600/30 disabled:opacity-50"
                  >
                    {isUploadingZip ? (
                      <>
                        <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                        <span>Building...</span>
                      </>
                    ) : (
                      <>
                        <UploadCloud className="h-3.5 w-3.5" />
                        <span>Upload &amp; Install</span>
                      </>
                    )}
                  </button>
                </div>
              </form>
            )}

            {/* TAB 3: CLONE FROM GIT */}
            {addTab === "git" && (
              <form onSubmit={handleCloneGit} className="space-y-3">
                <div>
                  <label className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">
                    Remote Git Repository URL
                  </label>
                  <input
                    type="url"
                    required
                    data-testid="input-git-url"
                    value={gitUrl}
                    onChange={(e) => setGitUrl(e.target.value)}
                    placeholder="https://github.com/my-org/aegisgate-plugin-postgres.git"
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-100 font-mono focus:outline-none focus:border-indigo-500"
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">
                      Git Branch / Tag (Optional)
                    </label>
                    <input
                      type="text"
                      value={gitBranch}
                      onChange={(e) => setGitBranch(e.target.value)}
                      placeholder="main"
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-100 font-mono focus:outline-none focus:border-indigo-500"
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">
                      Target Plugin ID (Optional)
                    </label>
                    <input
                      type="text"
                      value={gitPluginId}
                      onChange={(e) => setGitPluginId(e.target.value)}
                      placeholder="e.g. postgres_prod"
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-100 font-mono focus:outline-none focus:border-indigo-500"
                    />
                  </div>
                </div>

                {gitMessage && (
                  <p className="text-xs text-indigo-300 font-medium text-center animate-pulse">
                    {gitMessage}
                  </p>
                )}

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
                    data-testid="clone-git-btn"
                    disabled={!gitUrl.trim() || isCloningGit}
                    className="w-1/2 flex items-center justify-center space-x-2 bg-indigo-600 hover:bg-indigo-500 text-white py-2 rounded-lg text-xs font-semibold transition-colors shadow-md shadow-indigo-600/30 disabled:opacity-50"
                  >
                    {isCloningGit ? (
                      <>
                        <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                        <span>Cloning...</span>
                      </>
                    ) : (
                      <>
                        <GitBranch className="h-3.5 w-3.5" />
                        <span>Clone &amp; Install</span>
                      </>
                    )}
                  </button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}

      {/* Edit Modal */}
      {editingPlugin && (
        <div
          data-testid="edit-plugin-modal"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 overflow-y-auto"
        >
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-lg w-full p-6 shadow-2xl space-y-4 my-8">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <h3 className="text-sm font-bold text-slate-100 flex items-center space-x-2">
                <Sliders className="h-4 w-4 text-indigo-400" />
                <span>Edit Connection Configuration: {editingPlugin.name}</span>
              </h3>
              <button
                onClick={() => setEditingPlugin(null)}
                className="text-slate-400 hover:text-slate-200 text-xs"
              >
                Cancel
              </button>
            </div>

            <form onSubmit={handleSaveConfig} className="space-y-4">
              <div className="space-y-3">
                {editingPlugin.ui_schema && editingPlugin.ui_schema.length > 0 ? (
                  editingPlugin.ui_schema.map((field) => (
                    <DynamicFormField
                      key={field.key}
                      field={field}
                      value={editConfigValues[field.key] ?? field.default ?? ""}
                      onChange={(val) =>
                        setEditConfigValues((prev) => ({ ...prev, [field.key]: val }))
                      }
                    />
                  ))
                ) : (
                  <div className="text-xs text-slate-500 italic py-2">
                    No dynamic UI schema defined for this plugin.
                  </div>
                )}
              </div>

              <div className="flex space-x-2 pt-2 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setEditingPlugin(null)}
                  className="w-1/2 bg-slate-800 hover:bg-slate-700 text-slate-300 py-2 rounded-lg text-xs font-semibold transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSavingConfig}
                  className="w-1/2 flex items-center justify-center space-x-1.5 bg-indigo-600 hover:bg-indigo-500 text-white py-2 rounded-lg text-xs font-semibold transition-colors shadow-md shadow-indigo-600/30"
                >
                  {isSavingConfig ? (
                    <>
                      <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                      <span>Saving...</span>
                    </>
                  ) : (
                    <>
                      <Save className="h-3.5 w-3.5" />
                      <span>Save &amp; Re-Init Connection</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Uninstall Modal */}
      {uninstallingPlugin && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 overflow-y-auto">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-md w-full shadow-2xl overflow-hidden my-8">
            <div className="p-6 space-y-4">
              <div className="flex items-center space-x-3 text-rose-400">
                <div className="p-2.5 rounded-full bg-rose-500/10 border border-rose-500/20">
                  <AlertTriangle className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-100">Uninstall Pluggable Target</h3>
                  <span className="text-xs text-slate-400 font-mono">#{uninstallingPlugin.id}</span>
                </div>
              </div>

              <p className="text-xs text-slate-300 leading-relaxed">
                Are you sure you want to uninstall connector{" "}
                <strong className="text-white font-semibold">{uninstallingPlugin.name}</strong>?
              </p>

              <div className="space-y-2">
                <label className="flex items-start space-x-2.5 p-2.5 rounded-lg border border-slate-800 bg-slate-950 cursor-pointer">
                  <input
                    type="radio"
                    name="uninstall-mode"
                    data-testid="mode-soft-deactivate"
                    checked={!uninstallHardDelete}
                    onChange={() => setUninstallHardDelete(false)}
                    className="mt-0.5 text-indigo-500 focus:ring-0"
                  />
                  <div>
                    <span className="text-xs font-semibold text-slate-200 block">
                      Soft Deactivate (Recommended)
                    </span>
                    <span className="text-[11px] text-slate-400">
                      Disable target connection while retaining schema &amp; audit history.
                    </span>
                  </div>
                </label>

                <label className="flex items-start space-x-2.5 p-2.5 rounded-lg border border-rose-950/40 bg-slate-950 cursor-pointer">
                  <input
                    type="radio"
                    name="uninstall-mode"
                    data-testid="mode-hard-delete"
                    checked={uninstallHardDelete}
                    onChange={() => setUninstallHardDelete(true)}
                    className="mt-0.5 text-rose-500 focus:ring-0"
                  />
                  <div>
                    <span className="text-xs font-semibold text-rose-400 block">
                      Permanent Hard Delete
                    </span>
                    <span className="text-[11px] text-slate-400">
                      Permanently remove plugin configuration and metadata from SQLite database.
                    </span>
                  </div>
                </label>
              </div>
            </div>

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
    </div>
  );
};
