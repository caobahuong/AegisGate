"use client";

import { useEffect, useState, useRef, useCallback } from "react";

export type SseConnectionStatus = "connected" | "reconnecting" | "offline";

export interface SseEventPayload {
  event: string;
  data: any;
  timestamp: number;
}

interface UseSseOptions {
  url?: string;
  enabled?: boolean;
  onEvent?: (payload: SseEventPayload) => void;
  onStatusChange?: (status: SseConnectionStatus) => void;
}

const SSE_EVENT_NAMES = [
  "execution_created",
  "execution_paused",
  "execution_resumed",
  "execution_auto_approved",
  "execution_completed",
  "execution_rejected",
  "execution_failed",
  "execution_timeout",
  "execution_aborted",
  "plugin_installed",
  "plugin_status_changed",
];

export function useSse({
  url = "/api/monitor/events",
  enabled = true,
  onEvent,
  onStatusChange,
}: UseSseOptions = {}) {
  const [status, setStatusState] = useState<SseConnectionStatus>("reconnecting");
  const [lastEventTime, setLastEventTime] = useState<number | null>(null);

  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const backoffDelayRef = useRef<number>(1000);
  const retryCountRef = useRef<number>(0);

  const onEventRef = useRef(onEvent);
  onEventRef.current = onEvent;

  const onStatusChangeRef = useRef(onStatusChange);
  onStatusChangeRef.current = onStatusChange;

  const setStatus = useCallback((nextStatus: SseConnectionStatus) => {
    setStatusState(nextStatus);
    onStatusChangeRef.current?.(nextStatus);
  }, []);

  const connect = useCallback(() => {
    if (!enabled || typeof window === "undefined") return;

    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }

    try {
      const resolvedUrl =
        url.startsWith("http://") || url.startsWith("https://")
          ? url
          : `${process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000"}${url}`;

      const es = new EventSource(resolvedUrl);
      eventSourceRef.current = es;

      es.onopen = () => {
        setStatus("connected");
        backoffDelayRef.current = 1000;
        retryCountRef.current = 0;
      };

      const handleEventData = (eventName: string, e: MessageEvent) => {
        let parsedData = null;
        try {
          parsedData = JSON.parse(e.data);
        } catch {
          parsedData = e.data;
        }

        const now = Date.now();
        setLastEventTime(now);

        onEventRef.current?.({
          event: eventName,
          data: parsedData,
          timestamp: now,
        });
      };

      es.onmessage = (e) => handleEventData("message", e);

      SSE_EVENT_NAMES.forEach((name) => {
        es.addEventListener(name, (e: any) => handleEventData(name, e));
      });

      es.onerror = () => {
        es.close();
        eventSourceRef.current = null;

        retryCountRef.current += 1;
        const currentRetry = retryCountRef.current;

        if (currentRetry > 5) {
          setStatus("offline");
        } else {
          setStatus("reconnecting");
        }

        const delay = Math.min(backoffDelayRef.current, 10000);
        backoffDelayRef.current = Math.min(delay * 2, 10000);

        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current);
        }

        reconnectTimeoutRef.current = setTimeout(() => {
          connect();
        }, delay);
      };
    } catch {
      setStatus("offline");
    }
  }, [enabled, url, setStatus]);

  useEffect(() => {
    if (enabled) {
      connect();
    }

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
    };
  }, [enabled, connect]);

  const retry = useCallback(() => {
    backoffDelayRef.current = 1000;
    retryCountRef.current = 0;
    connect();
  }, [connect]);

  return { status, lastEventTime, retry };
}
