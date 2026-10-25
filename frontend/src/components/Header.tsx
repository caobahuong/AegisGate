"use client";

import React from "react";
import { Shield, Zap, Server, Terminal, Sun, Moon } from "lucide-react";
import { cn } from "@/lib/utils";

interface HeaderProps {
  autoMode: boolean;
  onToggleAutoMode: () => void;
  mcpOnline?: boolean;
  onOpenMcpModal?: () => void;
  theme?: "light" | "dark";
  onToggleTheme?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  autoMode,
  onToggleAutoMode,
  mcpOnline = true,
  onOpenMcpModal,
  theme = "light",
  onToggleTheme,
}) => {
  return (
    <header className="h-16 flex-shrink-0 w-full bg-slate-900 border-b border-slate-800 px-6 flex items-center justify-between sticky top-0 z-50">
      {/* Brand & Identity */}
      <div className="flex items-center space-x-3">
        <div className="h-9 w-9 rounded-lg bg-indigo-600 flex items-center justify-center shadow-lg shadow-indigo-600/30">
          <Shield className="h-5 w-5 text-white" />
        </div>
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-sm font-bold tracking-tight text-slate-100">AEGISGATE</h1>
            <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              v1.0 Core
            </span>
          </div>
          <p className="text-[11px] text-slate-400 hidden sm:block">
            AI Execution Proxy &amp; Pluggable Harness Platform
          </p>
        </div>
      </div>

      {/* Center / Status */}
      <div className="flex items-center space-x-3 sm:space-x-4">
        {/* MCP Server Status Indicator & Snippet Button */}
        <div className="flex items-center space-x-2.5 px-3 py-1.5 rounded-full bg-slate-950/60 border border-slate-800">
          <Server className="h-3.5 w-3.5 text-slate-400" />
          <span className="text-xs text-slate-300 font-medium hidden md:inline">MCP Server:</span>
          <div className="flex items-center space-x-1.5">
            <span
              className={cn(
                "h-2 w-2 rounded-full",
                mcpOnline ? "bg-emerald-400 animate-pulse" : "bg-red-500"
              )}
            />
            <span className="text-xs font-mono text-emerald-400 font-medium">
              {mcpOnline ? "Active" : "Offline"}
            </span>
          </div>

          {onOpenMcpModal && (
            <button
              onClick={onOpenMcpModal}
              data-testid="header-mcp-btn"
              className="flex items-center space-x-1 px-2.5 py-0.5 rounded-full bg-indigo-50 hover:bg-indigo-100 text-indigo-700 border border-indigo-200 dark:bg-indigo-600/20 dark:hover:bg-indigo-600/35 dark:text-indigo-400 dark:hover:text-indigo-300 dark:border-indigo-500/30 text-[11px] font-semibold transition-all shadow-xs"
              title="View and Copy MCP JSON for Claude, Cursor, and Cline"
            >
              <Terminal className="h-3 w-3 text-indigo-600 dark:text-indigo-400" />
              <span>MCP Config</span>
            </button>
          )}
        </div>

        {/* Auto Approval Mode Switch */}
        <button
          onClick={onToggleAutoMode}
          className={cn(
            "flex items-center space-x-2 px-3.5 py-1.5 rounded-lg border text-xs font-semibold transition-all duration-200",
            autoMode
              ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30 hover:bg-emerald-500/20"
              : "bg-amber-500/10 text-amber-400 border-amber-500/30 hover:bg-amber-500/20"
          )}
          title="Toggle Auto Approval Mode"
        >
          <Zap className={cn("h-3.5 w-3.5", autoMode ? "text-emerald-400" : "text-amber-400")} />
          <span className="hidden sm:inline">Auto Mode:</span>
          <span className="font-bold tracking-wide">{autoMode ? "ON" : "OFF (Manual Review)"}</span>
        </button>

        {/* Theme Switcher Button (Light Default / Dark) */}
        {onToggleTheme && (
          <button
            onClick={onToggleTheme}
            data-testid="theme-toggle-btn"
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border border-slate-700 hover:border-slate-600 bg-slate-800 hover:bg-slate-750 text-slate-200 text-xs font-semibold transition-all shadow-sm"
            title={`Current theme: ${theme}. Click to switch to ${theme === "light" ? "Dark" : "Light"} Mode`}
          >
            {theme === "light" ? (
              <>
                <Moon className="h-3.5 w-3.5 text-indigo-400" />
                <span className="hidden sm:inline">Dark</span>
              </>
            ) : (
              <>
                <Sun className="h-3.5 w-3.5 text-amber-400" />
                <span className="hidden sm:inline">Light</span>
              </>
            )}
          </button>
        )}
      </div>
    </header>
  );
};
