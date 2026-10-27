"use client";

import React, { useState } from "react";
import { Trash2, AlertTriangle } from "lucide-react";
import { PluginProfileResponse } from "@/types";
import { Modal } from "@/shared/ui/Modal";
import { Button } from "@/shared/ui/Button";
import { useToast } from "@/shared/hooks/useToast";

export interface UninstallModalProps {
  isOpen: boolean;
  onClose: () => void;
  plugin: PluginProfileResponse | null;
  onUninstallPlugin?: (pluginId: string, hardDelete: boolean) => Promise<void>;
}

export const UninstallModal: React.FC<UninstallModalProps> = ({
  isOpen,
  onClose,
  plugin,
  onUninstallPlugin,
}) => {
  const [hardDelete, setHardDelete] = useState<boolean>(false);
  const [isUninstalling, setIsUninstalling] = useState<boolean>(false);
  const { showToast } = useToast();

  if (!plugin) return null;

  const handleConfirm = async () => {
    if (!onUninstallPlugin || isUninstalling) return;

    setIsUninstalling(true);
    try {
      await onUninstallPlugin(plugin.id, hardDelete);
      showToast(
        hardDelete
          ? `Target "${plugin.name}" permanently deleted.`
          : `Target "${plugin.name}" disabled successfully.`,
        "info"
      );
      onClose();
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : "Failed to uninstall plugin", "error");
    } finally {
      setIsUninstalling(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Uninstall Pluggable Target"
      subtitle={`Choose uninstallation mode for #${plugin.id} (${plugin.name})`}
      icon={<Trash2 className="h-5 w-5 text-rose-500" />}
      maxWidth="md"
    >
      <div className="space-y-4">
        <div className="p-3.5 rounded-xl bg-amber-50 dark:bg-amber-500/10 border border-amber-200 dark:border-amber-500/30 text-amber-800 dark:text-amber-300 text-xs flex items-start space-x-2.5">
          <AlertTriangle className="h-4 w-4 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
          <p className="leading-relaxed">
            Removing this database target will immediately revoke AI Agent access to its schema
            catalog and pause any active execution tunnels.
          </p>
        </div>

        <div className="space-y-2">
          <label className="flex items-center space-x-2.5 p-3 rounded-lg border border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-950 cursor-pointer">
            <input
              type="radio"
              name="uninstall_mode"
              data-testid="mode-soft-deactivate"
              checked={!hardDelete}
              onChange={() => setHardDelete(false)}
              className="text-indigo-600 focus:ring-indigo-500"
            />
            <div className="text-xs">
              <span className="font-bold text-slate-800 dark:text-slate-200 block">
                Soft Deactivate (Recommended)
              </span>
              <span className="text-slate-500 dark:text-slate-400">
                Retains plugin files and audit logs, but disables execution and catalog access.
              </span>
            </div>
          </label>

          <label className="flex items-center space-x-2.5 p-3 rounded-lg border border-slate-200 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-950 cursor-pointer">
            <input
              type="radio"
              name="uninstall_mode"
              data-testid="mode-hard-delete"
              checked={hardDelete}
              onChange={() => setHardDelete(true)}
              className="text-rose-600 focus:ring-rose-500"
            />
            <div className="text-xs">
              <span className="font-bold text-rose-700 dark:text-rose-400 block">
                Permanent Hard Delete
              </span>
              <span className="text-slate-500 dark:text-slate-400">
                Purges adapter files and profile record from the AegisGate registry entirely.
              </span>
            </div>
          </label>
        </div>

        <div className="flex justify-end space-x-2 pt-3 border-t border-slate-200 dark:border-slate-800">
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button
            variant="danger"
            data-testid="confirm-uninstall-btn"
            onClick={handleConfirm}
            isLoading={isUninstalling}
          >
            {hardDelete ? "Permanently Delete" : "Disable Target"}
          </Button>
        </div>
      </div>
    </Modal>
  );
};
