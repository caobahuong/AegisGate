"use client";

import React from "react";
import {
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Play,
  RotateCw,
  StopCircle,
  XCircle,
} from "lucide-react";
import { ExecutionResponse } from "@/types";
import { Button } from "@/shared/ui/Button";

export interface GatekeeperControlsPaneProps {
  selectedExecution: ExecutionResponse | null;
  actionLoading?: boolean;
  onApprove: (id: string) => Promise<void>;
  onReject: (id: string) => Promise<void>;
  onAbort: (id: string) => Promise<void>;
}

const renderStatusBadge = (status: string) => {
  switch (status) {
    case "PAUSED_FOR_REVIEW":
      return (
        <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded text-xs font-semibold bg-amber-500/15 text-amber-700 dark:text-amber-400 border border-amber-500/30 animate-pulse">
          <Clock className="h-3 w-3 mr-1" /> PAUSED FOR REVIEW
        </span>
      );
    case "QUEUED":
      return (
        <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded text-xs font-semibold bg-indigo-500/15 text-indigo-700 dark:text-indigo-400 border border-indigo-500/30">
          <Clock className="h-3 w-3 mr-1" /> QUEUED
        </span>
      );
    case "EXECUTING":
      return (
        <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded text-xs font-semibold bg-indigo-500/15 text-indigo-700 dark:text-indigo-400 border border-indigo-500/30 animate-pulse">
          <RotateCw className="h-3 w-3 mr-1 animate-spin" /> EXECUTING
        </span>
      );
    case "COMPLETED":
      return (
        <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded text-xs font-semibold bg-emerald-500/15 text-emerald-700 dark:text-emerald-400 border border-emerald-500/30">
          <CheckCircle2 className="h-3 w-3 mr-1" /> COMPLETED
        </span>
      );
    case "REJECTED":
      return (
        <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded text-xs font-semibold bg-red-500/15 text-red-700 dark:text-red-400 border border-red-500/30">
          <XCircle className="h-3 w-3 mr-1" /> REJECTED
        </span>
      );
    case "TIMEOUT":
      return (
        <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded text-xs font-semibold bg-red-500/15 text-red-700 dark:text-red-400 border border-red-500/30">
          <AlertTriangle className="h-3 w-3 mr-1" /> TIMEOUT (KILLED)
        </span>
      );
    case "ABORTED":
      return (
        <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded text-xs font-semibold bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-400 border border-slate-300 dark:border-slate-700">
          <StopCircle className="h-3 w-3 mr-1" /> ABORTED
        </span>
      );
    case "FAILED":
      return (
        <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded text-xs font-semibold bg-red-500/15 text-red-700 dark:text-red-400 border border-red-500/30">
          <AlertCircle className="h-3 w-3 mr-1" /> FAILED
        </span>
      );
    default:
      return (
        <span className="inline-flex items-center space-x-1 px-2.5 py-1 rounded text-xs font-semibold bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
          {status}
        </span>
      );
  }
};

export const GatekeeperControlsPane: React.FC<GatekeeperControlsPaneProps> = ({
  selectedExecution,
  actionLoading = false,
  onApprove,
  onReject,
  onAbort,
}) => {
  return (
    <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 space-y-5 shadow-sm">
      <div className="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-slate-800">
        <h2 className="text-xs font-bold uppercase tracking-wider text-slate-800 dark:text-slate-200">
          3. Gatekeeper Controls
        </h2>
        {selectedExecution && renderStatusBadge(selectedExecution.status)}
      </div>

      {!selectedExecution ? (
        <div className="py-16 text-center text-slate-400 dark:text-slate-500 text-xs">
          No active session selected.
        </div>
      ) : (
        <div className="space-y-5">
          {/* Session Meta Card */}
          <div className="bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg p-3 space-y-2 text-xs">
            <div className="flex justify-between">
              <span className="text-slate-500">Execution ID:</span>
              <span className="font-mono text-slate-900 dark:text-slate-200 font-bold">
                #{selectedExecution.id}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Mode:</span>
              <span className="text-slate-800 dark:text-slate-200 font-medium">
                {selectedExecution.auto_approved ? "Auto Approval ON" : "Manual Approval"}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Database SPID:</span>
              <span className="font-mono text-slate-800 dark:text-slate-200">
                {selectedExecution.spid ? selectedExecution.spid : "None allocated"}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Duration:</span>
              <span className="font-mono text-indigo-600 dark:text-indigo-400 font-bold">
                {selectedExecution.execution_time_ms !== null
                  ? `${selectedExecution.execution_time_ms} ms`
                  : "Pending"}
              </span>
            </div>
          </div>

          {/* Interactive Control Buttons */}
          <div className="space-y-2.5">
            {selectedExecution.status === "PAUSED_FOR_REVIEW" && (
              <div className="space-y-2">
                <p className="text-xs text-amber-700 dark:text-amber-300 font-medium leading-snug">
                  Plan verified. Query is paused awaiting human approval.
                </p>
                <div className="grid grid-cols-2 gap-2">
                  <Button
                    onClick={() => onApprove(selectedExecution.id)}
                    disabled={actionLoading}
                    isLoading={actionLoading}
                    variant="primary"
                    leftIcon={<Play className="h-3.5 w-3.5" />}
                    className="bg-emerald-600 hover:bg-emerald-500"
                  >
                    Approve &amp; Run
                  </Button>
                  <Button
                    onClick={() => onReject(selectedExecution.id)}
                    disabled={actionLoading}
                    variant="danger"
                    leftIcon={<XCircle className="h-3.5 w-3.5" />}
                  >
                    Reject
                  </Button>
                </div>
              </div>
            )}

            {selectedExecution.status === "EXECUTING" && (
              <div className="space-y-2">
                <div className="flex items-center space-x-2 text-indigo-600 dark:text-indigo-400 text-xs">
                  <RotateCw className="h-4 w-4 animate-spin" />
                  <span>Query running on target database with timeout guard...</span>
                </div>
                <Button
                  onClick={() => onAbort(selectedExecution.id)}
                  disabled={actionLoading}
                  variant="danger"
                  leftIcon={<StopCircle className="h-3.5 w-3.5" />}
                  className="w-full"
                >
                  Stop &amp; KILL Session Now
                </Button>
              </div>
            )}

            {selectedExecution.status === "COMPLETED" && (
              <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 space-y-2">
                <div className="flex items-center space-x-1.5 text-emerald-600 dark:text-emerald-400 text-xs font-bold">
                  <CheckCircle2 className="h-4 w-4" />
                  <span>Execution Successful</span>
                </div>
                <div className="font-mono text-[11px] bg-slate-50 dark:bg-slate-950 p-2 rounded text-slate-800 dark:text-slate-300 max-h-36 overflow-y-auto">
                  <pre className="whitespace-pre-wrap">
                    {selectedExecution.result_summary
                      ? JSON.stringify(selectedExecution.result_summary, null, 2)
                      : "No result payload"}
                  </pre>
                </div>
              </div>
            )}

            {(selectedExecution.status === "REJECTED" ||
              selectedExecution.status === "TIMEOUT" ||
              selectedExecution.status === "ABORTED" ||
              selectedExecution.status === "FAILED") && (
              <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-xs text-red-700 dark:text-red-300 space-y-1">
                <div className="font-bold flex items-center space-x-1 text-red-600 dark:text-red-400">
                  <AlertTriangle className="h-3.5 w-3.5" />
                  <span>Execution Terminated</span>
                </div>
                <p className="text-[11px] leading-relaxed">
                  {selectedExecution.error_message || "No error details reported."}
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
