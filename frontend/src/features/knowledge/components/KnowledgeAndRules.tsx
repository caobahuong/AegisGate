"use client";

import React from "react";
import { BookOpen, Filter, Shield } from "lucide-react";
import {
  CreateRuleRequest,
  KnowledgeChunkResponse,
  PluginProfileResponse,
  RuleResponse,
  UpdateRuleRequest,
} from "@/types";
import { cn } from "@/lib/utils";
import { useKnowledgeAndRules } from "../hooks/useKnowledgeAndRules";
import { KnowledgeChunksView } from "./KnowledgeChunksView";
import { KnowledgeEditorPane } from "./KnowledgeEditorPane";
import { GovernanceRulesView } from "./GovernanceRulesView";
import { RuleModal } from "./RuleModal";

export interface KnowledgeAndRulesProps {
  chunks: KnowledgeChunkResponse[];
  rules: RuleResponse[];
  plugins?: PluginProfileResponse[];
  onSaveDocs: (chunkId: string, docText: string, skillsText: string) => Promise<void>;
  onCreateRule: (rule: CreateRuleRequest) => Promise<void>;
  onUpdateRule?: (ruleId: string, rule: UpdateRuleRequest) => Promise<void>;
  onDeleteRule: (ruleId: string) => Promise<void>;
}

export const KnowledgeAndRules: React.FC<KnowledgeAndRulesProps> = (props) => {
  const { chunks, rules, plugins = [] } = props;
  const state = useKnowledgeAndRules(props);

  return (
    <div className="space-y-6">
      {/* Top Controls: Sub-tab Navigation + Target Scope Filter Dropdown */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-800 pb-4">
        {/* Sub-tab Switches */}
        <div className="flex items-center space-x-3">
          <button
            onClick={() => state.setActiveSubTab("knowledge")}
            className={cn(
              "flex items-center space-x-2 text-xs font-semibold px-3.5 py-2 rounded-lg transition-colors shadow-xs",
              state.activeSubTab === "knowledge"
                ? "bg-indigo-50 text-indigo-700 border border-indigo-200 dark:bg-indigo-600/20 dark:text-indigo-400 dark:border-indigo-500/30"
                : "text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-800/40"
            )}
          >
            <BookOpen className="h-4 w-4" />
            <span>Knowledge Chunks &amp; Skills ({state.filteredChunks.length})</span>
          </button>
          <button
            onClick={() => state.setActiveSubTab("rules")}
            className={cn(
              "flex items-center space-x-2 text-xs font-semibold px-3.5 py-2 rounded-lg transition-colors shadow-xs",
              state.activeSubTab === "rules"
                ? "bg-indigo-50 text-indigo-700 border border-indigo-200 dark:bg-indigo-600/20 dark:text-indigo-400 dark:border-indigo-500/30"
                : "text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-800/40"
            )}
          >
            <Shield className="h-4 w-4" />
            <span>Governance Rules ({state.filteredRules.length})</span>
          </button>
        </div>

        {/* Global Target Scope Filter Dropdown */}
        <div className="flex items-center space-x-2.5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 px-3.5 py-1.5 rounded-xl shadow-sm">
          <Filter className="h-3.5 w-3.5 text-indigo-500 dark:text-indigo-400 flex-shrink-0" />
          <span className="text-xs text-slate-500 dark:text-slate-400 font-medium whitespace-nowrap">
            Target Scope:
          </span>
          <select
            data-testid="target-filter-select"
            value={state.targetFilter}
            onChange={(e) => state.setTargetFilter(e.target.value)}
            className="bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 rounded-lg px-2.5 py-1 text-xs text-slate-900 dark:text-slate-100 font-medium focus:outline-none focus:border-indigo-500 cursor-pointer"
          >
            <option value="all">
              All Pluggable Targets ({chunks.length} chunks, {rules.length} rules)
            </option>
            <option value="global">
              Global Scope Only ({rules.filter((r) => !r.target_id).length} rules)
            </option>
            {plugins.map((p) => (
              <option key={p.id} value={p.id}>
                Target: {p.name} ({p.id})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Sub-tab 1: Knowledge Chunks & Markdown Docs */}
      {state.activeSubTab === "knowledge" && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <KnowledgeChunksView
            chunks={state.filteredChunks}
            selectedChunk={state.selectedChunk}
            onSelectChunk={state.setSelectedChunkId}
            getPluginName={state.getPluginName}
          />
          <KnowledgeEditorPane
            selectedChunk={state.selectedChunk}
            docContent={state.docContent}
            setDocContent={state.setDocContent}
            skillsContent={state.skillsContent}
            setSkillsContent={state.setSkillsContent}
            isSavingDocs={state.isSavingDocs}
            saveSuccess={state.saveSuccess}
            onSaveDocs={state.handleSaveDocs}
            getPluginName={state.getPluginName}
          />
        </div>
      )}

      {/* Sub-tab 2: Governance Rules */}
      {state.activeSubTab === "rules" && (
        <GovernanceRulesView
          rules={state.filteredRules}
          onOpenCreateRule={state.handleOpenCreateRule}
          onOpenEditRule={state.handleOpenEditRule}
          onDeleteRule={state.onDeleteRule}
          getPluginName={state.getPluginName}
        />
      )}

      {/* Create / Edit Rule Modal */}
      <RuleModal
        isOpen={state.showRuleModal}
        onClose={() => state.setShowRuleModal(false)}
        editingRule={state.editingRule}
        ruleId={state.ruleId}
        setRuleId={state.setRuleId}
        ruleName={state.ruleName}
        setRuleName={state.setRuleName}
        ruleTargetId={state.ruleTargetId}
        setRuleTargetId={state.setRuleTargetId}
        ruleType={state.ruleType}
        setRuleType={state.setRuleType}
        severity={state.severity}
        setSeverity={state.setSeverity}
        expression={state.expression}
        setExpression={state.setExpression}
        description={state.description}
        setDescription={state.setDescription}
        onSubmit={state.handleSubmitRule}
        plugins={plugins}
      />
    </div>
  );
};
