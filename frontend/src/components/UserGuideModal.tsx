"use client";

import React, { useState } from "react";
import {
  BookOpen,
  X,
  Layers,
  Terminal,
  Shield,
  Activity,
  Boxes,
  FileText,
  Copy,
  Check,
  CheckCircle2,
  AlertTriangle,
  Database,
  Sparkles,
  Clock,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface UserGuideModalProps {
  isOpen: boolean;
  onClose: () => void;
}

type GuideSection =
  | "overview"
  | "mcp"
  | "plugins"
  | "rules"
  | "execution"
  | "audit";

export const UserGuideModal: React.FC<UserGuideModalProps> = ({ isOpen, onClose }) => {
  const [activeSection, setActiveSection] = useState<GuideSection>("overview");
  const [copiedSnippet, setCopiedSnippet] = useState<string | null>(null);

  if (!isOpen) return null;

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
    setTimeout(() => setCopiedSnippet(null), 2000);
  };

  const sections = [
    { id: "overview" as GuideSection, label: "1. Overview & Architecture", icon: Layers },
    { id: "mcp" as GuideSection, label: "2. AI Connection via MCP", icon: Terminal },
    { id: "plugins" as GuideSection, label: "3. Pluggable Targets", icon: Boxes },
    { id: "rules" as GuideSection, label: "4. Governance Rules & Scope", icon: Shield },
    { id: "execution" as GuideSection, label: "5. Live Monitor & Approvals", icon: Activity },
    { id: "audit" as GuideSection, label: "6. Audit Logs Input / Output", icon: FileText },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 animate-in fade-in duration-150">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-4xl w-full h-[88vh] shadow-2xl flex flex-col overflow-hidden">
        
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-950/60 flex-shrink-0">
          <div className="flex items-center space-x-3">
            <div className="h-9 w-9 rounded-xl bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center">
              <BookOpen className="h-5 w-5 text-indigo-400" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-slate-100 flex items-center space-x-2">
                <span>AegisGate System User Guide</span>
                <span className="text-[10px] px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 font-mono">
                  v2.0 Enterprise
                </span>
              </h2>
              <p className="text-xs text-slate-400">
                Operational manual for the Zero-Trust Database Gateway for AI Agents (Claude, Cursor, Cline).
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            data-testid="close-user-guide-btn"
            title="Close"
            className="text-slate-400 hover:text-slate-200 p-1.5 rounded-lg hover:bg-slate-800 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Modal Body: Left Navigation & Right Content */}
        <div className="flex flex-1 overflow-hidden">
          
          {/* Left Navigation Sidebar */}
          <div className="w-64 border-r border-slate-800 p-4 space-y-1.5 bg-slate-950/40 flex-shrink-0 overflow-y-auto">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block px-2.5 pb-1">
              Documentation Topics
            </span>
            {sections.map((sec) => {
              const Icon = sec.icon;
              const isActive = activeSection === sec.id;
              return (
                <button
                  key={sec.id}
                  onClick={() => setActiveSection(sec.id)}
                  className={cn(
                    "w-full flex items-center space-x-2.5 px-3 py-2.5 rounded-lg text-xs font-medium transition-all text-left",
                    isActive
                      ? "bg-indigo-600/20 text-indigo-300 border border-indigo-500/30 font-semibold shadow-sm"
                      : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/40"
                  )}
                >
                  <Icon className={cn("h-4 w-4 flex-shrink-0", isActive ? "text-indigo-400" : "text-slate-500")} />
                  <span className="truncate">{sec.label}</span>
                </button>
              );
            })}

            <div className="pt-4 border-t border-slate-800/80 mt-4 space-y-2">
              <div className="p-3 rounded-lg bg-indigo-600/10 border border-indigo-500/20 space-y-1">
                <span className="text-[10px] font-bold text-indigo-400 flex items-center space-x-1">
                  <Sparkles className="h-3 w-3" />
                  <span>Gateway Status</span>
                </span>
                <p className="text-[11px] text-slate-300 leading-snug">
                  MCP Server is active and listening on port <code className="text-indigo-300 font-mono">8000</code>.
                </p>
              </div>
            </div>
          </div>

          {/* Right Content Area */}
          <div className="flex-1 p-6 overflow-y-auto space-y-6 text-xs text-slate-300 leading-relaxed">
            
            {/* 1. OVERVIEW */}
            {activeSection === "overview" && (
              <div className="space-y-4 animate-in fade-in duration-150">
                <div>
                  <h3 className="text-sm font-bold text-slate-100 flex items-center space-x-2">
                    <Layers className="h-4 w-4 text-indigo-400" />
                    <span>1. Zero-Trust Database Gateway Architecture</span>
                  </h3>
                  <p className="text-slate-400 mt-1">
                    AegisGate is an intermediate security and governance layer between AI Agents (Claude Code, Cursor, Cline) and Production Databases (SQL Server, MongoDB, PostgreSQL).
                  </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 space-y-1.5">
                    <div className="flex items-center space-x-1.5 text-indigo-400 font-bold text-xs">
                      <Database className="h-3.5 w-3.5" />
                      <span>Port 1: Structural Cache</span>
                    </div>
                    <p className="text-[11px] text-slate-400">
                      AI Agents read table schemas, columns, primary keys, and business docs from AegisGate&apos;s cache <strong>without touching the live DB</strong>.
                    </p>
                  </div>

                  <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 space-y-1.5">
                    <div className="flex items-center space-x-1.5 text-amber-400 font-bold text-xs">
                      <Shield className="h-3.5 w-3.5" />
                      <span>Port 2: Dry-Run Inspection</span>
                    </div>
                    <p className="text-[11px] text-slate-400">
                      Before execution, queries undergo Showplan XML / Explain inspection, cost calculation, and Governance Rules verification.
                    </p>
                  </div>

                  <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 space-y-1.5">
                    <div className="flex items-center space-x-1.5 text-emerald-400 font-bold text-xs">
                      <Activity className="h-3.5 w-3.5" />
                      <span>Port 3: Guarded Execution</span>
                    </div>
                    <p className="text-[11px] text-slate-400">
                      Executes queries under strict timeout guards, tracks live session SPIDs, and provides an instant Emergency Kill switch.
                    </p>
                  </div>
                </div>

                <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 space-y-2">
                  <h4 className="font-bold text-slate-200">Query Execution Lifecycle</h4>
                  <ol className="list-decimal list-inside space-y-1.5 text-[11px] text-slate-300">
                    <li><strong className="text-indigo-400">AI Submission:</strong> AI submits a query along with its intent (Reasoning) via MCP or REST API.</li>
                    <li><strong className="text-amber-400">Dry-Run &amp; Rule Check:</strong> Gateway inspects for violations (Full Table Scan, Forbidden Joins). If violated -&gt; immediately <strong>REJECTED</strong>.</li>
                    <li><strong className="text-indigo-400">Human Approval / Auto:</strong> If Auto Mode is ON -&gt; Executes immediately. If OFF -&gt; Pauses in <strong>PAUSED_FOR_REVIEW</strong> awaiting human approval.</li>
                    <li><strong className="text-emerald-400">Guarded Run:</strong> Safely executes under Timeout Guard and records full Input/Output in the Audit Log.</li>
                  </ol>
                </div>
              </div>
            )}

            {/* 2. MCP CONNECTION */}
            {activeSection === "mcp" && (
              <div className="space-y-4 animate-in fade-in duration-150">
                <div>
                  <h3 className="text-sm font-bold text-slate-100 flex items-center space-x-2">
                    <Terminal className="h-4 w-4 text-indigo-400" />
                    <span>2. Connecting AI Clients via MCP Protocol</span>
                  </h3>
                  <p className="text-slate-400 mt-1">
                    Provides standardized Model Context Protocol (MCP) over Stdio transport for Claude Desktop, Cursor, and Cline.
                  </p>
                </div>

                <div className="space-y-3">
                  <h4 className="font-bold text-slate-200">How to retrieve connection config:</h4>
                  <p className="text-slate-400">
                    Click the <strong>&quot;MCP Config&quot;</strong> button on the top Header (global connection) or the terminal icon on any Plugin card (scoped to that specific database).
                  </p>

                  <div className="space-y-1.5">
                    <div className="flex justify-between items-center">
                      <span className="text-[11px] font-mono text-slate-400">Sample configuration for Cursor (.cursor/mcp.json) or Claude Desktop:</span>
                      <button
                        onClick={() => handleCopyCode(JSON.stringify({
                          mcpServers: {
                            "aegisgate": {
                              command: "python",
                              args: ["-m", "core.gateway.mcp_server"],
                              env: { AEGISGATE_API_URL: "http://localhost:8000" }
                            },
                            "aegisgate-sqlserver_prod": {
                              command: "python",
                              args: ["-m", "core.gateway.mcp_server", "--plugin", "sqlserver_prod"],
                              env: { AEGISGATE_API_URL: "http://localhost:8000" }
                            }
                          }
                        }, null, 2), "mcp_json")}
                        className="flex items-center space-x-1 bg-slate-800 hover:bg-slate-700 text-slate-200 px-2 py-0.5 rounded text-[10px] transition-colors"
                      >
                        {copiedSnippet === "mcp_json" ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
                        <span>{copiedSnippet === "mcp_json" ? "Copied!" : "Copy Snippet"}</span>
                      </button>
                    </div>

                    <pre className="p-3 bg-[#090d16] border border-slate-700/80 rounded-xl font-mono text-[11px] text-indigo-200 overflow-x-auto shadow-sm">
{`{
  "mcpServers": {
    "aegisgate": {
      "command": "python",
      "args": ["-m", "core.gateway.mcp_server"],
      "env": { "AEGISGATE_API_URL": "http://localhost:8000" }
    },
    "aegisgate-sqlserver_prod": {
      "command": "python",
      "args": ["-m", "core.gateway.mcp_server", "--plugin", "sqlserver_prod"],
      "env": { "AEGISGATE_API_URL": "http://localhost:8000" }
    }
  }
}`}
                    </pre>
                  </div>
                </div>

                <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 space-y-2">
                  <h4 className="font-bold text-slate-200">4 MCP Tools Exposed to AI Agents:</h4>
                  <ul className="space-y-1.5 text-[11px]">
                    <li><code className="text-indigo-400 font-bold font-mono">get_catalog(target_id?, partition_key?)</code>: Inspect tables, columns, primary keys, and indexes from cache.</li>
                    <li><code className="text-indigo-400 font-bold font-mono">get_knowledge(target_id?, partition_key?)</code>: Read business context (doc.md), query skills, and active rules.</li>
                    <li><code className="text-indigo-400 font-bold font-mono">submit_execution(query, target_id?, reasoning?)</code>: Submit a SQL/DB statement through the Dry-Run &amp; guarded execution pipeline.</li>
                    <li><code className="text-indigo-400 font-bold font-mono">check_execution_status(execution_id)</code>: Poll approval status and retrieve returned dataset records.</li>
                  </ul>
                </div>
              </div>
            )}

            {/* 3. PLUGINS */}
            {activeSection === "plugins" && (
              <div className="space-y-4 animate-in fade-in duration-150">
                <div>
                  <h3 className="text-sm font-bold text-slate-100 flex items-center space-x-2">
                    <Boxes className="h-4 w-4 text-indigo-400" />
                    <span>3. Managing Pluggable Targets (Database Connectors)</span>
                  </h3>
                  <p className="text-slate-400 mt-1">
                    Each database runs as an isolated Stdio subprocess defining its own Dynamic UI Schema and custom telemetry card.
                  </p>
                </div>

                <div className="space-y-2">
                  <h4 className="font-bold text-slate-200">Key Capabilities on Pluggable Targets Tab:</h4>
                  <ul className="space-y-2 text-[11px]">
                    <li className="p-2.5 rounded-lg bg-slate-950 border border-slate-800">
                      <strong className="text-indigo-400 block mb-0.5">Edit Configuration:</strong>
                      Click <strong>&quot;Edit Configuration&quot;</strong> on any plugin card to modify Server, Port, Database Name, Username, or Password. Saving automatically dispatches a <code className="text-indigo-300 font-mono">re-init</code> signal to the adapter subprocess.
                    </li>
                    <li className="p-2.5 rounded-lg bg-slate-950 border border-slate-800">
                      <strong className="text-indigo-400 block mb-0.5">Sync Schema &amp; Indexes Now:</strong>
                      Scans live table structures and indexes from the target database and updates the AI structural cache.
                    </li>
                    <li className="p-2.5 rounded-lg bg-slate-950 border border-slate-800">
                      <strong className="text-red-400 block mb-0.5">Uninstall Plugin:</strong>
                      Click the red trash icon to either Soft Deactivate or permanently Hard Delete the plugin from the database.
                    </li>
                  </ul>
                </div>
              </div>
            )}

            {/* 4. RULES & SCOPING */}
            {activeSection === "rules" && (
              <div className="space-y-4 animate-in fade-in duration-150">
                <div>
                  <h3 className="text-sm font-bold text-slate-100 flex items-center space-x-2">
                    <Shield className="h-4 w-4 text-indigo-400" />
                    <span>4. Governance Rules &amp; Target Scoping</span>
                  </h3>
                  <p className="text-slate-400 mt-1">
                    Configure automated query guardrails to prevent costly or destructive AI-generated queries.
                  </p>
                </div>

                <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
                  <h4 className="font-bold text-slate-200">Creating &amp; Editing Rules:</h4>
                  <p className="text-slate-400 text-[11px]">
                    In the <strong>&quot;Governance Rules&quot;</strong> sub-tab, click <strong>&quot;Create Rule&quot;</strong> to add a new policy, or click the pencil <strong>&quot;Edit&quot;</strong> icon on any existing rule card:
                  </p>
                  <ul className="list-disc list-inside space-y-1 text-[11px] pl-2 text-slate-300">
                    <li><strong className="text-indigo-400">Target Scope:</strong> Choose <code className="text-indigo-300 font-mono">Global Scope</code> to enforce across all databases, or assign to a specific plugin (e.g., <code className="text-emerald-300 font-mono">sqlserver_prod</code>).</li>
                    <li><strong className="text-indigo-400">Rule Type:</strong>
                      <ul className="list-circle list-inside pl-4 pt-1 space-y-1">
                        <li><code className="text-indigo-300 font-mono">FORBID_JOIN</code>: Block joining sensitive tables (e.g., <code className="text-slate-200">Orders,AuditLogs</code>).</li>
                        <li><code className="text-indigo-300 font-mono">FORBID_TABLE_SCAN</code>: Reject queries missing indexed WHERE clauses that cause full table scans.</li>
                        <li><code className="text-indigo-300 font-mono">MAX_EXECUTION_TIME</code>: Cap maximum allowed execution duration in seconds (e.g., 15s).</li>
                        <li><code className="text-indigo-300 font-mono">CUSTOM</code>: Custom regular expression matching for domain-specific policies.</li>
                      </ul>
                    </li>
                  </ul>
                </div>

                <div className="p-3 rounded-lg bg-indigo-600/10 border border-indigo-500/20 text-[11px] space-y-1">
                  <span className="font-bold text-indigo-400 block">Target Scope Filter:</span>
                  <p className="text-slate-300">
                    Use the Target selector dropdown at the top of the Knowledge &amp; Rules tab to filter between <em>All Pluggable Targets</em>, <em>Global Scope Only</em>, or a specific Plugin.
                  </p>
                </div>
              </div>
            )}

            {/* 5. EXECUTION & AUTO MODE */}
            {activeSection === "execution" && (
              <div className="space-y-4 animate-in fade-in duration-150">
                <div>
                  <h3 className="text-sm font-bold text-slate-100 flex items-center space-x-2">
                    <Activity className="h-4 w-4 text-indigo-400" />
                    <span>5. Live Execution Monitor &amp; Approval Gatekeeper</span>
                  </h3>
                  <p className="text-slate-400 mt-1">
                    Monitor real-time query execution streams via Server-Sent Events (SSE).
                  </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 space-y-1.5">
                    <div className="flex items-center space-x-1.5 text-amber-400 font-bold text-xs">
                      <Clock className="h-3.5 w-3.5" />
                      <span>Manual Review Mode (Default)</span>
                    </div>
                    <p className="text-[11px] text-slate-400">
                      When Header toggle is <strong className="text-slate-200">OFF</strong>: After passing Dry-Run, queries pause at <code className="text-amber-400 font-mono">PAUSED_FOR_REVIEW</code>. Click <strong>&quot;Approve &amp; Run&quot;</strong> to execute or <strong>&quot;Reject&quot;</strong> to cancel.
                    </p>
                  </div>

                  <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 space-y-1.5">
                    <div className="flex items-center space-x-1.5 text-emerald-400 font-bold text-xs">
                      <CheckCircle2 className="h-3.5 w-3.5" />
                      <span>Auto Approval Mode</span>
                    </div>
                    <p className="text-[11px] text-slate-400">
                      Switch Header toggle to <strong className="text-emerald-400">ON</strong>: Any safe query (0 policy violations) is automatically approved and executed immediately, returning data to the AI in milliseconds.
                    </p>
                  </div>
                </div>

                <div className="p-3.5 rounded-xl bg-red-500/10 border border-red-500/20 text-red-300 text-[11px] space-y-1">
                  <div className="flex items-center space-x-1.5 font-bold text-red-400">
                    <AlertTriangle className="h-4 w-4" />
                    <span>Emergency Kill Switch (KILL SPID):</span>
                  </div>
                  <p>
                    If a running query hangs or consumes excessive resources, clicking <strong>&quot;Stop &amp; KILL Session Now&quot;</strong> dispatches an immediate native kill command to terminate the database session.
                  </p>
                </div>
              </div>
            )}

            {/* 6. AUDIT LOGS */}
            {activeSection === "audit" && (
              <div className="space-y-4 animate-in fade-in duration-150">
                <div>
                  <h3 className="text-sm font-bold text-slate-100 flex items-center space-x-2">
                    <FileText className="h-4 w-4 text-indigo-400" />
                    <span>6. Audit Logs &amp; Detailed Input / Output Inspection</span>
                  </h3>
                  <p className="text-slate-400 mt-1">
                    Complete immutable compliance trail separating query Input and database Output.
                  </p>
                </div>

                <div className="space-y-2">
                  <h4 className="font-bold text-slate-200">Two Core Views in Audit Inspector:</h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-[11px]">
                    <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 space-y-1">
                      <strong className="text-indigo-400 block font-bold text-xs">Input Details:</strong>
                      <p className="text-slate-400">• Full SQL Statement / Database Command.</p>
                      <p className="text-slate-400">• AI Intent &amp; Reasoning context.</p>
                      <p className="text-slate-400">• Target Database &amp; Operation Type (READ/WRITE).</p>
                    </div>

                    <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 space-y-1">
                      <strong className="text-emerald-400 block font-bold text-xs">Output Details:</strong>
                      <p className="text-slate-400">• Interactive Data Table of returned rows.</p>
                      <p className="text-slate-400">• Total Rows Returned / Rows Affected.</p>
                      <p className="text-slate-400">• Actual execution latency in milliseconds (ms).</p>
                      <p className="text-slate-400">• Raw JSON viewer and 1-click result copy.</p>
                    </div>
                  </div>
                </div>
              </div>
            )}

          </div>
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3.5 border-t border-slate-800 bg-slate-950/80 flex justify-between items-center flex-shrink-0">
          <span className="text-[11px] text-slate-500">
            AegisGate Protection Protocol • Enterprise AI Database Gateway
          </span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition-colors shadow-md shadow-indigo-600/30"
          >
            Got it, close guide
          </button>
        </div>

      </div>
    </div>
  );
};
