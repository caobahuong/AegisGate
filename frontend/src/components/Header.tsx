"use client";

import React from "react";
import { Shield, Zap, Server, Terminal, Sun, Moon } from "lucide-react";
import { cn } from "@/lib/utils";
import { SseIndicator } from "@/shared/ui/SseIndicator";
import { SseConnectionStatus } from "@/shared/hooks/useSse";

export interface HeaderProps {
  autoMode: boolean;
  onToggleAutoMode: () => void;
  mcpOnline?: boolean;
  sseStatus?: SseConnectionStatus;
  onRetrySse?: () => void;
  onOpenMcpModal?: () => void;
  theme?: "light" | "dark";
  onToggleTheme?: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  autoMode,
  onToggleAutoMode,
  mcpOnline = true,
  sseStatus,
  onRetrySse,
  onOpenMcpModal,
  theme = "light",
  onToggleTheme,
}) => {
  const currentSseStatus: SseConnectionStatus = sseStatus ?? (mcpOnline ? "connected" : "offline");

  return (
    <header className="h-16 flex-shrink-0 w-full bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 px-6 flex items-center justify-between sticky top-0 z-50">
      {/* Brand & Identity */}
      <div className="flex items-center space-x-3">
        <div className="h-9 w-9 rounded-lg bg-indigo-600 flex items-center justify-center shadow-lg shadow-indigo-600/30">
          <Shield className="h-5 w-5 text-white" />
        </div>
        <div>
          <div className="flex items-center space-x-2">
            <h1 className="text-sm font-bold tracking-tight text-slate-900 dark:text-slate-100">
              AEGISGATE
            </h1>
            <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded bg-indigo-50 dark:bg-indigo-500/10 text-indigo-700 dark:text-indigo-400 border border-indigo-200 dark:border-indigo-500/20">
              v1.0 Core
            </span>
          </div>
          <p className="text-[11px] text-slate-500 dark:text-slate-400 hidden sm:block">
            AI Execution Proxy &amp; Pluggable Harness Platform
          </p>
        </div>
      </div>

      {/* Center / Status */}
      <div className="flex items-center space-x-3 sm:space-x-4">
        {/* SSE Stream Status Indicator */}
        <SseIndicator status={currentSseStatus} onRetry={onRetrySse} />

        {/* MCP Server Status Indicator & Snippet Button */}
        <div className="flex items-center space-x-2.5 px-3 py-1.5 rounded-full bg-slate-50 dark:bg-slate-950/60 border border-slate-200 dark:border-slate-800">
          <Server className="h-3.5 w-3.5 text-slate-500 dark:text-slate-400" />
          <span className="text-xs text-slate-700 dark:text-slate-300 font-medium hidden md:inline">
            MCP Server:
          </span>
          <div className="flex items-center space-x-1.5">
            <span
              className={cn(
                "h-2 w-2 rounded-full",
                mcpOnline ? "bg-emerald-500 animate-pulse" : "bg-red-500"
              )}
            />
            <span className="text-xs font-mono text-emerald-700 dark:text-emerald-400 font-medium">
              {mcpOnline ? "Active" : "Offline"}
            </span>
          </div>

          {onOpenMcpModal && (
            <button
              onClick={onOpenMcpModal}
              data-testid="header-mcp-btn"
              aria-label="View and Copy MCP JSON configuration"
              className="flex items-center space-x-1 px-2.5 py-0.5 rounded-full bg-indigo-50 hover:bg-indigo-100 text-indigo-700 border border-indigo-200 dark:bg-indigo-600/20 dark:hover:bg-indigo-600/35 dark:text-indigo-400 dark:hover:text-indigo-300 dark:border-indigo-500/30 text-[11px] font-semibold transition-all shadow-xs focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
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
          aria-label={`Toggle auto approval mode, currently ${autoMode ? "ON" : "OFF"}`}
          className={cn(
            "flex items-center space-x-2 px-3.5 py-1.5 rounded-lg border text-xs font-semibold transition-all duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500",
            autoMode
              ? "bg-emerald-50 text-emerald-700 border-emerald-300 dark:bg-emerald-500/10 dark:text-emerald-400 dark:border-emerald-500/30 hover:bg-emerald-100 dark:hover:bg-emerald-500/20"
              : "bg-amber-50 text-amber-700 border-amber-300 dark:bg-amber-500/10 dark:text-amber-400 dark:border-amber-500/30 hover:bg-amber-100 dark:hover:bg-amber-500/20"
          )}
          title="Toggle Auto Approval Mode"
        >
          <Zap
            className={cn(
              "h-3.5 w-3.5",
              autoMode
                ? "text-emerald-600 dark:text-emerald-400"
                : "text-amber-600 dark:text-amber-400"
            )}
          />
          <span className="hidden sm:inline">Auto Mode:</span>
          <span className="font-bold tracking-wide">{autoMode ? "ON" : "OFF (Manual Review)"}</span>
        </button>

        {/* Theme Switcher Button */}
        {onToggleTheme && (
          <button
            onClick={onToggleTheme}
            data-testid="theme-toggle-btn"
            aria-label={`Switch to ${theme === "light" ? "Dark" : "Light"} mode`}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border border-slate-300 dark:border-slate-700 hover:border-slate-400 dark:hover:border-slate-600 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-750 text-slate-800 dark:text-slate-200 text-xs font-semibold transition-all shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
            title={`Current theme: ${theme}. Click to switch to ${theme === "light" ? "Dark" : "Light"} Mode`}
          >
            {theme === "light" ? (
              <>
                <Moon className="h-3.5 w-3.5 text-indigo-600 dark:text-indigo-400" />
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
