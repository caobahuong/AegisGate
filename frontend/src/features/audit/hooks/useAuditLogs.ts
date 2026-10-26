"use client";

import { useState, useMemo, useCallback } from "react";
import { ExecutionResponse, PluginProfileResponse } from "@/types";
import { useToast } from "@/shared/hooks/useToast";

export interface UseAuditLogsOptions {
  logs?: ExecutionResponse[];
  executions?: ExecutionResponse[];
  plugins?: PluginProfileResponse[];
  initialLimit?: number;
}

export function useAuditLogs({
  logs,
  executions,
  plugins = [],
  initialLimit = 50,
}: UseAuditLogsOptions) {
  const logList = useMemo(() => logs || executions || [], [logs, executions]);
  const [searchTerm, setSearchTerm] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");
  const [selectedLog, setSelectedLog] = useState<ExecutionResponse | null>(null);
  const [modalTab, setModalTab] = useState<"output" | "input" | "governance">("output");
  const [outputViewMode, setOutputViewMode] = useState<"table" | "json">("table");
  const [limit, setLimit] = useState<number>(initialLimit);
  const { showToast } = useToast();

  const filteredLogs = useMemo(() => {
    return logList.filter((log) => {
      const matchesSearch =
        log.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
        log.query.toLowerCase().includes(searchTerm.toLowerCase()) ||
        log.target_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
        (log.reasoning && log.reasoning.toLowerCase().includes(searchTerm.toLowerCase()));

      const matchesStatus = statusFilter === "ALL" || log.status === statusFilter;
      return matchesSearch && matchesStatus;
    });
  }, [logList, searchTerm, statusFilter]);

  const visibleLogs = useMemo(() => {
    return filteredLogs.slice(0, limit);
  }, [filteredLogs, limit]);

  const hasMore = visibleLogs.length < filteredLogs.length;

  const loadMore = useCallback(() => {
    setLimit((prev) => prev + 50);
  }, []);

  const getPluginName = useCallback(
    (targetId: string): string => {
      const found = plugins.find((p) => p.id === targetId);
      return found ? found.name : targetId;
    },
    [plugins]
  );

  const copyToClipboard = useCallback(
    (text: string, label: string) => {
      if (typeof navigator !== "undefined" && navigator.clipboard) {
        navigator.clipboard.writeText(text);
      } else {
        const textarea = document.createElement("textarea");
        textarea.value = text;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand("copy");
        document.body.removeChild(textarea);
      }
      showToast(`${label} copied to clipboard`, "info");
    },
    [showToast]
  );

  return {
    searchTerm,
    setSearchTerm,
    statusFilter,
    setStatusFilter,
    selectedLog,
    setSelectedLog,
    modalTab,
    setModalTab,
    outputViewMode,
    setOutputViewMode,
    filteredLogs,
    visibleLogs,
    hasMore,
    loadMore,
    totalCount: filteredLogs.length,
    getPluginName,
    copyToClipboard,
  };
}
