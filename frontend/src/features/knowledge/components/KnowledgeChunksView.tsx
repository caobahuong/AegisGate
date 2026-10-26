"use client";

import React from "react";
import { Database, Table } from "lucide-react";
import { KnowledgeChunkResponse } from "@/types";
import { cn } from "@/lib/utils";

export interface KnowledgeChunksViewProps {
  chunks: KnowledgeChunkResponse[];
  selectedChunk: KnowledgeChunkResponse | null;
  onSelectChunk: (chunkId: string) => void;
  getPluginName: (targetId: string | null | undefined) => string;
}

export const KnowledgeChunksView: React.FC<KnowledgeChunksViewProps> = ({
  chunks,
  selectedChunk,
  onSelectChunk,
  getPluginName,
}) => {
  return (
    <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 space-y-4 shadow-sm">
      <div className="flex items-center justify-between pb-2 border-b border-slate-200 dark:border-slate-800">
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300 flex items-center space-x-2">
          <Table className="h-4 w-4 text-indigo-500 dark:text-indigo-400" />
          <span>Partitioned Knowledge Chunks</span>
        </h3>
        <span className="text-[10px] text-slate-500 font-mono">
          {chunks.length} item{chunks.length === 1 ? "" : "s"}
        </span>
      </div>

      <div className="space-y-2 max-h-[420px] overflow-y-auto">
        {chunks.length === 0 ? (
          <div className="p-4 text-center space-y-1 bg-slate-50 dark:bg-slate-950/40 rounded-lg border border-slate-200 dark:border-slate-800/60">
            <p className="text-xs text-slate-600 dark:text-slate-400">
              No knowledge chunks found for this target scope.
            </p>
            <p className="text-[11px] text-slate-500">
              Go to Pluggable Targets and click &quot;Sync Catalog&quot; to extract schema
              partitions.
            </p>
          </div>
        ) : (
          chunks.map((chunk) => (
            <button
              key={chunk.id}
              onClick={() => onSelectChunk(chunk.id)}
              className={cn(
                "w-full text-left p-3 rounded-lg border transition-all duration-150 space-y-1.5",
                selectedChunk?.id === chunk.id
                  ? "bg-indigo-50/70 dark:bg-indigo-600/15 border-indigo-300 dark:border-indigo-500/40 text-slate-900 dark:text-slate-100 ring-1 ring-indigo-500/20"
                  : "bg-slate-50 dark:bg-slate-950/60 border-slate-200 dark:border-slate-800/80 text-slate-700 dark:text-slate-400 hover:border-slate-300 dark:hover:border-slate-700"
              )}
            >
              <div className="flex justify-between items-center">
                <span className="text-xs font-bold text-slate-900 dark:text-slate-200">
                  {chunk.title}
                </span>
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-400 border border-slate-300 dark:border-slate-700">
                  {chunk.partition_key}
                </span>
              </div>

              {/* Target Association Badge */}
              <div className="flex items-center space-x-1.5">
                <span
                  data-testid={`chunk-target-badge-${chunk.id}`}
                  className="text-[10px] font-semibold px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 flex items-center space-x-1"
                >
                  <Database className="h-2.5 w-2.5 flex-shrink-0" />
                  <span className="truncate max-w-[160px]">
                    Target: {getPluginName(chunk.target_id)}
                  </span>
                </span>
              </div>
            </button>
          ))
        )}
      </div>

      {/* Selected Chunk Schema Preview */}
      {selectedChunk && (
        <div className="pt-2 border-t border-slate-200 dark:border-slate-800 space-y-2">
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 block">
            Cached Schema Metadata (Zero-Touch AI)
          </span>
          <div className="bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded p-2.5 max-h-56 overflow-y-auto font-mono text-[11px] text-slate-800 dark:text-slate-300">
            <pre className="whitespace-pre-wrap">
              {JSON.stringify(selectedChunk.catalog, null, 2)}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
};
