"use client";

import React from "react";
import { ShieldCheck, CheckCircle2, AlertTriangle, XCircle, Clock } from "lucide-react";
import { PluginProfileResponse } from "@/types";
import { Modal } from "@/shared/ui/Modal";
import { Button } from "@/shared/ui/Button";

export interface CertificationModalProps {
  isOpen: boolean;
  onClose: () => void;
  plugin: PluginProfileResponse | null;
}

export const CertificationModal: React.FC<CertificationModalProps> = ({
  isOpen,
  onClose,
  plugin,
}) => {
  if (!plugin) return null;

  const report = plugin.certification_report || {};
  const checks =
    (report as { checks?: Record<string, { status?: string; error?: string }> }).checks || {};

  const stages = [
    { key: "handshake", title: "1. Handshake & RPC Ping" },
    { key: "sync_knowledge", title: "2. Sync Knowledge Schema" },
    { key: "dry_run", title: "3. Dry-Run Analysis" },
    { key: "abort", title: "4. Abort Hook Protocol" },
  ];

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Plugin Sanity & Certification Report"
      subtitle={`4-stage automated compatibility validation for #${plugin.id}`}
      icon={<ShieldCheck className="h-5 w-5" />}
      maxWidth="lg"
    >
      <div data-testid="cert-inspect-modal" className="space-y-4">
        {/* Overall Status Banner */}
        <div
          className={`p-3.5 rounded-xl border flex items-center space-x-2.5 text-xs font-semibold ${
            plugin.is_certified
              ? "bg-emerald-50 dark:bg-emerald-500/10 border-emerald-300 dark:border-emerald-500/30 text-emerald-800 dark:text-emerald-400"
              : "bg-amber-50 dark:bg-amber-500/10 border-amber-300 dark:border-amber-500/30 text-amber-800 dark:text-amber-400"
          }`}
        >
          {plugin.is_certified ? (
            <CheckCircle2 className="h-4 w-4 flex-shrink-0" />
          ) : (
            <AlertTriangle className="h-4 w-4 flex-shrink-0" />
          )}
          <span>
            {plugin.is_certified
              ? "Certified: Passed all 4 Stage Compatibility Checks (Ready for Production AI Agents)"
              : "Compatibility Notice: Incomplete or warning checks detected"}
          </span>
        </div>

        {/* 4 Stages List */}
        <div className="space-y-2">
          {stages.map((stage) => {
            const check = checks[stage.key];
            const isPassed = check?.status === "pass" || plugin.is_certified;
            return (
              <div
                key={stage.key}
                className="p-3 rounded-lg border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-950/40 flex items-start justify-between space-x-3 text-xs"
              >
                <div>
                  <span className="font-semibold text-slate-800 dark:text-slate-200 block">
                    {stage.title}
                  </span>
                  {check?.error && (
                    <span className="font-mono text-[11px] text-rose-600 dark:text-rose-400 mt-1 block">
                      {check.error}
                    </span>
                  )}
                </div>
                <div className="flex items-center space-x-1.5 flex-shrink-0">
                  {isPassed ? (
                    <span className="inline-flex items-center text-[10px] font-bold text-emerald-700 dark:text-emerald-400 bg-emerald-100 dark:bg-emerald-500/20 px-2 py-0.5 rounded">
                      <CheckCircle2 className="h-3 w-3 mr-1" /> PASS
                    </span>
                  ) : check?.status === "fail" ? (
                    <span className="inline-flex items-center text-[10px] font-bold text-rose-700 dark:text-rose-400 bg-rose-100 dark:bg-rose-500/20 px-2 py-0.5 rounded">
                      <XCircle className="h-3 w-3 mr-1" /> FAIL
                    </span>
                  ) : (
                    <span className="inline-flex items-center text-[10px] font-medium text-slate-500 bg-slate-200 dark:bg-slate-800 px-2 py-0.5 rounded">
                      <Clock className="h-3 w-3 mr-1" /> UNCHECKED
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>

        <div className="flex justify-end pt-2 border-t border-slate-200 dark:border-slate-800">
          <Button variant="secondary" size="sm" onClick={onClose}>
            Close Report
          </Button>
        </div>
      </div>
    </Modal>
  );
};
