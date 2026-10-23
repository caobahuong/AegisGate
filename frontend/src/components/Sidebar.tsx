"use client";

import React from "react";
import { Activity, Boxes, BookOpen, FileText, Database, HelpCircle } from "lucide-react";
import { ActiveTab, PluginProfileResponse } from "@/types";
import { cn } from "@/lib/utils";

interface SidebarProps {
  activeTab: ActiveTab;
  onTabChange: (tab: ActiveTab) => void;
  plugins: PluginProfileResponse[];
  onOpenUserGuide?: () => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeTab,
  onTabChange,
  plugins,
  onOpenUserGuide,
}) => {
  const navItems = [
    {
      id: "monitor" as ActiveTab,
      label: "Live Execution Monitor",
      icon: Activity,
    },
    {
      id: "plugins" as ActiveTab,
      label: "Pluggable Targets",
      icon: Boxes,
    },
    {
      id: "knowledge" as ActiveTab,
      label: "Knowledge & Rules",
      icon: BookOpen,
    },
    {
      id: "logs" as ActiveTab,
      label: "Audit Logs",
      icon: FileText,
    },
  ];

  return (
    <aside className="w-64 flex-shrink-0 bg-slate-900 border-r border-slate-800 flex flex-col justify-between h-full overflow-hidden select-none">
      {/* Navigation Links */}
      <div className="p-4 space-y-1">
        <div className="px-3 py-2 text-[10px] font-bold uppercase tracking-wider text-slate-500">
          Core Harness Navigation
        </div>
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onTabChange(item.id)}
              className={cn(
                "w-full flex items-center space-x-3 px-3 py-2.5 rounded-lg text-xs font-medium transition-all duration-150",
                isActive
                  ? "bg-indigo-600/15 text-indigo-400 font-semibold border border-indigo-600/30"
                  : "text-slate-400 hover:text-slate-100 hover:bg-slate-800/60"
              )}
            >
              <Icon className={cn("h-4 w-4", isActive ? "text-indigo-400" : "text-slate-400")} />
              <span>{item.label}</span>
            </button>
          );
        })}

        {/* User Guide Button */}
        <div className="pt-3">
          <button
            onClick={onOpenUserGuide}
            data-testid="sidebar-user-guide-btn"
            className="w-full flex items-center space-x-3 px-3 py-2.5 rounded-lg text-xs font-semibold text-indigo-300 hover:text-white bg-indigo-600/10 hover:bg-indigo-600/20 border border-indigo-500/20 transition-all duration-150 shadow-sm"
          >
            <HelpCircle className="h-4 w-4 text-indigo-400 flex-shrink-0" />
            <span>User Guide & Docs</span>
          </button>
        </div>
      </div>

      {/* Connected Plugins Section at Bottom */}
      <div className="p-4 border-t border-slate-800/80 bg-slate-950/40">
        <div className="flex items-center justify-between mb-2">
          <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
            Connected Targets ({plugins.length})
          </span>
        </div>
        <div className="space-y-2 max-h-48 overflow-y-auto">
          {plugins.length === 0 ? (
            <p className="text-[11px] text-slate-500 italic">No plugins connected</p>
          ) : (
            plugins.map((plugin) => (
              <div
                key={plugin.id}
                data-testid={`sidebar-plugin-${plugin.id}`}
                className="flex items-center justify-between p-2 rounded bg-slate-900 border border-slate-800 text-[11px]"
              >
                <div className="flex items-center space-x-2 truncate">
                  <Database className="h-3.5 w-3.5 text-indigo-400 flex-shrink-0" />
                  <span className="text-slate-200 truncate font-medium">{plugin.name}</span>
                </div>
                <div className="flex items-center space-x-1.5 flex-shrink-0 ml-2">
                  <span
                    className={cn(
                      "h-1.5 w-1.5 rounded-full",
                      plugin.status === "active" ? "bg-emerald-400" : "bg-slate-500"
                    )}
                  />
                  <span className="text-[10px] text-slate-400 font-mono">
                    {plugin.latency_ms > 0 ? `${plugin.latency_ms}ms` : "idle"}
                  </span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </aside>
  );
};
