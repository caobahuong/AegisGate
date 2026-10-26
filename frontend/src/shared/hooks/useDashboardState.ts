import { useState, useEffect, useCallback } from "react";
import {
  ActiveTab,
  KnowledgeChunkResponse,
  McpConfigResponse,
  PluginProfileResponse,
  RuleResponse,
} from "@/types";
import {
  fetchAutoMode,
  fetchGlobalMcpConfig,
  fetchKnowledgeChunks,
  fetchPluginMcpConfig,
  fetchRules,
  setAutoMode as apiSetAutoMode,
} from "@/shared/lib/api";
import { useToast } from "@/shared/hooks/useToast";

export function useDashboardState() {
  const [activeTab, setActiveTab] = useState<ActiveTab>("monitor");
  const [autoMode, setAutoMode] = useState<boolean>(false);
  const [chunks, setChunks] = useState<KnowledgeChunkResponse[]>([]);
  const [rules, setRules] = useState<RuleResponse[]>([]);
  const { showToast } = useToast();

  const [showMcpModal, setShowMcpModal] = useState<boolean>(false);
  const [showGuideModal, setShowGuideModal] = useState<boolean>(false);
  const [mcpModalData, setMcpModalData] = useState<McpConfigResponse | null>(null);
  const [mcpModalTitle, setMcpModalTitle] = useState<string>("MCP Connection Configuration");
  const [mcpModalSubtitle, setMcpModalSubtitle] = useState<string>(
    "Global AegisGate MCP Server configuration"
  );
  const [isMcpLoading, setIsMcpLoading] = useState<boolean>(false);

  useEffect(() => {
    Promise.all([
      fetchAutoMode().then(setAutoMode),
      fetchKnowledgeChunks().then(setChunks),
      fetchRules().then(setRules),
    ]).catch(console.error);
  }, []);

  const handleToggleAutoMode = async () => {
    try {
      const updated = await apiSetAutoMode(!autoMode);
      setAutoMode(updated);
      showToast(`Auto approval mode ${updated ? "enabled" : "disabled"}`, "info");
    } catch (err: unknown) {
      showToast(err instanceof Error ? err.message : "Failed to toggle auto mode", "error");
    }
  };

  const handleOpenGlobalMcp = async () => {
    setMcpModalTitle("AegisGate Global MCP Connection");
    setMcpModalSubtitle("Connect Claude Desktop, Cursor, or Cline to AegisGate Core Gateway");
    setShowMcpModal(true);
    setIsMcpLoading(true);
    try {
      setMcpModalData(await fetchGlobalMcpConfig());
    } finally {
      setIsMcpLoading(false);
    }
  };

  const handleOpenPluginMcp = async (plugin: PluginProfileResponse) => {
    setMcpModalTitle(`MCP Connection: ${plugin.name}`);
    setMcpModalSubtitle(`Target connector snippet for ${plugin.driver} (${plugin.id})`);
    setShowMcpModal(true);
    setIsMcpLoading(true);
    try {
      setMcpModalData(await fetchPluginMcpConfig(plugin.id));
    } finally {
      setIsMcpLoading(false);
    }
  };

  const reloadChunks = useCallback(async () => setChunks(await fetchKnowledgeChunks()), []);
  const reloadRules = useCallback(async () => setRules(await fetchRules()), []);

  return {
    activeTab,
    setActiveTab,
    autoMode,
    handleToggleAutoMode,
    chunks,
    reloadChunks,
    rules,
    reloadRules,
    showMcpModal,
    setShowMcpModal,
    showGuideModal,
    setShowGuideModal,
    mcpModalData,
    mcpModalTitle,
    mcpModalSubtitle,
    isMcpLoading,
    handleOpenGlobalMcp,
    handleOpenPluginMcp,
  };
}
