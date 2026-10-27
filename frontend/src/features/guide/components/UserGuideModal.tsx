"use client";

import React, { useState } from "react";
import {
  BookOpen,
  Layers,
  Terminal,
  Shield,
  Activity,
  Boxes,
  FileText,
  Sparkles,
} from "lucide-react";
import { Modal } from "@/shared/ui/Modal";
import { Button } from "@/shared/ui/Button";
import { getBackendOrigin } from "@/shared/lib/api";
import { cn } from "@/lib/utils";
import { GuideOverviewSection } from "./GuideOverviewSection";
import { GuideMcpSection } from "./GuideMcpSection";
import { GuidePluginsSection } from "./GuidePluginsSection";
import { GuideRulesSection } from "./GuideRulesSection";
import { GuideExecutionSection } from "./GuideExecutionSection";
import { GuideAuditSection } from "./GuideAuditSection";

export interface UserGuideModalProps {
  isOpen: boolean;
  onClose: () => void;
}

type GuideSection = "overview" | "mcp" | "plugins" | "rules" | "execution" | "audit";

const SECTIONS = [
  {
    id: "overview" as GuideSection,
    label: "1. Overview & Architecture",
    icon: Layers,
  },
  {
    id: "mcp" as GuideSection,
    label: "2. AI Connection via MCP",
    icon: Terminal,
  },
  { id: "plugins" as GuideSection, label: "3. Pluggable Targets", icon: Boxes },
  {
    id: "rules" as GuideSection,
    label: "4. Governance Rules & Scope",
    icon: Shield,
  },
  {
    id: "execution" as GuideSection,
    label: "5. Live Monitor & Approvals",
    icon: Activity,
  },
  {
    id: "audit" as GuideSection,
    label: "6. Audit Logs Input / Output",
    icon: FileText,
  },
];

export const UserGuideModal: React.FC<UserGuideModalProps> = ({ isOpen, onClose }) => {
  const [activeSection, setActiveSection] = useState<GuideSection>("overview");
  const backendUrl = getBackendOrigin();

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="AegisGate System User Guide"
      subtitle="Operational manual for the Zero-Trust Database Gateway for AI Agents (Claude, Cursor, Cline)"
      icon={<BookOpen className="h-5 w-5" />}
      maxWidth="4xl"
      className="p-0 overflow-hidden"
    >
      <div className="flex flex-col md:flex-row min-h-[500px] max-h-[70vh] -m-6 overflow-hidden">
        {/* Left Navigation Sidebar */}
        <nav
          aria-label="Documentation Topics"
          className="w-full md:w-60 border-b md:border-b-0 md:border-r border-slate-200 dark:border-slate-800 p-4 space-y-1.5 bg-slate-50/60 dark:bg-slate-950/40 flex-shrink-0 overflow-y-auto select-none"
        >
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block px-2.5 pb-1">
            Topics
          </span>
          {SECTIONS.map((sec) => {
            const Icon = sec.icon;
            const isActive = activeSection === sec.id;
            return (
              <button
                key={sec.id}
                type="button"
                onClick={() => setActiveSection(sec.id)}
                className={cn(
                  "w-full flex items-center space-x-2.5 px-3 py-2 rounded-lg text-xs font-medium transition-all text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500",
                  isActive
                    ? "bg-indigo-50 dark:bg-indigo-600/20 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-500/30 font-semibold shadow-xs"
                    : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800/40"
                )}
              >
                <Icon
                  className={cn(
                    "h-4 w-4 flex-shrink-0",
                    isActive ? "text-indigo-600 dark:text-indigo-400" : "text-slate-400"
                  )}
                  aria-hidden="true"
                />
                <span className="truncate">{sec.label}</span>
              </button>
            );
          })}

          <div className="pt-4 border-t border-slate-200 dark:border-slate-800/80 mt-4 space-y-2">
            <div className="p-2.5 rounded-lg bg-indigo-50 dark:bg-indigo-600/10 border border-indigo-200 dark:border-indigo-500/20 space-y-1">
              <span className="text-[10px] font-bold text-indigo-700 dark:text-indigo-400 flex items-center space-x-1">
                <Sparkles className="h-3 w-3" aria-hidden="true" />
                <span>Gateway Status</span>
              </span>
              <p className="text-[11px] text-slate-600 dark:text-slate-300 leading-snug">
                MCP Server is active at{" "}
                <code className="text-indigo-700 dark:text-indigo-300 font-mono text-[10px] font-bold">
                  {backendUrl}
                </code>
              </p>
            </div>
          </div>
        </nav>

        {/* Right Content Area */}
        <div className="flex-1 p-6 overflow-y-auto space-y-6 text-xs text-slate-700 dark:text-slate-300 leading-relaxed bg-white dark:bg-slate-900">
          {activeSection === "overview" && <GuideOverviewSection />}
          {activeSection === "mcp" && <GuideMcpSection />}
          {activeSection === "plugins" && <GuidePluginsSection />}
          {activeSection === "rules" && <GuideRulesSection />}
          {activeSection === "execution" && <GuideExecutionSection />}
          {activeSection === "audit" && <GuideAuditSection />}
        </div>
      </div>

      {/* Modal Footer */}
      <div className="flex items-center justify-between pt-4 mt-6 border-t border-slate-200 dark:border-slate-800 text-xs">
        <span className="text-[11px] text-slate-500 dark:text-slate-400 font-medium">
          AegisGate Protection Protocol • Enterprise AI Database Gateway
        </span>
        <Button variant="primary" size="sm" onClick={onClose} data-testid="close-user-guide-btn">
          Got it, close guide
        </Button>
      </div>
    </Modal>
  );
};
