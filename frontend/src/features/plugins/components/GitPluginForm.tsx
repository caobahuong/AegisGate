"use client";

import React, { useState } from "react";
import { InstallGitPluginRequest } from "@/types";
import { Button } from "@/shared/ui/Button";
import { useToast } from "@/shared/hooks/useToast";

export interface GitPluginFormProps {
  onInstallGit?: (req: InstallGitPluginRequest) => Promise<void>;
  onClose: () => void;
}

export const GitPluginForm: React.FC<GitPluginFormProps> = ({ onInstallGit, onClose }) => {
  const { showToast } = useToast();
  const [gitUrl, setGitUrl] = useState<string>("");
  const [gitBranch, setGitBranch] = useState<string>("main");
  const [gitId, setGitId] = useState<string>("");
  const [isCloningGit, setIsCloningGit] = useState<boolean>(false);

  const handleGitSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!gitUrl.trim() || !onInstallGit || isCloningGit) return;

    setIsCloningGit(true);
    try {
      await onInstallGit({
        git_url: gitUrl.trim(),
        branch: gitBranch.trim() || undefined,
        plugin_id: gitId.trim() || undefined,
      });
      showToast("Git plugin cloned and certified successfully!", "success");
      onClose();
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : "Failed to clone Git plugin", "error");
    } finally {
      setIsCloningGit(false);
    }
  };

  return (
    <form onSubmit={handleGitSubmit} className="space-y-4 pt-2">
      <div>
        <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
          Git Clone URL
        </label>
        <input
          type="text"
          data-testid="input-git-url"
          value={gitUrl}
          onChange={(e) => setGitUrl(e.target.value)}
          placeholder="https://github.com/org/aegisgate-plugin-postgres.git"
          required
          className="w-full bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-900 dark:text-slate-100 font-mono"
        />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
            Branch
          </label>
          <input
            type="text"
            value={gitBranch}
            onChange={(e) => setGitBranch(e.target.value)}
            className="w-full bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-900 dark:text-slate-100 font-mono"
          />
        </div>
        <div>
          <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1">
            Override Plugin ID
          </label>
          <input
            type="text"
            value={gitId}
            onChange={(e) => setGitId(e.target.value)}
            placeholder="Optional ID override"
            className="w-full bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-900 dark:text-slate-100 font-mono"
          />
        </div>
      </div>
      <div className="flex justify-end space-x-2">
        <Button variant="secondary" onClick={onClose}>
          Cancel
        </Button>
        <Button
          type="submit"
          data-testid="clone-git-btn"
          disabled={!gitUrl.trim()}
          isLoading={isCloningGit}
        >
          Clone &amp; Install Git
        </Button>
      </div>
    </form>
  );
};
