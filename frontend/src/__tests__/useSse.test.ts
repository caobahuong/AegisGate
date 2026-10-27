import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useSse } from "@/shared/hooks/useSse";

class MockEventSource {
  static instances: MockEventSource[] = [];
  url: string;
  onopen: (() => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: (() => void) | null = null;
  listeners: Record<string, ((event: any) => void)[]> = {};

  constructor(url: string) {
    this.url = url;
    MockEventSource.instances.push(this);
  }

  addEventListener(event: string, cb: (event: any) => void) {
    if (!this.listeners[event]) this.listeners[event] = [];
    this.listeners[event].push(cb);
  }

  removeEventListener(event: string, cb: (event: any) => void) {
    if (this.listeners[event]) {
      this.listeners[event] = this.listeners[event].filter((l) => l !== cb);
    }
  }

  close() {
    // closed
  }

  simulateOpen() {
    if (this.onopen) this.onopen();
  }

  simulateMessage(data: any) {
    if (this.onmessage) {
      this.onmessage(new MessageEvent("message", { data: JSON.stringify(data) }));
    }
  }

  simulateEvent(name: string, data: any) {
    const handlers = this.listeners[name] || [];
    handlers.forEach((h) => h(new MessageEvent(name, { data: JSON.stringify(data) })));
  }

  simulateError() {
    if (this.onerror) this.onerror();
  }
}

describe("useSse Hook", () => {
  const originalEventSource = global.EventSource;

  beforeEach(() => {
    MockEventSource.instances = [];
    (global as any).EventSource = MockEventSource;
    vi.useFakeTimers();
  });

  afterEach(() => {
    (global as any).EventSource = originalEventSource;
    vi.useRealTimers();
  });

  it("connects to SSE URL and transitions status to connected on open", () => {
    const { result } = renderHook(() => useSse({ url: "/api/monitor/events" }));

    expect(result.current.status).toBe("reconnecting");
    expect(MockEventSource.instances.length).toBe(1);

    act(() => {
      MockEventSource.instances[0].simulateOpen();
    });

    expect(result.current.status).toBe("connected");
  });

  it("dispatches named events to onEvent callback", () => {
    const onEvent = vi.fn();
    renderHook(() => useSse({ url: "/api/monitor/events", onEvent }));

    act(() => {
      MockEventSource.instances[0].simulateOpen();
      MockEventSource.instances[0].simulateEvent("execution_created", {
        id: "exec_123",
      });
    });

    expect(onEvent).toHaveBeenCalledWith(
      expect.objectContaining({
        event: "execution_created",
        data: { id: "exec_123" },
      })
    );
  });

  it("handles errors and applies backoff retry", () => {
    const onStatusChange = vi.fn();
    const { result } = renderHook(() => useSse({ url: "/api/monitor/events", onStatusChange }));

    act(() => {
      MockEventSource.instances[0].simulateError();
    });

    expect(result.current.status).toBe("reconnecting");

    // Fast-forward backoff delay (1000ms)
    act(() => {
      vi.advanceTimersByTime(1000);
    });

    expect(MockEventSource.instances.length).toBe(2);
  });
});
