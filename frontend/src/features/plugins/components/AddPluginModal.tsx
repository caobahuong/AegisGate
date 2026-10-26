"use client";

import React, { useState } from "react";
import { Plus, Upload, GitBranch, Database } from "lucide-react";
import { RegisterPluginRequest, InstallGitPluginRequest } from "@/types";
import { Modal } from "@/shared/ui/Modal";
import { Tabs } from "@/shared/ui/Tabs";
import { ManualPluginForm } from "./ManualPluginForm";
import { ZipPluginForm } from "./ZipPluginForm";
import { GitPluginForm } from "./GitPluginForm";

export interface AddPluginModalProps {
  isOpen: boolean;
  onClose: () => void;
  onRegisterPlugin: (req: RegisterPluginRequest) => Promise<void>;
  onInstallZip?: (file: File) => Promise<void>;
  onInstallGit?: (req: InstallGitPluginRequest) => Promise<void>;
}

export const AddPluginModal: React.FC<AddPluginModalProps> = ({
  isOpen,
  onClose,
  onRegisterPlugin,
  onInstallZip,
  onInstallGit,
}) => {
  const [activeTab, setActiveTab] = useState<string>("preset");

  const tabItems = [
    { id: "preset", label: "Presets & Manual", icon: <Database className="h-3.5 w-3.5" /> },
    { id: "zip", label: "ZIP Archive", icon: <Upload className="h-3.5 w-3.5" /> },
    { id: "git", label: "Git Repository", icon: <GitBranch className="h-3.5 w-3.5" /> },
  ];

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Register New Pluggable Target"
      subtitle="Connect a new SQL or NoSQL database adapter to AegisGate proxy harness"
      icon={<Plus className="h-5 w-5" />}
      maxWidth="2xl"
    >
      <div className="space-y-4">
        <Tabs items={tabItems} activeTab={activeTab} onTabChange={setActiveTab} />

        {activeTab === "preset" && (
          <ManualPluginForm onRegisterPlugin={onRegisterPlugin} onClose={onClose} />
        )}

        {activeTab === "zip" && (
          <ZipPluginForm onInstallZip={onInstallZip} onClose={onClose} />
        )}

        {activeTab === "git" && (
          <GitPluginForm onInstallGit={onInstallGit} onClose={onClose} />
        )}
      </div>
    </Modal>
  );
};
