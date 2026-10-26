"use client";

import { useState, useCallback, useEffect, useMemo } from "react";
import { ExecutionResponse } from "@/types";
import {
  fetchExecutions as apiFetchExecutions,
  submitExecution as apiSubmitExecution,
  approveExecution as apiApproveExecution,
  rejectExecution as apiRejectExecution,
  abortExecution as apiAbortExecution,
} from "@/shared/lib/api";
import { useToast } from "@/shared/hooks/useToast";
import { useSse, SseEventPayload } from "@/shared/hooks/useSse";

export interface UseExecutionsOptions {
  initialExecutions?: ExecutionResponse[];
}

export function useExecutions(options?: UseExecutionsOptions) {
  const [executions, setExecutions] = useState<ExecutionResponse[]>(
    options?.initialExecutions || []
  );
  const [selectedExecution, setSelectedExecution] = useState<ExecutionResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [actionLoading, setActionLoading] = useState<boolean>(false);
  const { showToast } = useToast();

  const refresh = useCallback(async () => {
    try {
      const data = await apiFetchExecutions();
      setExecutions(data);
      setSelectedExecution((curr) => {
        if (!curr) return data[0] || null;
        return data.find((e) => e.id === curr.id) || curr;
      });
    } catch (err: unknown) {
      console.error("Failed to refresh executions:", err);
    }
  }, []);

  // Handle SSE events
  const handleSseEvent = useCallback(
    ({ event, data }: SseEventPayload) => {
      try {
        if (event === "execution_update" && data) {
          const updated: ExecutionResponse = data;
          setExecutions((prev) => {
            const exists = prev.some((e) => e.id === updated.id);
            if (exists) {
              return prev.map((e) => (e.id === updated.id ? updated : e));
            }
            return [updated, ...prev];
          });
          setSelectedExecution((curr) => (!curr || curr.id === updated.id ? updated : curr));
        } else if (
          typeof event === "string" &&
          event.startsWith("execution_")
        ) {
          void refresh();
        }
      } catch (err) {
        console.error("SSE handler error:", err);
      }
    },
    [refresh]
  );

  const { status: sseStatus } = useSse({
    onEvent: handleSseEvent,
  });
  const isConnected = sseStatus === "connected";

  // Polling safety net every 10s
  useEffect(() => {
    const timer = setInterval(() => {
      if (typeof document !== "undefined" && document.visibilityState === "visible") {
        void refresh();
      }
    }, 10000);
    return () => clearInterval(timer);
  }, [refresh]);

  // Initial load
  useEffect(() => {
    setIsLoading(true);
    refresh().finally(() => setIsLoading(false));
  }, [refresh]);

  const submitQuery = useCallback(
    async (targetId: string, query: string, reasoning: string) => {
      setIsSubmitting(true);
      try {
        const newExec = await apiSubmitExecution({
          target_id: targetId,
          query,
          reasoning,
        });
        setExecutions((prev) => [newExec, ...prev.filter((e) => e.id !== newExec.id)]);
        setSelectedExecution(newExec);
        showToast(`Execution #${newExec.id} submitted successfully`, "success");
        return newExec;
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : "Failed to submit execution";
        showToast(msg, "error");
        throw err;
      } finally {
        setIsSubmitting(false);
      }
    },
    [showToast]
  );

  const approve = useCallback(
    async (id: string, reviewer: string = "Admin Dashboard") => {
      setActionLoading(true);
      try {
        const updated = await apiApproveExecution(id, reviewer);
        setExecutions((prev) => prev.map((e) => (e.id === updated.id ? updated : e)));
        setSelectedExecution(updated);
        showToast(`Execution #${id} approved and resumed`, "success");
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : "Approval failed";
        showToast(msg, "error");
        throw err;
      } finally {
        setActionLoading(false);
      }
    },
    [showToast]
  );

  const reject = useCallback(
    async (id: string, reason: string = "Rejected by operator") => {
      setActionLoading(true);
      try {
        const updated = await apiRejectExecution(id, reason);
        setExecutions((prev) => prev.map((e) => (e.id === updated.id ? updated : e)));
        setSelectedExecution(updated);
        showToast(`Execution #${id} rejected`, "info");
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : "Rejection failed";
        showToast(msg, "error");
        throw err;
      } finally {
        setActionLoading(false);
      }
    },
    [showToast]
  );

  const abort = useCallback(
    async (id: string) => {
      setActionLoading(true);
      try {
        const updated = await apiAbortExecution(id);
        setExecutions((prev) => prev.map((e) => (e.id === updated.id ? updated : e)));
        setSelectedExecution(updated);
        showToast(`Execution #${id} aborted and process killed`, "warning");
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : "Abort failed";
        showToast(msg, "error");
        throw err;
      } finally {
        setActionLoading(false);
      }
    },
    [showToast]
  );

  return {
    executions,
    setExecutions,
    selectedExecution,
    setSelectedExecution,
    isLoading,
    isSubmitting,
    actionLoading,
    sseStatus,
    isConnected,
    refresh,
    submitQuery,
    approve,
    reject,
    abort,
  };
}
