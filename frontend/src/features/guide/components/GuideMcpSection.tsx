"use client";

import React, { useState } from "react";
import { Terminal, Copy, Check } from "lucide-react";
import { getBackendOrigin } from "@/shared/lib/api";
import { useToast } from "@/shared/hooks/useToast";

export const GuideMcpSection: React.FC = () => {
  const [copiedSnippet, setCopiedSnippet] = useState<string | null>(null);
  const { showToast } = useToast();
  const backendUrl = getBackendOrigin();

  const handleCopyCode = (code: string, id: string) => {
    if (typeof navigator !== "undefined" && navigator.clipboard) {
      navigator.clipboard.writeText(code);
    } else {
      const textarea = document.createElement("textarea");
      textarea.value = code;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      document.body.removeChild(textarea);
    }
    setCopiedSnippet(id);
    showToast("MCP JSON snippet copied to clipboard!", "success", 3000);
    setTimeout(() => setCopiedSnippet(null), 2000);
  };

  const sampleConfig = JSON.stringify(
    {
      mcpServers: {
        aegisgate: {
          command: "python",
          args: ["-m", "core.gateway.mcp_server"],
          env: { AEGISGATE_API_URL: backendUrl },
        },
        "aegisgate-sqlserver_prod": {
          command: "python",
          args: ["-m", "core.gateway.mcp_server", "--plugin", "sqlserver_prod"],
          env: { AEGISGATE_API_URL: backendUrl },
        },
      },
    },
    null,
    2
  );

  return (
    <div className="space-y-4 animate-in fade-in duration-150">
      <div>
        <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 flex items-center space-x-2">
          <Terminal className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />
          <span>2. Connecting AI Clients via MCP Protocol</span>
        </h3>
        <p className="text-slate-500 dark:text-slate-400 mt-1">
          Provides standardized Model Context Protocol (MCP) over Stdio transport for Claude Desktop, Cursor, and Cline.
        </p>
      </div>

      <div className="space-y-3">
        <h4 className="font-bold text-slate-800 dark:text-slate-200">How to retrieve connection config:</h4>
        <p className="text-slate-500 dark:text-slate-400">
          Click the <strong>&quot;MCP Config&quot;</strong> button on the top Header (global connection) or the terminal
          icon on any Plugin card (scoped to that specific database).
        </p>

        <div className="space-y-1.5">
          <div className="flex justify-between items-center">
            <span className="text-[11px] font-mono text-slate-500 dark:text-slate-400">
              Configured endpoint: <code className="text-indigo-600 dark:text-indigo-400 font-bold">{backendUrl}</code>
            </span>
            <button
              type="button"
              onClick={() => handleCopyCode(sampleConfig, "mcp_json")}
              className="flex items-center space-x-1 bg-slate-200 dark:bg-slate-800 hover:bg-slate-300 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 px-2 py-0.5 rounded text-[10px] transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
            >
              {copiedSnippet === "mcp_json" ? (
                <Check className="h-3 w-3 text-emerald-600 dark:text-emerald-400" />
              ) : (
                <Copy className="h-3 w-3" />
              )}
              <span>{copiedSnippet === "mcp_json" ? "Copied!" : "Copy Snippet"}</span>
            </button>
          </div>

          <pre className="p-3 bg-slate-900 border border-slate-700/80 rounded-xl font-mono text-[11px] text-indigo-200 overflow-x-auto shadow-sm select-all">
            {sampleConfig}
          </pre>
        </div>
      </div>

      <div className="p-4 rounded-xl bg-slate-50/80 dark:bg-slate-950/80 border border-slate-200 dark:border-slate-800 space-y-2">
        <h4 className="font-bold text-slate-800 dark:text-slate-200">4 MCP Tools Exposed to AI Agents:</h4>
        <ul className="space-y-1.5 text-[11px] text-slate-700 dark:text-slate-300">
          <li>
            <code className="text-indigo-600 dark:text-indigo-400 font-bold font-mono">
              get_catalog(target_id?, partition_key?)
            </code>
            : Inspect tables, columns, primary keys, and indexes from cache.
          </li>
          <li>
            <code className="text-indigo-600 dark:text-indigo-400 font-bold font-mono">
              get_knowledge(target_id?, partition_key?)
            </code>
            : Read business context (doc.md), query skills, and active rules.
          </li>
          <li>
            <code className="text-indigo-600 dark:text-indigo-400 font-bold font-mono">
              submit_execution(query, target_id?, reasoning?)
            </code>
            : Submit a SQL/DB statement through the Dry-Run &amp; guarded execution pipeline.
          </li>
          <li>
            <code className="text-indigo-600 dark:text-indigo-400 font-bold font-mono">
              check_execution_status(execution_id)
            </code>
            : Poll approval status and retrieve returned dataset records.
          </li>
        </ul>
      </div>
    </div>
  );
};
