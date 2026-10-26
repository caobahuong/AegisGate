"use client";

import { useState, useMemo, useEffect } from "react";
import {
  KnowledgeChunkResponse,
  RuleResponse,
  PluginProfileResponse,
  RuleType,
  RuleSeverity,
} from "@/types";
import { useToast } from "@/shared/hooks/useToast";

export interface UseKnowledgeAndRulesOptions {
  chunks: KnowledgeChunkResponse[];
  rules: RuleResponse[];
  plugins?: PluginProfileResponse[];
  onSaveDocs?: (chunkId: string, docText: string, skillsText: string) => Promise<void>;
  onCreateRule?: (rule: any) => Promise<void>;
  onUpdateRule?: (ruleId: string, rule: any) => Promise<void>;
  onDeleteRule?: (ruleId: string) => Promise<void>;
}

export function useKnowledgeAndRules({
  chunks,
  rules,
  plugins = [],
  onSaveDocs,
  onCreateRule,
  onUpdateRule,
  onDeleteRule,
}: UseKnowledgeAndRulesOptions) {
  const [activeSubTab, setActiveSubTab] = useState<"knowledge" | "rules">("knowledge");
  const [targetFilter, setTargetFilter] = useState<string>("all");
  const { showToast } = useToast();

  const filteredChunks = useMemo(() => {
    return chunks.filter((c) => {
      if (targetFilter === "all") return true;
      if (targetFilter === "global") return false;
      return c.target_id === targetFilter;
    });
  }, [chunks, targetFilter]);

  const filteredRules = useMemo(() => {
    return rules.filter((r) => {
      if (targetFilter === "all") return true;
      if (targetFilter === "global") return !r.target_id;
      return r.target_id === targetFilter;
    });
  }, [rules, targetFilter]);

  // Selected chunk state
  const [selectedChunkId, setSelectedChunkId] = useState<string>(
    filteredChunks[0]?.id || chunks[0]?.id || ""
  );

  const selectedChunk = useMemo(() => {
    return (
      filteredChunks.find((c) => c.id === selectedChunkId) ||
      filteredChunks[0] ||
      chunks[0] ||
      null
    );
  }, [filteredChunks, selectedChunkId, chunks]);

  const [docContent, setDocContent] = useState<string>(selectedChunk?.doc_content || "");
  const [skillsContent, setSkillsContent] = useState<string>(selectedChunk?.skills_content || "");
  const [isSavingDocs, setIsSavingDocs] = useState<boolean>(false);
  const [saveSuccess, setSaveSuccess] = useState<boolean>(false);

  useEffect(() => {
    if (selectedChunk) {
      setDocContent(selectedChunk.doc_content || "");
      setSkillsContent(selectedChunk.skills_content || "");
    }
  }, [selectedChunk]);

  // Rule Modal state
  const [showRuleModal, setShowRuleModal] = useState<boolean>(false);
  const [editingRule, setEditingRule] = useState<RuleResponse | null>(null);
  const [ruleId, setRuleId] = useState<string>("" );
  const [ruleName, setRuleName] = useState<string>("");
  const [ruleTargetId, setRuleTargetId] = useState<string>("");
  const [ruleType, setRuleType] = useState<RuleType>("FORBID_JOIN");
  const [expression, setExpression] = useState<string>("");
  const [description, setDescription] = useState<string>("");
  const [severity, setSeverity] = useState<RuleSeverity>("HIGH");

  const handleSaveDocs = async () => {
    if (!selectedChunk || !onSaveDocs) return;
    setIsSavingDocs(true);
    setSaveSuccess(false);
    try {
      await onSaveDocs(selectedChunk.id, docContent, skillsContent);
      setSaveSuccess(true);
      showToast("Documentation & skills saved successfully", "success");
      setTimeout(() => setSaveSuccess(false), 3000);
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : "Failed to save docs", "error");
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
    try {
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
        showToast(`Rule "${ruleName}" updated successfully`, "success");
      } else {
        if (!onCreateRule || !ruleId || !ruleName) return;
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
        showToast(`Rule "${ruleName}" created successfully`, "success");
      }
      setShowRuleModal(false);
      setEditingRule(null);
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : "Failed to save rule", "error");
    }
  };

  const getPluginName = (targetId: string | null | undefined): string => {
    if (!targetId) return "Global";
    const found = plugins.find((p) => p.id === targetId);
    return found ? found.name : targetId;
  };

  return {
    activeSubTab,
    setActiveSubTab,
    targetFilter,
    setTargetFilter,
    filteredChunks,
    filteredRules,
    selectedChunkId,
    setSelectedChunkId,
    selectedChunk,
    docContent,
    setDocContent,
    skillsContent,
    setSkillsContent,
    isSavingDocs,
    saveSuccess,
    handleSaveDocs,
    showRuleModal,
    setShowRuleModal,
    editingRule,
    ruleId,
    setRuleId,
    ruleName,
    setRuleName,
    ruleTargetId,
    setRuleTargetId,
    ruleType,
    setRuleType,
    expression,
    setExpression,
    description,
    setDescription,
    severity,
    setSeverity,
    handleOpenCreateRule,
    handleOpenEditRule,
    handleSubmitRule,
    getPluginName,
    onDeleteRule,
  };
}
