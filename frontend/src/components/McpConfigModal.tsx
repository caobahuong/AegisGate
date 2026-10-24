"use client";

import React, { useState } from "react";
import { Terminal, Copy, Check, X, Cpu, ExternalLink, Sparkles } from "lucide-react";
import { McpConfigResponse } from "@/types";
import { cn } from "@/lib/utils";

interface McpConfigModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: string;
  subtitle?: string;
  configData: McpConfigResponse | null;
  isLoading?: boolean;
}

type ClientTab = "claude" | "cursor" | "cline" | "raw";

export const McpConfigModal: React.FC<McpConfigModalProps> = ({
  isOpen,
  onClose,
  title = "MCP Connection Configuration",
  subtitle = "Model Context Protocol JSON configuration for AI developer agents",
  configData,
  isLoading = false,
}) => {
  const [activeTab, setActiveTab] = useState<ClientTab>("claude");
  const [copied, setCopied] = useState<boolean>(false);

  if (!isOpen) return null;

  // Generate appropriate JSON payload for the selected client
  const getFormattedSnippet = (): string => {
    if (!configData) return "{}";

    let payload: Record<string, unknown> = {};

    if (activeTab === "raw") {
      payload = {
        mcpServers: configData.mcpServers || {},
      };
    } else if (configData.client_configs && configData.client_configs[activeTab]) {
      payload = configData.client_configs[activeTab] as Record<string, unknown>;
    } else {
      payload = {
        mcpServers: configData.mcpServers || {},
      };
    }

    return JSON.stringify(payload, null, 2);
  };

  const snippetText = getFormattedSnippet();

  const handleCopy = async () => {
    try {
      if (navigator.clipboard && typeof navigator.clipboard.writeText === "function") {
        await navigator.clipboard.writeText(snippetText);
      } else if (typeof document.execCommand === "function") {
        // Fallback for iFrame, non-HTTPS, or environments without clipboard API
        const textArea = document.createElement("textarea");
        textArea.value = snippetText;
        textArea.style.position = "fixed";
        textArea.style.left = "-999999px";
        textArea.style.top = "-999999px";
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        document.execCommand("copy");
        textArea.remove();
      }
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy MCP configuration:", err);
    }
  };

  const clientInstructions: Record<ClientTab, { file: string; desc: string }> = {
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

  return (
    <div
      data-testid="mcp-modal"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200"
    >
      <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Modal Header */}
        <div className="flex items-center justify-between p-5 border-b border-slate-800 bg-slate-850">
          <div className="flex items-center space-x-3">
            <div className="h-10 w-10 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center shadow-xs">
              <Terminal className="h-5 w-5 text-indigo-400" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-slate-100 flex items-center space-x-2">
                <span>{title}</span>
                <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  FastMCP 2.0
                </span>
              </h3>
              <p className="text-xs text-slate-400 mt-0.5">{subtitle}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-100 p-1.5 rounded-lg hover:bg-slate-800 transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Client Selection Tabs */}
        <div className="px-5 pt-3 pb-2.5 border-b border-slate-800 bg-slate-850/60 flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center space-x-1.5 bg-slate-800/80 p-1 rounded-xl border border-slate-750">
            {(
              [
                { id: "claude", label: "Claude Desktop / Code" },
                { id: "cursor", label: "Cursor (.cursor/mcp.json)" },
                { id: "cline", label: "Cline (VS Code)" },
                { id: "raw", label: "Raw JSON" },
              ] as { id: ClientTab; label: string }[]
            ).map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={cn(
                  "px-3 py-1.5 rounded-lg text-xs font-medium transition-all",
                  activeTab === tab.id
                    ? "bg-slate-900 text-indigo-400 shadow-xs font-semibold border border-slate-700"
                    : "text-slate-400 hover:text-slate-100 hover:bg-slate-750/50"
                )}
              >
                {tab.label}
              </button>
            ))}
          </div>

          <button
            onClick={handleCopy}
            data-testid="copy-mcp-btn"
            className={cn(
              "flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-200 shadow-sm",
              copied
                ? "bg-emerald-600 text-white shadow-emerald-600/30"
                : "bg-indigo-600 hover:bg-indigo-500 text-white shadow-indigo-600/30"
            )}
          >
            {copied ? (
              <>
                <Check className="h-3.5 w-3.5" />
                <span>Copied to Clipboard!</span>
              </>
            ) : (
              <>
                <Copy className="h-3.5 w-3.5" />
                <span>Copy to Clipboard</span>
              </>
            )}
          </button>
        </div>

        {/* Modal Body / Code Snippet */}
        <div className="p-5 overflow-y-auto space-y-4">
          {isLoading ? (
            <div className="py-12 flex flex-col items-center justify-center space-y-3">
              <Cpu className="h-8 w-8 text-indigo-400 animate-spin" />
              <p className="text-xs text-slate-400">Loading MCP configuration schema...</p>
            </div>
          ) : (
            <>
              {/* Instructions Callout */}
              <div className="bg-slate-850 border border-slate-800 rounded-xl p-3.5 space-y-1.5 shadow-xs">
                <div className="flex flex-wrap items-center gap-1.5 text-indigo-400 text-xs font-semibold">
                  <Sparkles className="h-3.5 w-3.5" />
                  <span>Target Configuration File:</span>
                  <code className="text-[11px] font-mono text-slate-100 bg-slate-900 px-2 py-0.5 rounded border border-slate-800 shadow-xs">
                    {clientInstructions[activeTab].file}
                  </code>
                </div>
                <p className="text-[11px] text-slate-400 leading-relaxed">
                  {clientInstructions[activeTab].desc}
                </p>
              </div>

              {/* Monospace Code Snippet Display (Terminal Style for High Contrast) */}
              <div className="relative rounded-xl overflow-hidden border border-slate-750 bg-[#090d16] shadow-lg">
                <div className="flex items-center justify-between px-3.5 py-2 bg-[#0f172a] border-b border-slate-800 text-[11px] font-mono">
                  <span className="text-slate-300 font-semibold flex items-center space-x-1.5">
                    <Terminal className="h-3 w-3 text-indigo-400" />
                    <span>mcp_config.json</span>
                  </span>
                  <span className="text-[10px] text-indigo-300 bg-indigo-500/15 border border-indigo-500/30 px-2 py-0.5 rounded uppercase tracking-wider font-semibold">
                    {activeTab} format
                  </span>
                </div>
                <pre
                  data-testid="mcp-json-snippet"
                  className="p-4 text-xs font-mono text-indigo-200 overflow-x-auto leading-relaxed select-all selection:bg-indigo-500/40 selection:text-white"
                >
                  {snippetText}
                </pre>
              </div>

              {/* Standard MCP Tools provided by AegisGate */}
              <div className="bg-slate-850 border border-slate-800 rounded-xl p-3.5 space-y-2.5 shadow-xs">
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
                  Exported MCP Tools (Enabled for AI Agent)
                </span>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px] font-mono">
                  <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800 shadow-xs">
                    <span className="text-indigo-400 font-bold block">1. get_catalog</span>
                    <span className="text-[10px] text-slate-400 block mt-0.5">Zero-touch cached schema retrieval</span>
                  </div>
                  <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800 shadow-xs">
                    <span className="text-indigo-400 font-bold block">2. get_knowledge</span>
                    <span className="text-[10px] text-slate-400 block mt-0.5">Retrieve doc.md, skills &amp; active rules</span>
                  </div>
                  <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800 shadow-xs">
                    <span className="text-indigo-400 font-bold block">3. submit_execution</span>
                    <span className="text-[10px] text-slate-400 block mt-0.5">Dry-Run &amp; rule governance execution</span>
                  </div>
                  <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800 shadow-xs">
                    <span className="text-indigo-400 font-bold block">4. check_execution_status</span>
                    <span className="text-[10px] text-slate-400 block mt-0.5">Poll query result or pause review</span>
                  </div>
                </div>
              </div>
            </>
          )}
        </div>

        {/* Modal Footer */}
        <div className="p-4 border-t border-slate-800 bg-slate-850 flex items-center justify-between">
          <div className="text-[11px] text-slate-400 flex items-center space-x-1.5">
            <ExternalLink className="h-3 w-3 text-indigo-400" />
            <span>Transports supported: Stdio &amp; Server-Sent Events (SSE)</span>
          </div>
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg text-xs font-semibold text-slate-100 bg-slate-800 hover:bg-slate-750 border border-slate-700 transition-colors shadow-xs"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
