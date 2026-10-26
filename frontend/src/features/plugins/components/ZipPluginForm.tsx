"use client";

import React, { useState } from "react";
import { Upload } from "lucide-react";
import { Button } from "@/shared/ui/Button";
import { useToast } from "@/shared/hooks/useToast";

export interface ZipPluginFormProps {
  onInstallZip?: (file: File) => Promise<void>;
  onClose: () => void;
}

export const ZipPluginForm: React.FC<ZipPluginFormProps> = ({ onInstallZip, onClose }) => {
  const { showToast } = useToast();
  const [zipFile, setZipFile] = useState<File | null>(null);
  const [isUploadingZip, setIsUploadingZip] = useState<boolean>(false);

  const handleZipSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!zipFile || !onInstallZip || isUploadingZip) return;

    setIsUploadingZip(true);
    try {
      await onInstallZip(zipFile);
      showToast("Plugin ZIP uploaded and certified successfully!", "success");
      onClose();
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : "Failed to install plugin from ZIP", "error");
    } finally {
      setIsUploadingZip(false);
    }
  };

  return (
    <form onSubmit={handleZipSubmit} className="space-y-4 pt-2">
      <div className="p-6 border-2 border-dashed border-slate-300 dark:border-slate-700 rounded-xl text-center">
        <Upload className="h-8 w-8 mx-auto text-indigo-500 mb-2" />
        <p className="text-xs text-slate-600 dark:text-slate-400 mb-2">Upload a packaged .zip plugin archive</p>
        <input
          type="file"
          accept=".zip"
          onChange={(e) => setZipFile(e.target.files?.[0] || null)}
          className="text-xs text-slate-600 dark:text-slate-400"
        />
      </div>
      <div className="flex justify-end space-x-2">
        <Button variant="secondary" onClick={onClose}>
          Cancel
        </Button>
        <Button type="submit" disabled={!zipFile} isLoading={isUploadingZip}>
          Upload &amp; Install ZIP
        </Button>
      </div>
    </form>
  );
};
