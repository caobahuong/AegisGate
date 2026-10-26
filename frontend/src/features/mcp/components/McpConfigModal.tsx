"use client";

import React, { useState } from "react";
import { Terminal, Copy, Check, Cpu, ExternalLink, Sparkles } from "lucide-react";
import { McpConfigResponse } from "@/types";
import { Modal } from "@/shared/ui/Modal";
import { Tabs } from "@/shared/ui/Tabs";
import { Button } from "@/shared/ui/Button";
import { useToast } from "@/shared/hooks/useToast";

export interface McpConfigModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  subtitle?: string;
  configData: McpConfigResponse | null;
  isLoading?: boolean;
}

type ClientTab = "claude" | "cursor" | "cline" | "raw";

const CLIENT_INSTRUCTIONS: Record<ClientTab, { file: string; desc: string }> = {
  claude: {
    file: "%APPDATA%\\Claude\\claude_desktop_config.json (Windows) or ~/Library/Application Support/Claude/ (Mac)",
    desc: "Paste this JSON into your Claude Desktop or Claude Code configuration file to enable AegisGate tools.",
  },
  cursor: {
    file: ".cursor/mcp.json (Project root) or Cursor Settings > Features > MCP",
    desc: "Add this server configuration to enable Cursor Composer and Chat to execute through AegisGate proxy.",
  },
  cline: {
    file: "cline_mcp_settings.json",
    desc: "Configure Cline in VS Code to utilize AegisGate governance rules, catalog, and safe dry-run inspection.",
  },
  raw: {
    file: "Standard Stdio JSON-RPC MCP Spec",
    desc: "Universal MCP Stdio transport command and arguments for any custom Model Context Protocol client.",
  },
};

export const McpConfigModal: React.FC<McpConfigModalProps> = ({
  isOpen,
  onClose,
  title = "MCP Connection Configuration",
  subtitle = "Model Context Protocol JSON configuration for AI developer agents",
  configData,
  isLoading = false,
}) => {
  const [activeTab, setActiveTab] = useState<string>("claude");
  const [copied, setCopied] = useState<boolean>(false);
  const { showToast } = useToast();

  const getFormattedSnippet = (): string => {
    if (!configData) return "{}";
    let payload: Record<string, unknown> = {};

    if (activeTab === "raw") {
      payload = { mcpServers: configData.mcpServers || {} };
    } else if (configData.client_configs && configData.client_configs[activeTab]) {
      payload = configData.client_configs[activeTab] as Record<string, unknown>;
    } else {
      payload = { mcpServers: configData.mcpServers || {} };
    }

    return JSON.stringify(payload, null, 2);
  };

  const snippetText = getFormattedSnippet();

  const handleCopy = async () => {
    try {
      if (navigator.clipboard && typeof navigator.clipboard.writeText === "function") {
        await navigator.clipboard.writeText(snippetText);
      } else if (typeof document.execCommand === "function") {
        const textArea = document.createElement("textarea");
        textArea.value = snippetText;
        textArea.style.position = "fixed";
        textArea.style.left = "-999999px";
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        document.execCommand("copy");
        textArea.remove();
      }
      setCopied(true);
      showToast("MCP Configuration copied to clipboard!", "success", 3000);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      showToast("Failed to copy to clipboard", "error");
    }
  };

  const tabItems = [
    { id: "claude", label: "Claude Desktop", icon: <Sparkles className="h-3.5 w-3.5" /> },
    { id: "cursor", label: "Cursor AI", icon: <Cpu className="h-3.5 w-3.5" /> },
    { id: "cline", label: "Cline (VS Code)", icon: <Terminal className="h-3.5 w-3.5" /> },
    { id: "raw", label: "Universal JSON", icon: <ExternalLink className="h-3.5 w-3.5" /> },
  ];

  const currentInstruction = CLIENT_INSTRUCTIONS[activeTab as ClientTab] || CLIENT_INSTRUCTIONS.claude;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={title}
      subtitle={subtitle}
      icon={<Terminal className="h-5 w-5" />}
      maxWidth="2xl"
    >
      <div data-testid="mcp-modal" className="space-y-4">
        {/* Client Selection Tabs */}
        <Tabs
          items={tabItems}
          activeTab={activeTab}
          onTabChange={setActiveTab}
          variant="pill"
        />

        {/* Client Instructions */}
        <div className="bg-slate-50 dark:bg-slate-950/60 border border-slate-200 dark:border-slate-800 rounded-xl p-3.5 space-y-1.5 text-xs">
          <p className="text-slate-600 dark:text-slate-400 font-medium">{currentInstruction.desc}</p>
          <div className="flex items-center space-x-2 pt-1 font-mono text-[11px] text-slate-700 dark:text-slate-300">
            <span className="text-slate-400">Target Config File:</span>
            <span className="px-1.5 py-0.5 rounded bg-slate-200 dark:bg-slate-800 text-indigo-700 dark:text-indigo-400 font-semibold select-all break-all">
              {currentInstruction.file}
            </span>
          </div>
        </div>

        {/* Code Snippet Box */}
        <div className="relative rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-900 overflow-hidden shadow-inner">
          <div className="flex items-center justify-between px-4 py-2 border-b border-slate-800 bg-slate-950/80">
            <div className="flex items-center space-x-2">
              <span className="h-2.5 w-2.5 rounded-full bg-rose-500/80 inline-block" />
              <span className="h-2.5 w-2.5 rounded-full bg-amber-500/80 inline-block" />
              <span className="h-2.5 w-2.5 rounded-full bg-emerald-500/80 inline-block" />
              <span className="ml-2 font-mono text-[11px] text-slate-400">mcp_config.json</span>
            </div>
            <button
              type="button"
              onClick={handleCopy}
              data-testid="copy-mcp-btn"
              className="flex items-center space-x-1.5 text-xs font-semibold px-2.5 py-1 rounded-md bg-indigo-600/30 hover:bg-indigo-600/50 text-indigo-300 border border-indigo-500/30 transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400"
            >
              {copied ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
              <span>{copied ? "Copied!" : "Copy Snippet"}</span>
            </button>
          </div>

          <pre
            data-testid="mcp-json-snippet"
            className="p-4 text-xs font-mono text-slate-200 overflow-x-auto max-h-72 leading-relaxed select-all"
          >
            {isLoading ? "Generating MCP Configuration..." : snippetText}
          </pre>
        </div>

        {/* Footer info & close */}
        <div className="flex items-center justify-between pt-2 text-xs">
          <span className="text-slate-500 dark:text-slate-400 font-mono text-[11px]">
            Server: {configData?.server_name || "AegisGate Gateway"} (Stdio Transport)
          </span>
          <Button variant="secondary" size="sm" onClick={onClose}>
            Close
          </Button>
        </div>
      </div>
    </Modal>
  );
};
