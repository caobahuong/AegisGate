"use client";

import React, { useState } from "react";
import {
  BookOpen,
  Check,
  FileCode,
  FileText,
  Plus,
  Save,
  Shield,
  Trash2,
  Table,
} from "lucide-react";
import {
  CreateRuleRequest,
  KnowledgeChunkResponse,
  RuleResponse,
  RuleSeverity,
  RuleType,
} from "@/types";
import { cn } from "@/lib/utils";

interface KnowledgeAndRulesProps {
  chunks: KnowledgeChunkResponse[];
  rules: RuleResponse[];
  onSaveDocs: (chunkId: string, docText: string, skillsText: string) => Promise<void>;
  onCreateRule: (rule: CreateRuleRequest) => Promise<void>;
  onDeleteRule: (ruleId: string) => Promise<void>;
}

export const KnowledgeAndRules: React.FC<KnowledgeAndRulesProps> = ({
  chunks,
  rules,
  onSaveDocs,
  onCreateRule,
  onDeleteRule,
}) => {
  const [activeSubTab, setActiveSubTab] = useState<"knowledge" | "rules">("knowledge");

  // Knowledge State
  const [selectedChunkId, setSelectedChunkId] = useState<string>(chunks[0]?.id || "");
  const selectedChunk = chunks.find((c) => c.id === selectedChunkId) || chunks[0];
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
  const [ruleId, setRuleId] = useState<string>("");
  const [ruleName, setRuleName] = useState<string>("");
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

  const handleAddRule = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ruleId || !ruleName) return;
    await onCreateRule({
      id: ruleId.trim(),
      name: ruleName.trim(),
      target_id: null, // global or all targets
      rule_type: ruleType,
      expression: expression.trim(),
      description: description.trim(),
      severity,
      is_active: true,
    });
    setShowRuleModal(false);
    setRuleId("");
    setRuleName("");
    setExpression("");
    setDescription("");
  };

  return (
    <div className="space-y-6">
      {/* Sub-tab Navigation */}
      <div className="flex items-center space-x-4 border-b border-slate-800 pb-3">
        <button
          onClick={() => setActiveSubTab("knowledge")}
          className={cn(
            "flex items-center space-x-2 text-xs font-semibold px-3 py-1.5 rounded-lg transition-colors",
            activeSubTab === "knowledge"
              ? "bg-indigo-600/20 text-indigo-400 border border-indigo-500/30"
              : "text-slate-400 hover:text-slate-200"
          )}
        >
          <BookOpen className="h-4 w-4" />
          <span>Knowledge Chunks & Markdown Docs ({chunks.length})</span>
        </button>
        <button
          onClick={() => setActiveSubTab("rules")}
          className={cn(
            "flex items-center space-x-2 text-xs font-semibold px-3 py-1.5 rounded-lg transition-colors",
            activeSubTab === "rules"
              ? "bg-indigo-600/20 text-indigo-400 border border-indigo-500/30"
              : "text-slate-400 hover:text-slate-200"
          )}
        >
          <Shield className="h-4 w-4" />
          <span>Governance Rules ({rules.length})</span>
        </button>
      </div>

      {/* ========================================================
          SUB-TAB 1: Knowledge Chunks & Markdown Docs
         ======================================================== */}
      {activeSubTab === "knowledge" && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Partitions List & Schema Viewer */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-4">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center space-x-2">
              <Table className="h-4 w-4 text-indigo-400" />
              <span>Partitioned Knowledge Chunks</span>
            </h3>

            <div className="space-y-2">
              {chunks.map((chunk) => (
                <button
                  key={chunk.id}
                  onClick={() => setSelectedChunkId(chunk.id)}
                  className={cn(
                    "w-full text-left p-3 rounded-lg border transition-all duration-150 space-y-1",
                    selectedChunk?.id === chunk.id
                      ? "bg-indigo-600/15 border-indigo-500/40 text-slate-100"
                      : "bg-slate-950/60 border-slate-800/80 text-slate-400 hover:border-slate-700"
                  )}
                >
                  <div className="flex justify-between items-center">
                    <span className="text-xs font-bold text-slate-200">{chunk.title}</span>
                    <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">
                      {chunk.partition_key}
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-500 font-mono truncate">
                    Target: {chunk.target_id}
                  </p>
                </button>
              ))}
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
          <div className="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-xl p-5 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center space-x-2">
                <FileCode className="h-4 w-4 text-indigo-400" />
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200">
                  Hybrid Markdown Docs Editor: {selectedChunk?.title}
                </h3>
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
                  placeholder="# System Documentation\nDetail business context..."
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
                  placeholder="# Standard Skills\nDefine recommended queries..."
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
              onClick={() => setShowRuleModal(true)}
              className="flex items-center space-x-2 bg-indigo-600 hover:bg-indigo-500 text-white px-3 py-1.5 rounded-lg text-xs font-semibold shadow-md shadow-indigo-600/30 transition-colors"
            >
              <Plus className="h-4 w-4" />
              <span>Create Rule</span>
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {rules.map((rule) => (
              <div
                key={rule.id}
                className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-3"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <span
                      className={cn(
                        "text-[10px] font-bold px-2 py-0.5 rounded",
                        rule.severity === "CRITICAL" && "bg-red-500/20 text-red-400 border border-red-500/30",
                        rule.severity === "HIGH" && "bg-amber-500/20 text-amber-400 border border-amber-500/30",
                        rule.severity === "MEDIUM" && "bg-indigo-500/20 text-indigo-400 border border-indigo-500/30",
                        rule.severity === "LOW" && "bg-slate-800 text-slate-300"
                      )}
                    >
                      {rule.severity}
                    </span>
                    <h4 className="text-xs font-bold text-slate-200">{rule.name}</h4>
                  </div>
                  <button
                    onClick={() => onDeleteRule(rule.id)}
                    className="text-slate-500 hover:text-red-400 p-1 transition-colors"
                    title="Delete Rule"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>

                <div className="space-y-1.5 text-xs">
                  <div>
                    <span className="text-slate-500 text-[10px] font-semibold uppercase block">
                      Rule Type & Parameters
                    </span>
                    <span className="font-mono text-indigo-400 font-semibold">{rule.rule_type}</span>
                    <span className="text-slate-400 mx-1.5">|</span>
                    <span className="font-mono text-slate-300 bg-slate-950 px-1.5 py-0.5 rounded border border-slate-800">
                      {rule.expression || "Global"}
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-400 leading-snug">{rule.description}</p>
                </div>
              </div>
            ))}
          </div>

          {/* Add Rule Modal */}
          {showRuleModal && (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
              <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-md w-full p-6 shadow-2xl space-y-4">
                <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                  <h3 className="text-sm font-bold text-slate-100 flex items-center space-x-2">
                    <Shield className="h-4 w-4 text-indigo-400" />
                    <span>Create Governance Rule</span>
                  </h3>
                  <button
                    onClick={() => setShowRuleModal(false)}
                    className="text-slate-400 hover:text-slate-200 text-xs"
                  >
                    Cancel
                  </button>
                </div>

                <form onSubmit={handleAddRule} className="space-y-3">
                  <div>
                    <label className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">
                      Rule ID
                    </label>
                    <input
                      type="text"
                      required
                      value={ruleId}
                      onChange={(e) => setRuleId(e.target.value)}
                      placeholder="e.g. rule_no_cross_join"
                      className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-xs text-slate-100 font-mono focus:outline-none focus:border-indigo-500"
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
                      className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-xs text-slate-100 focus:outline-none focus:border-indigo-500"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">
                        Rule Type
                      </label>
                      <select
                        value={ruleType}
                        onChange={(e) => setRuleType(e.target.value as RuleType)}
                        className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-xs text-slate-100 focus:outline-none focus:border-indigo-500"
                      >
                        <option value="FORBID_JOIN">FORBID_JOIN</option>
                        <option value="FORBID_TABLE_SCAN">FORBID_TABLE_SCAN</option>
                        <option value="MAX_EXECUTION_TIME">MAX_EXECUTION_TIME</option>
                        <option value="CUSTOM">CUSTOM</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1">
                        Severity
                      </label>
                      <select
                        value={severity}
                        onChange={(e) => setSeverity(e.target.value as RuleSeverity)}
                        className="w-full bg-slate-950 border border-slate-800 rounded px-2.5 py-1.5 text-xs text-slate-100 focus:outline-none focus:border-indigo-500"
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
                      placeholder="e.g. Orders,AuditLogs"
                      className="w-full bg-slate-950 border border-slate-800 rounded px-3 py-1.5 text-xs text-slate-100 font-mono focus:outline-none focus:border-indigo-500"
                    />
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
                      className="w-full bg-slate-950 border border-slate-800 rounded p-2.5 text-xs text-slate-100 focus:outline-none focus:border-indigo-500 resize-none"
                    />
                  </div>

                  <div className="flex space-x-2 pt-2">
                    <button
                      type="button"
                      onClick={() => setShowRuleModal(false)}
                      className="w-1/2 bg-slate-800 hover:bg-slate-700 text-slate-300 py-2 rounded-lg text-xs font-semibold transition-colors"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      className="w-1/2 bg-indigo-600 hover:bg-indigo-500 text-white py-2 rounded-lg text-xs font-semibold transition-colors shadow-md shadow-indigo-600/30"
                    >
                      Save Rule
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

