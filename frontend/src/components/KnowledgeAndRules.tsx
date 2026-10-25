"use client";

import React, { useState } from "react";
import {
  BookOpen,
  Check,
  Database,
  FileCode,
  FileText,
  Filter,
  Globe,
  Pencil,
  Plus,
  Save,
  Shield,
  Trash2,
  Table,
} from "lucide-react";
import {
  CreateRuleRequest,
  KnowledgeChunkResponse,
  PluginProfileResponse,
  RuleResponse,
  RuleSeverity,
  RuleType,
  UpdateRuleRequest,
} from "@/types";
import { cn } from "@/lib/utils";

interface KnowledgeAndRulesProps {
  chunks: KnowledgeChunkResponse[];
  rules: RuleResponse[];
  plugins?: PluginProfileResponse[];
  onSaveDocs: (chunkId: string, docText: string, skillsText: string) => Promise<void>;
  onCreateRule: (rule: CreateRuleRequest) => Promise<void>;
  onUpdateRule?: (ruleId: string, rule: UpdateRuleRequest) => Promise<void>;
  onDeleteRule: (ruleId: string) => Promise<void>;
}

export const KnowledgeAndRules: React.FC<KnowledgeAndRulesProps> = ({
  chunks,
  rules,
  plugins = [],
  onSaveDocs,
  onCreateRule,
  onUpdateRule,
  onDeleteRule,
}) => {
  const [activeSubTab, setActiveSubTab] = useState<"knowledge" | "rules">("knowledge");
  const [targetFilter, setTargetFilter] = useState<string>("all");

  // Filtered collections based on target scope
  const filteredChunks = chunks.filter((c) => {
    if (targetFilter === "all") return true;
    if (targetFilter === "global") return false;
    return c.target_id === targetFilter;
  });

  const filteredRules = rules.filter((r) => {
    if (targetFilter === "all") return true;
    if (targetFilter === "global") return !r.target_id;
    return r.target_id === targetFilter;
  });

  // Knowledge State
  const [selectedChunkId, setSelectedChunkId] = useState<string>(
    filteredChunks[0]?.id || chunks[0]?.id || ""
  );
  const selectedChunk =
    filteredChunks.find((c) => c.id === selectedChunkId) || filteredChunks[0] || chunks[0];
  const [docContent, setDocContent] = useState<string>(selectedChunk?.doc_content || "");
  const [skillsContent, setSkillsContent] = useState<string>(selectedChunk?.skills_content || "");
  const [isSavingDocs, setIsSavingDocs] = useState<boolean>(false);
  const [saveSuccess, setSaveSuccess] = useState<boolean>(false);

  // Update editor when selectedChunk changes
  React.useEffect(() => {
    if (selectedChunk) {
      setDocContent(selectedChunk.doc_content || "");
      setSkillsContent(selectedChunk.skills_content || "");
    }
  }, [selectedChunk]);

  // Rule Form State
  const [showRuleModal, setShowRuleModal] = useState<boolean>(false);
  const [editingRule, setEditingRule] = useState<RuleResponse | null>(null);
  const [ruleId, setRuleId] = useState<string>("");
  const [ruleName, setRuleName] = useState<string>("");
  const [ruleTargetId, setRuleTargetId] = useState<string>(
    targetFilter !== "all" && targetFilter !== "global" ? targetFilter : ""
  );
  const [ruleType, setRuleType] = useState<RuleType>("FORBID_JOIN");
  const [expression, setExpression] = useState<string>("");
  const [description, setDescription] = useState<string>("");
  const [severity, setSeverity] = useState<RuleSeverity>("HIGH");

  const handleSaveDocs = async () => {
    if (!selectedChunk) return;
    setIsSavingDocs(true);
    setSaveSuccess(false);
    try {
      await onSaveDocs(selectedChunk.id, docContent, skillsContent);
      setSaveSuccess(true);
      setTimeout(() => setSaveSuccess(false), 3000);
    } finally {
      setIsSavingDocs(false);
    }
  };

  const handleOpenCreateRule = () => {
    setEditingRule(null);
    setRuleId("");
    setRuleName("");
    setRuleTargetId(targetFilter !== "all" && targetFilter !== "global" ? targetFilter : "");
    setRuleType("FORBID_JOIN");
    setExpression("");
    setDescription("");
    setSeverity("HIGH");
    setShowRuleModal(true);
  };

  const handleOpenEditRule = (rule: RuleResponse) => {
    setEditingRule(rule);
    setRuleId(rule.id);
    setRuleName(rule.name);
    setRuleTargetId(rule.target_id || "");
    setRuleType(rule.rule_type);
    setExpression(rule.expression || "");
    setDescription(rule.description || "");
    setSeverity(rule.severity);
    setShowRuleModal(true);
  };

  const handleSubmitRule = async (e: React.FormEvent) => {
    e.preventDefault();
    if (editingRule) {
      if (!onUpdateRule) return;
      await onUpdateRule(editingRule.id, {
        name: ruleName.trim(),
        target_id: ruleTargetId.trim() ? ruleTargetId.trim() : null,
        rule_type: ruleType,
        expression: expression.trim(),
        description: description.trim(),
        severity,
        is_active: true,
      });
    } else {
      if (!ruleId || !ruleName) return;
      await onCreateRule({
        id: ruleId.trim(),
        name: ruleName.trim(),
        target_id: ruleTargetId.trim() ? ruleTargetId.trim() : null,
        rule_type: ruleType,
        expression: expression.trim(),
        description: description.trim(),
        severity,
        is_active: true,
      });
    }
    setShowRuleModal(false);
    setEditingRule(null);
    setRuleId("");
    setRuleName("");
    setRuleTargetId("");
    setExpression("");
    setDescription("");
  };

  const getPluginName = (targetId: string | null | undefined): string => {
    if (!targetId) return "Global";
    const found = plugins.find((p) => p.id === targetId);
    return found ? found.name : targetId;
  };

  return (
    <div className="space-y-6">
      {/* Top Controls: Sub-tab Navigation + Target Scope Filter Dropdown */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        {/* Sub-tab Switches */}
        <div className="flex items-center space-x-3">
          <button
            onClick={() => setActiveSubTab("knowledge")}
            className={cn(
              "flex items-center space-x-2 text-xs font-semibold px-3.5 py-2 rounded-lg transition-colors shadow-xs",
              activeSubTab === "knowledge"
                ? "bg-indigo-50 text-indigo-700 border border-indigo-200 dark:bg-indigo-600/20 dark:text-indigo-400 dark:border-indigo-500/30"
                : "text-slate-400 hover:text-slate-100 hover:bg-slate-800/40"
            )}
          >
            <BookOpen className="h-4 w-4" />
            <span>Knowledge Chunks &amp; Skills ({filteredChunks.length})</span>
          </button>
          <button
            onClick={() => setActiveSubTab("rules")}
            className={cn(
              "flex items-center space-x-2 text-xs font-semibold px-3.5 py-2 rounded-lg transition-colors shadow-xs",
              activeSubTab === "rules"
                ? "bg-indigo-50 text-indigo-700 border border-indigo-200 dark:bg-indigo-600/20 dark:text-indigo-400 dark:border-indigo-500/30"
                : "text-slate-400 hover:text-slate-100 hover:bg-slate-800/40"
            )}
          >
            <Shield className="h-4 w-4" />
            <span>Governance Rules ({filteredRules.length})</span>
          </button>
        </div>

        {/* Global Target Scope Filter Dropdown */}
        <div className="flex items-center space-x-2.5 bg-slate-900 border border-slate-800 px-3.5 py-1.5 rounded-xl shadow-sm">
          <Filter className="h-3.5 w-3.5 text-indigo-400 flex-shrink-0" />
          <span className="text-xs text-slate-400 font-medium whitespace-nowrap">
            Target Scope:
          </span>
          <select
            data-testid="target-filter-select"
            value={targetFilter}
            onChange={(e) => setTargetFilter(e.target.value)}
            className="bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1 text-xs text-slate-100 font-medium focus:outline-none focus:border-indigo-500 cursor-pointer"
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

      {/* ========================================================
          SUB-TAB 1: Knowledge Chunks & Markdown Docs
         ======================================================== */}
      {activeSubTab === "knowledge" && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Partitions List & Schema Viewer */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-4 shadow-sm">
            <div className="flex items-center justify-between pb-2 border-b border-slate-800">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center space-x-2">
                <Table className="h-4 w-4 text-indigo-400" />
                <span>Partitioned Knowledge Chunks</span>
              </h3>
              <span className="text-[10px] text-slate-500 font-mono">
                {filteredChunks.length} item{filteredChunks.length === 1 ? "" : "s"}
              </span>
            </div>

            <div className="space-y-2">
              {filteredChunks.length === 0 ? (
                <div className="p-4 text-center space-y-1 bg-slate-950/40 rounded-lg border border-slate-800/60">
                  <p className="text-xs text-slate-400">
                    No knowledge chunks found for this target scope.
                  </p>
                  <p className="text-[11px] text-slate-500">
                    Go to Pluggable Targets and click &quot;Sync Catalog&quot; to extract schema
                    partitions.
                  </p>
                </div>
              ) : (
                filteredChunks.map((chunk) => (
                  <button
                    key={chunk.id}
                    onClick={() => setSelectedChunkId(chunk.id)}
                    className={cn(
                      "w-full text-left p-3 rounded-lg border transition-all duration-150 space-y-1.5",
                      selectedChunk?.id === chunk.id
                        ? "bg-indigo-600/15 border-indigo-500/40 text-slate-100 ring-1 ring-indigo-500/20"
                        : "bg-slate-950/60 border-slate-800/80 text-slate-400 hover:border-slate-700"
                    )}
                  >
                    <div className="flex justify-between items-center">
                      <span className="text-xs font-bold text-slate-200">{chunk.title}</span>
                      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                        {chunk.partition_key}
                      </span>
                    </div>

                    {/* Target Association Badge */}
                    <div className="flex items-center space-x-1.5">
                      <span
                        data-testid={`chunk-target-badge-${chunk.id}`}
                        className="text-[10px] font-semibold px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center space-x-1"
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
              <div className="pt-2 border-t border-slate-800 space-y-2">
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
                  Cached Schema Metadata (Zero-Touch AI)
                </span>
                <div className="bg-slate-950 border border-slate-800 rounded p-2.5 max-h-56 overflow-y-auto font-mono text-[11px] text-slate-300">
                  <pre className="whitespace-pre-wrap">
                    {JSON.stringify(selectedChunk.catalog, null, 2)}
                  </pre>
                </div>
              </div>
            )}
          </div>

          {/* Markdown Docs & Skills Editor */}
          <div className="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4 shadow-sm">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center space-x-3">
                <div className="h-8 w-8 rounded-lg bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center">
                  <FileCode className="h-4 w-4 text-indigo-400" />
                </div>
                <div>
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200">
                    Hybrid Docs & Skills: {selectedChunk?.title || "No partition selected"}
                  </h3>
                  {selectedChunk && (
                    <div className="flex items-center space-x-2 mt-0.5">
                      <span className="text-[10px] font-medium text-emerald-400 flex items-center space-x-1">
                        <Database className="h-2.5 w-2.5" />
                        <span>Target: {getPluginName(selectedChunk.target_id)}</span>
                      </span>
                      <span className="text-slate-600">•</span>
                      <span className="text-[10px] font-mono text-slate-400">
                        Partition: {selectedChunk.partition_key}
                      </span>
                    </div>
                  )}
                </div>
              </div>
              <button
                onClick={handleSaveDocs}
                disabled={isSavingDocs || !selectedChunk}
                className="flex items-center space-x-1.5 bg-indigo-600 hover:bg-indigo-500 text-white px-3 py-1.5 rounded-lg text-xs font-semibold shadow-md shadow-indigo-600/30 transition-colors disabled:opacity-50"
              >
                {saveSuccess ? (
                  <>
                    <Check className="h-3.5 w-3.5 text-emerald-300" />
                    <span>Saved!</span>
                  </>
                ) : (
                  <>
                    <Save className="h-3.5 w-3.5" />
                    <span>{isSavingDocs ? "Saving..." : "Save Docs & Skills"}</span>
                  </>
                )}
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* doc.md editor */}
              <div className="space-y-2">
                <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider flex items-center space-x-1.5">
                  <FileText className="h-3.5 w-3.5 text-indigo-400" />
                  <span>Business Rules & Context (doc.md)</span>
                </label>
                <textarea
                  value={docContent}
                  onChange={(e) => setDocContent(e.target.value)}
                  rows={14}
                  className="w-full font-mono text-xs bg-slate-950 border border-slate-800 rounded-lg p-3 text-slate-200 focus:outline-none focus:border-indigo-500 leading-relaxed resize-none"
                  placeholder="# System Documentation&#10;Detail business context..."
                />
              </div>

              {/* skills.md editor */}
              <div className="space-y-2">
                <label className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider flex items-center space-x-1.5">
                  <FileCode className="h-3.5 w-3.5 text-emerald-400" />
                  <span>Query Skills & Templates (skills.md)</span>
                </label>
                <textarea
                  value={skillsContent}
                  onChange={(e) => setSkillsContent(e.target.value)}
                  rows={14}
                  className="w-full font-mono text-xs bg-slate-950 border border-slate-800 rounded-lg p-3 text-slate-200 focus:outline-none focus:border-indigo-500 leading-relaxed resize-none"
                  placeholder="# Standard Skills&#10;Define recommended queries..."
                />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ========================================================
          SUB-TAB 2: Governance Rules
         ======================================================== */}
      {activeSubTab === "rules" && (
        <div className="space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <div>
              <h3 className="text-sm font-bold text-slate-100 flex items-center space-x-2">
                <Shield className="h-4 w-4 text-indigo-400" />
                <span>Governance & Security Rules</span>
              </h3>
              <p className="text-xs text-slate-400">
                Active rules enforced during Dry-Run inspection before queries can execute.
              </p>
            </div>
            <button
              onClick={handleOpenCreateRule}
              data-testid="create-rule-btn"
              className="flex items-center space-x-2 bg-indigo-600 hover:bg-indigo-500 text-white px-3.5 py-1.5 rounded-lg text-xs font-semibold shadow-md shadow-indigo-600/30 transition-colors"
            >
              <Plus className="h-4 w-4" />
              <span>Create Rule</span>
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {filteredRules.length === 0 ? (
              <div className="col-span-2 p-8 text-center bg-slate-900 border border-slate-800 rounded-xl space-y-2">
                <Shield className="h-8 w-8 text-slate-500 mx-auto" />
                <p className="text-xs font-medium text-slate-300">
                  No governance rules found for this target scope.
                </p>
                <p className="text-[11px] text-slate-500">
                  Click &quot;Create Rule&quot; to define query restrictions for this database
                  target or globally.
                </p>
              </div>
            ) : (
              filteredRules.map((rule) => (
                <div
                  key={rule.id}
                  data-testid={`rule-card-${rule.id}`}
                  className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3 shadow-sm hover:border-slate-700 transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <span
                        className={cn(
                          "text-[10px] font-bold px-2 py-0.5 rounded",
                          rule.severity === "CRITICAL" &&
                            "bg-red-500/20 text-red-400 border border-red-500/30",
                          rule.severity === "HIGH" &&
                            "bg-amber-500/20 text-amber-400 border border-amber-500/30",
                          rule.severity === "MEDIUM" &&
                            "bg-indigo-500/20 text-indigo-400 border border-indigo-500/30",
                          rule.severity === "LOW" && "bg-slate-800 text-slate-300"
                        )}
                      >
                        {rule.severity}
                      </span>
                      <h4 className="text-xs font-bold text-slate-200">{rule.name}</h4>
                    </div>

                    <div className="flex items-center space-x-1.5">
                      {/* Target Scoping Badge */}
                      {rule.target_id ? (
                        <span
                          data-testid={`rule-target-badge-${rule.id}`}
                          className="text-[10px] font-semibold px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center space-x-1"
                        >
                          <Database className="h-2.5 w-2.5" />
                          <span>Target: {getPluginName(rule.target_id)}</span>
                        </span>
                      ) : (
                        <span
                          data-testid={`rule-target-badge-${rule.id}`}
                          className="text-[10px] font-semibold px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 flex items-center space-x-1"
                        >
                          <Globe className="h-2.5 w-2.5" />
                          <span>Global Scope</span>
                        </span>
                      )}

                      {/* Edit Rule Button */}
                      <button
                        onClick={() => handleOpenEditRule(rule)}
                        data-testid={`edit-rule-btn-${rule.id}`}
                        className="text-slate-500 hover:text-indigo-400 p-1 rounded hover:bg-slate-800 transition-colors"
                        title="Edit Rule & Target Scoping"
                      >
                        <Pencil className="h-3.5 w-3.5" />
                      </button>

                      {/* Delete Rule Button */}
                      <button
                        onClick={() => onDeleteRule(rule.id)}
                        className="text-slate-500 hover:text-red-400 p-1 rounded hover:bg-slate-800 transition-colors"
                        title="Delete Rule"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </button>
                    </div>
                  </div>

                  <div className="space-y-1.5 text-xs">
                    <div>
                      <span className="text-slate-500 text-[10px] font-semibold uppercase block">
                        Rule Type & Parameters
                      </span>
                      <span className="font-mono text-indigo-400 font-semibold">
                        {rule.rule_type}
                      </span>
                      <span className="text-slate-400 mx-1.5">|</span>
                      <span className="font-mono text-slate-300 bg-slate-950 px-1.5 py-0.5 rounded border border-slate-800">
                        {rule.expression || "Global"}
                      </span>
                    </div>
                    <p className="text-[11px] text-slate-400 leading-snug">{rule.description}</p>
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Add / Edit Rule Modal */}
          {showRuleModal && (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 animate-in fade-in duration-150">
              <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
                <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                  <h3 className="text-sm font-bold text-slate-100 flex items-center space-x-2">
                    <Shield className="h-4 w-4 text-indigo-400" />
                    <span>
                      {editingRule
                        ? `Edit Governance Rule: #${editingRule.id}`
                        : "Create Governance Rule"}
                    </span>
                  </h3>
                  <button
                    onClick={() => {
                      setShowRuleModal(false);
                      setEditingRule(null);
                    }}
                    className="text-slate-400 hover:text-slate-200 text-xs"
                  >
                    Cancel
                  </button>
                </div>

                <form onSubmit={handleSubmitRule} className="space-y-3.5">
                  <div>
                    <label className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">
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
                          ? "bg-slate-950/60 border-slate-800 text-slate-500 cursor-not-allowed"
                          : "bg-slate-950 border-slate-800 text-slate-100"
                      )}
                    />
                  </div>

                  <div>
                    <label className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">
                      Rule Name
                    </label>
                    <input
                      type="text"
                      required
                      value={ruleName}
                      onChange={(e) => setRuleName(e.target.value)}
                      placeholder="e.g. Forbid Orders & AuditLogs Join"
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-100 focus:outline-none focus:border-indigo-500"
                    />
                  </div>

                  {/* Target Scope Selection */}
                  <div>
                    <label className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">
                      Target Scope / Associated Plugin
                    </label>
                    <select
                      data-testid="create-rule-target-select"
                      value={ruleTargetId}
                      onChange={(e) => setRuleTargetId(e.target.value)}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-100 focus:outline-none focus:border-indigo-500 font-medium cursor-pointer"
                    >
                      <option value="">Global Scope (Applies to all targets)</option>
                      {plugins.map((p) => (
                        <option key={p.id} value={p.id}>
                          Target: {p.name} ({p.id})
                        </option>
                      ))}
                    </select>
                    <p className="text-[10px] text-slate-500 mt-1">
                      Select &quot;Global Scope&quot; to enforce across all databases, or assign
                      specifically to a database connector.
                    </p>
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">
                        Rule Type
                      </label>
                      <select
                        value={ruleType}
                        onChange={(e) => setRuleType(e.target.value as RuleType)}
                        className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-100 focus:outline-none focus:border-indigo-500"
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
                      <label className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">
                        Severity
                      </label>
                      <select
                        value={severity}
                        onChange={(e) => setSeverity(e.target.value as RuleSeverity)}
                        className="w-full bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-100 focus:outline-none focus:border-indigo-500"
                      >
                        <option value="CRITICAL">CRITICAL</option>
                        <option value="HIGH">HIGH</option>
                        <option value="MEDIUM">MEDIUM</option>
                        <option value="LOW">LOW</option>
                      </select>
                    </div>
                  </div>

                  <div>
                    <label className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">
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
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-100 font-mono focus:outline-none focus:border-indigo-500"
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
                    <label className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">
                      Description
                    </label>
                    <textarea
                      value={description}
                      onChange={(e) => setDescription(e.target.value)}
                      rows={2}
                      placeholder="Why this rule must be enforced..."
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-xs text-slate-100 focus:outline-none focus:border-indigo-500 resize-none"
                    />
                  </div>

                  <div className="flex space-x-2 pt-2">
                    <button
                      type="button"
                      onClick={() => {
                        setShowRuleModal(false);
                        setEditingRule(null);
                      }}
                      className="w-1/2 bg-slate-800 hover:bg-slate-700 text-slate-300 py-2 rounded-lg text-xs font-semibold transition-colors"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      data-testid="submit-create-rule-btn"
                      className="w-1/2 bg-indigo-600 hover:bg-indigo-500 text-white py-2 rounded-lg text-xs font-semibold transition-colors shadow-md shadow-indigo-600/30"
                    >
                      {editingRule ? "Save Rule Changes" : "Save Rule"}
                    </button>
                  </div>
                </form>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
