"use client";

import React from "react";
import { Shield } from "lucide-react";
import { PluginProfileResponse, RuleResponse, RuleSeverity, RuleType } from "@/types";
import { Modal } from "@/shared/ui/Modal";
import { Button } from "@/shared/ui/Button";
import { cn } from "@/lib/utils";

export interface RuleModalProps {
  isOpen: boolean;
  onClose: () => void;
  editingRule: RuleResponse | null;
  ruleId: string;
  setRuleId: (val: string) => void;
  ruleName: string;
  setRuleName: (val: string) => void;
  ruleTargetId: string;
  setRuleTargetId: (val: string) => void;
  ruleType: RuleType;
  setRuleType: (val: RuleType) => void;
  severity: RuleSeverity;
  setSeverity: (val: RuleSeverity) => void;
  expression: string;
  setExpression: (val: string) => void;
  description: string;
  setDescription: (val: string) => void;
  onSubmit: (e: React.FormEvent) => Promise<void>;
  plugins: PluginProfileResponse[];
}

export const RuleModal: React.FC<RuleModalProps> = ({
  isOpen,
  onClose,
  editingRule,
  ruleId,
  setRuleId,
  ruleName,
  setRuleName,
  ruleTargetId,
  setRuleTargetId,
  ruleType,
  setRuleType,
  severity,
  setSeverity,
  expression,
  setExpression,
  description,
  setDescription,
  onSubmit,
  plugins,
}) => {
  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={editingRule ? `Edit Governance Rule: #${editingRule.id}` : "Create Governance Rule"}
      subtitle="Define query restrictions enforced during dry-run inspection"
      icon={<Shield className="h-5 w-5" />}
      maxWidth="md"
    >
      <form onSubmit={onSubmit} className="space-y-3.5">
        <div>
          <label className="block text-[11px] font-semibold text-slate-700 dark:text-slate-400 uppercase tracking-wider mb-1">
            Rule ID{" "}
            {editingRule && (
              <span className="text-[10px] text-slate-500 lowercase">(read-only)</span>
            )}
          </label>
          <input
            type="text"
            required
            disabled={Boolean(editingRule)}
            value={ruleId}
            onChange={(e) => setRuleId(e.target.value)}
            placeholder="e.g. rule_no_cross_join"
            className={cn(
              "w-full border rounded-lg px-3 py-1.5 text-xs font-mono focus:outline-none focus:border-indigo-500",
              editingRule
                ? "bg-slate-100 dark:bg-slate-950/60 border-slate-300 dark:border-slate-800 text-slate-500 cursor-not-allowed"
                : "bg-white dark:bg-slate-950 border-slate-300 dark:border-slate-800 text-slate-900 dark:text-slate-100"
            )}
          />
        </div>

        <div>
          <label className="block text-[11px] font-semibold text-slate-700 dark:text-slate-400 uppercase tracking-wider mb-1">
            Rule Name
          </label>
          <input
            type="text"
            required
            value={ruleName}
            onChange={(e) => setRuleName(e.target.value)}
            placeholder="e.g. Forbid Orders & AuditLogs Join"
            className="w-full bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-900 dark:text-slate-100 focus:outline-none focus:border-indigo-500"
          />
        </div>

        {/* Target Scope Selection */}
        <div>
          <label className="block text-[11px] font-semibold text-slate-700 dark:text-slate-400 uppercase tracking-wider mb-1">
            Target Scope / Associated Plugin
          </label>
          <select
            data-testid="create-rule-target-select"
            value={ruleTargetId}
            onChange={(e) => setRuleTargetId(e.target.value)}
            className="w-full bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-900 dark:text-slate-100 focus:outline-none focus:border-indigo-500 font-medium cursor-pointer"
          >
            <option value="">Global Scope (Applies to all targets)</option>
            {plugins.map((p) => (
              <option key={p.id} value={p.id}>
                Target: {p.name} ({p.id})
              </option>
            ))}
          </select>
          <p className="text-[10px] text-slate-500 mt-1">
            Select &quot;Global Scope&quot; to enforce across all databases, or assign specifically
            to a database connector.
          </p>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-[11px] font-semibold text-slate-700 dark:text-slate-400 uppercase tracking-wider mb-1">
              Rule Type
            </label>
            <select
              value={ruleType}
              onChange={(e) => setRuleType(e.target.value as RuleType)}
              className="w-full bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-900 dark:text-slate-100 focus:outline-none focus:border-indigo-500"
            >
              <option value="FORBID_JOIN">FORBID_JOIN</option>
              <option value="FORBID_TABLE_SCAN">FORBID_TABLE_SCAN</option>
              <option value="MAX_EXECUTION_TIME">MAX_EXECUTION_TIME</option>
              <option value="CUSTOM">CUSTOM</option>
              <option value="REDACT_FIELD">REDACT_FIELD (blank output)</option>
              <option value="REMOVE_FIELD">REMOVE_FIELD (delete output)</option>
            </select>
          </div>

          <div>
            <label className="block text-[11px] font-semibold text-slate-700 dark:text-slate-400 uppercase tracking-wider mb-1">
              Severity
            </label>
            <select
              value={severity}
              onChange={(e) => setSeverity(e.target.value as RuleSeverity)}
              className="w-full bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-900 dark:text-slate-100 focus:outline-none focus:border-indigo-500"
            >
              <option value="CRITICAL">CRITICAL</option>
              <option value="HIGH">HIGH</option>
              <option value="MEDIUM">MEDIUM</option>
              <option value="LOW">LOW</option>
            </select>
          </div>
        </div>

        <div>
          <label className="block text-[11px] font-semibold text-slate-700 dark:text-slate-400 uppercase tracking-wider mb-1">
            Expression Parameter
          </label>
          <input
            type="text"
            value={expression}
            onChange={(e) => setExpression(e.target.value)}
            placeholder={
              ruleType === "REDACT_FIELD" || ruleType === "REMOVE_FIELD"
                ? "e.g. Password,Salary,SSN (comma-separated field names)"
                : "e.g. Orders,AuditLogs"
            }
            className="w-full bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-900 dark:text-slate-100 font-mono focus:outline-none focus:border-indigo-500"
          />
          {(ruleType === "REDACT_FIELD" || ruleType === "REMOVE_FIELD") && (
            <p className="text-[10px] text-slate-500 mt-1">
              {ruleType === "REDACT_FIELD"
                ? "Matching fields stay in the result but their value is set to null before it is stored or sent to the AI."
                : "Matching fields are deleted from the result before it is stored or sent to the AI."}
            </p>
          )}
        </div>

        <div>
          <label className="block text-[11px] font-semibold text-slate-700 dark:text-slate-400 uppercase tracking-wider mb-1">
            Description
          </label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={2}
            placeholder="Why this rule must be enforced..."
            className="w-full bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-800 rounded-lg p-2.5 text-xs text-slate-900 dark:text-slate-100 focus:outline-none focus:border-indigo-500 resize-none"
          />
        </div>

        <div className="flex space-x-2 pt-2 border-t border-slate-200 dark:border-slate-800">
          <Button variant="secondary" onClick={onClose} className="w-1/2">
            Cancel
          </Button>
          <Button type="submit" data-testid="submit-create-rule-btn" className="w-1/2">
            {editingRule ? "Save Rule Changes" : "Save Rule"}
          </Button>
        </div>
      </form>
    </Modal>
  );
};
