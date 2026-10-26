"use client";

import React from "react";
import { Check, Database, FileCode, FileText, Save } from "lucide-react";
import { KnowledgeChunkResponse } from "@/types";
import { Button } from "@/shared/ui/Button";

export interface KnowledgeEditorPaneProps {
  selectedChunk: KnowledgeChunkResponse | null;
  docContent: string;
  setDocContent: (val: string) => void;
  skillsContent: string;
  setSkillsContent: (val: string) => void;
  isSavingDocs: boolean;
  saveSuccess: boolean;
  onSaveDocs: () => Promise<void>;
  getPluginName: (targetId: string | null | undefined) => string;
}

export const KnowledgeEditorPane: React.FC<KnowledgeEditorPaneProps> = ({
  selectedChunk,
  docContent,
  setDocContent,
  skillsContent,
  setSkillsContent,
  isSavingDocs,
  saveSuccess,
  onSaveDocs,
  getPluginName,
}) => {
  return (
    <div className="lg:col-span-2 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 space-y-4 shadow-sm">
      <div className="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-slate-800">
        <div className="flex items-center space-x-3">
          <div className="h-8 w-8 rounded-lg bg-indigo-50 dark:bg-indigo-600/20 border border-indigo-200 dark:border-indigo-500/30 flex items-center justify-center">
            <FileCode className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />
          </div>
          <div>
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-800 dark:text-slate-200">
              Hybrid Docs &amp; Skills: {selectedChunk?.title || "No partition selected"}
            </h3>
            {selectedChunk && (
              <div className="flex items-center space-x-2 mt-0.5">
                <span className="text-[10px] font-medium text-emerald-600 dark:text-emerald-400 flex items-center space-x-1">
                  <Database className="h-2.5 w-2.5" />
                  <span>Target: {getPluginName(selectedChunk.target_id)}</span>
                </span>
                <span className="text-slate-400 dark:text-slate-600">•</span>
                <span className="text-[10px] font-mono text-slate-500 dark:text-slate-400">
                  Partition: {selectedChunk.partition_key}
                </span>
              </div>
            )}
          </div>
        </div>
        <Button
          onClick={onSaveDocs}
          disabled={isSavingDocs || !selectedChunk}
          isLoading={isSavingDocs}
          variant="primary"
          size="sm"
        >
          {saveSuccess ? (
            <>
              <Check className="h-3.5 w-3.5 text-emerald-300 mr-1" />
              <span>Saved!</span>
            </>
          ) : (
            <>
              <Save className="h-3.5 w-3.5 mr-1" />
              <span>Save Docs &amp; Skills</span>
            </>
          )}
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* doc.md editor */}
        <div className="space-y-2">
          <label className="text-[11px] font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wider flex items-center space-x-1.5">
            <FileText className="h-3.5 w-3.5 text-indigo-500 dark:text-indigo-400" />
            <span>Business Rules &amp; Context (doc.md)</span>
          </label>
          <textarea
            value={docContent}
            onChange={(e) => setDocContent(e.target.value)}
            rows={14}
            className="w-full font-mono text-xs bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-800 rounded-lg p-3 text-slate-900 dark:text-slate-200 focus:outline-none focus:border-indigo-500 leading-relaxed resize-none"
            placeholder="# System Documentation&#10;Detail business context..."
          />
        </div>

        {/* skills.md editor */}
        <div className="space-y-2">
          <label className="text-[11px] font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wider flex items-center space-x-1.5">
            <FileCode className="h-3.5 w-3.5 text-emerald-500 dark:text-emerald-400" />
            <span>Query Skills &amp; Templates (skills.md)</span>
          </label>
          <textarea
            value={skillsContent}
            onChange={(e) => setSkillsContent(e.target.value)}
            rows={14}
            className="w-full font-mono text-xs bg-slate-50 dark:bg-slate-950 border border-slate-300 dark:border-slate-800 rounded-lg p-3 text-slate-900 dark:text-slate-200 focus:outline-none focus:border-indigo-500 leading-relaxed resize-none"
            placeholder="# Standard Skills&#10;Define recommended queries..."
          />
        </div>
      </div>
    </div>
  );
};
