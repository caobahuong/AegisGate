"use client";

import React from "react";
import { Database, Globe, Pencil, Plus, Shield, Trash2 } from "lucide-react";
import { RuleResponse } from "@/types";
import { Button } from "@/shared/ui/Button";
import { cn } from "@/lib/utils";

export interface GovernanceRulesViewProps {
  rules: RuleResponse[];
  onOpenCreateRule: () => void;
  onOpenEditRule: (rule: RuleResponse) => void;
  onDeleteRule?: (ruleId: string) => Promise<void>;
  getPluginName: (targetId: string | null | undefined) => string;
}

export const GovernanceRulesView: React.FC<GovernanceRulesViewProps> = ({
  rules,
  onOpenCreateRule,
  onOpenEditRule,
  onDeleteRule,
  getPluginName,
}) => {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between pb-3 border-b border-slate-200 dark:border-slate-800">
        <div>
          <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center space-x-2">
            <Shield className="h-4 w-4 text-indigo-500 dark:text-indigo-400" />
            <span>Governance &amp; Security Rules</span>
          </h3>
          <p className="text-xs text-slate-600 dark:text-slate-400">
            Active rules enforced during Dry-Run inspection before queries can execute.
          </p>
        </div>
        <Button
          onClick={onOpenCreateRule}
          data-testid="create-rule-btn"
          variant="primary"
          size="sm"
        >
          <Plus className="h-4 w-4 mr-1.5" />
          Create Rule
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {rules.length === 0 ? (
          <div className="col-span-2 p-8 text-center bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl space-y-2">
            <Shield className="h-8 w-8 text-slate-400 dark:text-slate-500 mx-auto" />
            <p className="text-xs font-medium text-slate-700 dark:text-slate-300">
              No governance rules found for this target scope.
            </p>
            <p className="text-[11px] text-slate-500">
              Click &quot;Create Rule&quot; to define query restrictions for this database target or
              globally.
            </p>
          </div>
        ) : (
          rules.map((rule) => (
            <div
              key={rule.id}
              data-testid={`rule-card-${rule.id}`}
              className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 space-y-3 shadow-sm hover:border-slate-300 dark:hover:border-slate-700 transition-colors"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <span
                    className={cn(
                      "text-[10px] font-bold px-2 py-0.5 rounded",
                      rule.severity === "CRITICAL" &&
                        "bg-red-500/20 text-red-600 dark:text-red-400 border border-red-500/30",
                      rule.severity === "HIGH" &&
                        "bg-amber-500/20 text-amber-600 dark:text-amber-400 border border-amber-500/30",
                      rule.severity === "MEDIUM" &&
                        "bg-indigo-500/20 text-indigo-600 dark:text-indigo-400 border border-indigo-500/30",
                      rule.severity === "LOW" &&
                        "bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300"
                    )}
                  >
                    {rule.severity}
                  </span>
                  <h4 className="text-xs font-bold text-slate-900 dark:text-slate-200">
                    {rule.name}
                  </h4>
                </div>

                <div className="flex items-center space-x-1.5">
                  {/* Target Scoping Badge */}
                  {rule.target_id ? (
                    <span
                      data-testid={`rule-target-badge-${rule.id}`}
                      className="text-[10px] font-semibold px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20 flex items-center space-x-1"
                    >
                      <Database className="h-2.5 w-2.5" />
                      <span>Target: {getPluginName(rule.target_id)}</span>
                    </span>
                  ) : (
                    <span
                      data-testid={`rule-target-badge-${rule.id}`}
                      className="text-[10px] font-semibold px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 border border-indigo-500/20 flex items-center space-x-1"
                    >
                      <Globe className="h-2.5 w-2.5" />
                      <span>Global Scope</span>
                    </span>
                  )}

                  {/* Edit Rule Button */}
                  <button
                    onClick={() => onOpenEditRule(rule)}
                    data-testid={`edit-rule-btn-${rule.id}`}
                    aria-label={`Edit Rule ${rule.name}`}
                    className="text-slate-400 hover:text-indigo-600 dark:hover:text-indigo-400 p-1 rounded hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                    title="Edit Rule & Target Scoping"
                  >
                    <Pencil className="h-3.5 w-3.5" />
                  </button>

                  {/* Delete Rule Button */}
                  {onDeleteRule && (
                    <button
                      onClick={() => onDeleteRule(rule.id)}
                      aria-label={`Delete Rule ${rule.name}`}
                      className="text-slate-400 hover:text-red-600 dark:hover:text-red-400 p-1 rounded hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                      title="Delete Rule"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </button>
                  )}
                </div>
              </div>

              <div className="space-y-1.5 text-xs">
                <div>
                  <span className="text-slate-500 text-[10px] font-semibold uppercase block">
                    Rule Type &amp; Parameters
                  </span>
                  <span className="font-mono text-indigo-600 dark:text-indigo-400 font-semibold">
                    {rule.rule_type}
                  </span>
                  <span className="text-slate-400 mx-1.5">|</span>
                  <span className="font-mono text-slate-800 dark:text-slate-300 bg-slate-100 dark:bg-slate-950 px-1.5 py-0.5 rounded border border-slate-200 dark:border-slate-800">
                    {rule.expression || "Global"}
                  </span>
                </div>
                <p className="text-[11px] text-slate-600 dark:text-slate-400 leading-snug">
                  {rule.description}
                </p>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
