"use client";

import React from "react";
import { ExecutionResponse } from "@/types";
import { AuditTableRow } from "./AuditTableRow";
import { Button } from "@/shared/ui/Button";

export interface AuditLogsTableProps {
  logs: ExecutionResponse[];
  totalCount: number;
  hasMore: boolean;
  onLoadMore: () => void;
  getPluginName: (targetId: string) => string;
  onSelectLog: (log: ExecutionResponse) => void;
}

export const AuditLogsTable: React.FC<AuditLogsTableProps> = ({
  logs,
  totalCount,
  hasMore,
  onLoadMore,
  getPluginName,
  onSelectLog,
}) => {
  return (
    <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl overflow-hidden shadow-sm">
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-50 dark:bg-slate-950/80 border-b border-slate-200 dark:border-slate-800 text-[10px] font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            <tr>
              <th className="py-3 px-4">Session ID</th>
              <th className="py-3 px-4">Target Plugin</th>
              <th className="py-3 px-4">Input (Statement &amp; Intent)</th>
              <th className="py-3 px-4">Output (Result)</th>
              <th className="py-3 px-4">Status</th>
              <th className="py-3 px-4">Duration</th>
              <th className="py-3 px-4">Timestamp</th>
              <th className="py-3 px-4 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200 dark:divide-slate-800/80">
            {logs.length === 0 ? (
              <tr>
                <td colSpan={8} className="py-12 text-center text-slate-400 dark:text-slate-500 italic">
                  No matching execution logs found.
                </td>
              </tr>
            ) : (
              logs.map((log) => (
                <AuditTableRow
                  key={log.id}
                  log={log}
                  pluginName={getPluginName(log.target_id)}
                  onSelect={onSelectLog}
                />
              ))
            )}
          </tbody>
        </table>
      </div>

      {hasMore && (
        <div className="p-3 border-t border-slate-200 dark:border-slate-800 flex items-center justify-between text-xs text-slate-500">
          <span>
            Showing {logs.length} of {totalCount} logs
          </span>
          <Button variant="secondary" size="sm" onClick={onLoadMore}>
            Load More (50+)
          </Button>
        </div>
      )}
    </div>
  );
};
