"use client";

import React from "react";
import { Activity, RefreshCw, AlertCircle } from "lucide-react";
import { cn } from "@/lib/utils";
import { SseConnectionStatus } from "@/shared/hooks/useSse";

export interface SseIndicatorProps {
  status: SseConnectionStatus;
  onRetry?: () => void;
  className?: string;
}

export const SseIndicator: React.FC<SseIndicatorProps> = ({ status, onRetry, className }) => {
  const statusConfig = {
    connected: {
      label: "Live Stream",
      subLabel: "Connected",
      badgeClass: "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/20",
      dotClass: "bg-emerald-500 animate-pulse",
      icon: Activity,
    },
    reconnecting: {
      label: "Live Stream",
      subLabel: "Reconnecting...",
      badgeClass: "bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-500/20",
      dotClass: "bg-amber-500",
      icon: RefreshCw,
    },
    offline: {
      label: "Live Stream",
      subLabel: "Offline",
      badgeClass: "bg-rose-500/10 text-rose-700 dark:text-rose-400 border-rose-500/20",
      dotClass: "bg-rose-500",
      icon: AlertCircle,
    },
  };

  const current = statusConfig[status];
  const Icon = current.icon;

  return (
    <div
      role="status"
      aria-live="polite"
      data-testid="sse-status-indicator"
      className={cn(
        "flex items-center space-x-2 px-2.5 py-1 rounded-full border text-xs font-semibold select-none",
        current.badgeClass,
        className
      )}
      title={`Real-time SSE event bus status: ${current.subLabel}`}
    >
      <span className={cn("h-2 w-2 rounded-full", current.dotClass)} aria-hidden="true" />
      <Icon
        className={cn("h-3 w-3", status === "reconnecting" && "animate-spin")}
        aria-hidden="true"
      />
      <span className="hidden md:inline font-medium">{current.label}:</span>
      <span className="font-bold">{current.subLabel}</span>

      {status === "offline" && onRetry && (
        <button
          type="button"
          onClick={onRetry}
          aria-label="Retry real-time connection"
          className="ml-1 px-1.5 py-0.5 rounded text-[10px] bg-rose-600 text-white hover:bg-rose-500 transition-colors"
        >
          Retry
        </button>
      )}
    </div>
  );
};
