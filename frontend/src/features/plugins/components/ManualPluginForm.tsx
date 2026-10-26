"use client";

import React, { useState } from "react";
import { RegisterPluginRequest } from "@/types";
import { Button } from "@/shared/ui/Button";
import { useToast } from "@/shared/hooks/useToast";

export interface ManualPluginFormProps {
  onRegisterPlugin: (req: RegisterPluginRequest) => Promise<void>;
  onClose: () => void;
}

export const ManualPluginForm: React.FC<ManualPluginFormProps> = ({ onRegisterPlugin, onClose }) => {
  const { showToast } = useToast();
  const [preset, setPreset] = useState<string>("sqlserver");
  const [id, setId] = useState<string>("sqlserver_prod");
  const [name, setName] = useState<string>("SQL Server Enterprise");
  const [driver, setDriver] = useState<string>("pyodbc/mssql");
  const [entrypoint, setEntrypoint] = useState<string>("python plugins/sqlserver_plugin/adapter.py");
  const [dryRunCmd, setDryRunCmd] = useState<string>("SET SHOWPLAN_XML ON");
  const [abortCmd, setAbortCmd] = useState<string>("KILL {spid}");
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  const handlePresetSelect = (p: string) => {
    setPreset(p);
    if (p === "sqlserver") {
      setId("sqlserver_prod");
      setName("SQL Server Enterprise");
      setDriver("pyodbc/mssql");
      setEntrypoint("python plugins/sqlserver_plugin/adapter.py");
      setDryRunCmd("SET SHOWPLAN_XML ON");
      setAbortCmd("KILL {spid}");
    } else if (p === "mongodb") {
      setId("mongodb_prod");
      setName("MongoDB Analytics Cluster");
      setDriver("pymongo/mongodb");
      setEntrypoint("python plugins/mongodb_plugin/adapter.py");
      setDryRunCmd("db.runCommand({explain})");
      setAbortCmd("db.killOp({opid})");
    } else {
      setId("custom_plugin");
      setName("Custom Data Target");
      setDriver("custom/driver");
      setEntrypoint("python adapter.py");
      setDryRunCmd("EXPLAIN {query}");
      setAbortCmd("KILL {spid}");
    }
  };

  const handleManualSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!id.trim() || !name.trim() || isSubmitting) return;

    setIsSubmitting(true);
    try {
      await onRegisterPlugin({
        id: id.trim(),
        name: name.trim(),
        driver: driver.trim(),
        entrypoint: entrypoint.trim(),
        dry_run_command: dryRunCmd.trim(),
        abort_command: abortCmd.trim(),
        config: {},
      });
      showToast(`Plugin "${name}" registered successfully!`, "success");
      onClose();
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : "Failed to register plugin", "error");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleManualSubmit} className="space-y-4 pt-2">
      <div>
        <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
          Adapter Template
        </label>
        <select
          value={preset}
          onChange={(e) => handlePresetSelect(e.target.value)}
          className="w-full bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-900 dark:text-slate-100"
        >
          <option value="sqlserver">Microsoft SQL Server (pyodbc / simulated)</option>
          <option value="mongodb">MongoDB Enterprise (pymongo / simulated)</option>
          <option value="custom">Custom JSON-RPC Adapter</option>
        </select>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">Target ID</label>
          <input
            type="text"
            value={id}
            onChange={(e) => setId(e.target.value)}
            required
            className="w-full bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-900 dark:text-slate-100 font-mono"
          />
        </div>
        <div>
          <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">Display Name</label>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            className="w-full bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-900 dark:text-slate-100"
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">Driver</label>
          <input
            type="text"
            value={driver}
            onChange={(e) => setDriver(e.target.value)}
            required
            className="w-full bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-900 dark:text-slate-100 font-mono"
          />
        </div>
        <div>
          <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">Entrypoint</label>
          <input
            type="text"
            value={entrypoint}
            onChange={(e) => setEntrypoint(e.target.value)}
            required
            className="w-full bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-900 dark:text-slate-100 font-mono"
          />
        </div>
      </div>

      <div className="flex justify-end space-x-2 pt-2 border-t border-slate-200 dark:border-slate-800">
        <Button variant="secondary" onClick={onClose}>
          Cancel
        </Button>
        <Button type="submit" isLoading={isSubmitting}>
          Register Plugin
        </Button>
      </div>
    </form>
  );
};
