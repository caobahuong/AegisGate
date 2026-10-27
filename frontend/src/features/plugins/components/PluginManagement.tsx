"use client";

import React, { useState } from "react";
import { Plus, Boxes, ShieldCheck, Activity } from "lucide-react";
import {
  PluginProfileResponse,
  RegisterPluginRequest,
  InstallGitPluginRequest,
  PluginCertificationResponse,
  PluginCertificationReport,
  UpdatePluginConfigRequest,
} from "@/types";
import { Button } from "@/shared/ui/Button";
import { EmptyState } from "@/shared/ui/EmptyState";
import { PluginCard } from "./PluginCard";
import { AddPluginModal } from "./AddPluginModal";
import { EditConfigModal } from "./EditConfigModal";
import { UninstallModal } from "./UninstallModal";
import { CertificationModal } from "./CertificationModal";

export interface PluginManagementProps {
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
  // Modal states
  const [showAddModal, setShowAddModal] = useState<boolean>(false);
  const [editingPlugin, setEditingPlugin] = useState<PluginProfileResponse | null>(null);
  const [uninstallingPlugin, setUninstallingPlugin] = useState<PluginProfileResponse | null>(null);
  const [inspectCertPlugin, setInspectCertPlugin] = useState<PluginProfileResponse | null>(null);

  // In-flight operation IDs
  const [verifyingId, setVerifyingId] = useState<string | null>(null);
  const [syncingId, setSyncingId] = useState<string | null>(null);

  const handleRunSanityCheck = async (id: string) => {
    if (!onVerifyPlugin || verifyingId) return;
    setVerifyingId(id);
    try {
      const report = await onVerifyPlugin(id);
      const target = plugins.find((p) => p.id === id);
      if (target) {
        setInspectCertPlugin({
          ...target,
          is_certified: report.certified,
          certification_report: report as unknown as PluginCertificationReport,
        });
      }
    } finally {
      setVerifyingId(null);
    }
  };

  const handleSync = async (id: string) => {
    if (syncingId) return;
    setSyncingId(id);
    try {
      await onSyncPlugin(id);
    } finally {
      setSyncingId(null);
    }
  };

  const totalSessions = plugins.reduce((acc, p) => acc + (p.active_sessions_count || 0), 0);
  const certifiedCount = plugins.filter((p) => p.is_certified).length;

  return (
    <div className="space-y-6">
      {/* Header & Metrics */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
        <div>
          <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center space-x-2">
            <Boxes className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />
            <span>Pluggable Targets &amp; Connectors</span>
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Isolated database adapter workers executing via JSON-RPC 2.0 over Stdio.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <div className="flex items-center space-x-3 text-xs bg-slate-50 dark:bg-slate-950 px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-800 font-mono">
            <span className="flex items-center space-x-1.5 text-slate-600 dark:text-slate-400">
              <Activity className="h-3 w-3 text-indigo-500" />
              <span>
                Pool:{" "}
                <strong className="text-slate-900 dark:text-slate-100">{totalSessions}</strong>{" "}
                SPIDs
              </span>
            </span>
            <span className="text-slate-300 dark:text-slate-700">|</span>
            <span className="flex items-center space-x-1.5 text-slate-600 dark:text-slate-400">
              <ShieldCheck className="h-3 w-3 text-emerald-500" />
              <span>
                Certified:{" "}
                <strong className="text-emerald-700 dark:text-emerald-400">
                  {certifiedCount}/{plugins.length}
                </strong>
              </span>
            </span>
          </div>

          <Button onClick={() => setShowAddModal(true)} leftIcon={<Plus className="h-4 w-4" />}>
            Add Pluggable Target
          </Button>
        </div>
      </div>

      {/* Target Plugins Grid */}
      {plugins.length === 0 ? (
        <EmptyState
          title="No Pluggable Targets Registered"
          description="Register a database adapter plugin (SQL Server, MongoDB, PostgreSQL) to begin routing queries through AegisGate."
          icon={<Boxes className="h-8 w-8 text-indigo-500" />}
          action={<Button onClick={() => setShowAddModal(true)}>Register First Target</Button>}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {plugins.map((plugin) => (
            <PluginCard
              key={plugin.id}
              plugin={plugin}
              verifyingId={verifyingId}
              syncingId={syncingId}
              onRunSanityCheck={handleRunSanityCheck}
              onOpenEdit={setEditingPlugin}
              onSync={handleSync}
              onViewMcpConfig={onViewMcpConfig}
              onOpenUninstall={setUninstallingPlugin}
              onInspectCert={setInspectCertPlugin}
            />
          ))}
        </div>
      )}

      {/* Modals */}
      <AddPluginModal
        isOpen={showAddModal}
        onClose={() => setShowAddModal(false)}
        onRegisterPlugin={onRegisterPlugin}
        onInstallZip={onInstallZip}
        onInstallGit={onInstallGit}
      />

      <EditConfigModal
        isOpen={!!editingPlugin}
        onClose={() => setEditingPlugin(null)}
        plugin={editingPlugin}
        onUpdatePlugin={onUpdatePlugin}
      />

      <UninstallModal
        isOpen={!!uninstallingPlugin}
        onClose={() => setUninstallingPlugin(null)}
        plugin={uninstallingPlugin}
        onUninstallPlugin={onUninstallPlugin}
      />

      <CertificationModal
        isOpen={!!inspectCertPlugin}
        onClose={() => setInspectCertPlugin(null)}
        plugin={inspectCertPlugin}
      />
    </div>
  );
};
