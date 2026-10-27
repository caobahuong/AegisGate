"use client";

import React, { useState, useEffect } from "react";
import { Sliders } from "lucide-react";
import { PluginProfileResponse, UpdatePluginConfigRequest } from "@/types";
import { Modal } from "@/shared/ui/Modal";
import { Button } from "@/shared/ui/Button";
import { useToast } from "@/shared/hooks/useToast";
import { DynamicFormField } from "./DynamicFormField";

export interface EditConfigModalProps {
  isOpen: boolean;
  onClose: () => void;
  plugin: PluginProfileResponse | null;
  onUpdatePlugin?: (pluginId: string, req: UpdatePluginConfigRequest) => Promise<void>;
}

export const EditConfigModal: React.FC<EditConfigModalProps> = ({
  isOpen,
  onClose,
  plugin,
  onUpdatePlugin,
}) => {
  const [configValues, setConfigValues] = useState<Record<string, unknown>>({});
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const { showToast } = useToast();

  useEffect(() => {
    if (plugin) {
      setConfigValues(plugin.config || {});
    }
  }, [plugin]);

  if (!plugin) return null;

  const handleFieldChange = (name: string, value: unknown) => {
    setConfigValues((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!onUpdatePlugin || isSaving) return;

    setIsSaving(true);
    try {
      await onUpdatePlugin(plugin.id, { config: configValues });
      showToast(`Configuration updated for "${plugin.name}"!`, "success");
      onClose();
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : "Failed to update configuration", "error");
    } finally {
      setIsSaving(false);
    }
  };

  const uiSchema = plugin.ui_schema || [];

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`Configure Target: ${plugin.name}`}
      subtitle={`Dynamic connection and authentication properties for #${plugin.id}`}
      icon={<Sliders className="h-5 w-5" />}
      maxWidth="xl"
    >
      <form onSubmit={handleSave} data-testid="edit-plugin-modal" className="space-y-4">
        {uiSchema.length === 0 ? (
          <div className="p-4 text-center text-xs text-slate-500">
            No dynamic UI schema defined for this plugin. Configuration operates on raw key-value
            pairs.
          </div>
        ) : (
          <div className="space-y-3.5">
            {uiSchema.map((field) => (
              <DynamicFormField
                key={field.key}
                field={field}
                value={configValues[field.key]}
                onChange={(val) => handleFieldChange(field.key, val)}
              />
            ))}
          </div>
        )}

        <div className="flex justify-end space-x-2 pt-4 border-t border-slate-200 dark:border-slate-800">
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" isLoading={isSaving}>
            Save &amp; Re-Init Connection
          </Button>
        </div>
      </form>
    </Modal>
  );
};
