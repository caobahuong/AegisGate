"use client";

import React, { createContext, useContext, useState, useCallback } from "react";
import { CheckCircle2, AlertCircle, AlertTriangle, Info, X } from "lucide-react";
import { cn } from "@/lib/utils";

export type ToastType = "success" | "error" | "warning" | "info";

export interface ToastItem {
  id: string;
  message: string;
  type: ToastType;
  durationMs: number;
}

interface ToastContextValue {
  toasts: ToastItem[];
  showToast: (message: string, type?: ToastType, durationMs?: number) => void;
  dismissToast: (id: string) => void;
}

const ToastContext = createContext<ToastContextValue | undefined>(undefined);

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const dismissToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const showToast = useCallback(
    (message: string, type: ToastType = "info", durationMs: number = 5000) => {
      const id = `toast-${Date.now()}-${Math.random().toString(36).substring(2, 7)}`;
      const newToast: ToastItem = { id, message, type, durationMs };

      setToasts((prev) => [...prev, newToast]);

      if (durationMs > 0) {
        setTimeout(() => {
          dismissToast(id);
        }, durationMs);
      }
    },
    [dismissToast]
  );

  return (
    <ToastContext.Provider value={{ toasts, showToast, dismissToast }}>
      {children}
      {/* Toast Region */}
      <div
        aria-live="polite"
        aria-atomic="false"
        className="fixed bottom-4 right-4 z-[100] flex flex-col space-y-2 max-w-md w-full pointer-events-none px-4 sm:px-0"
      >
        {toasts.map((toast) => {
          const isAlert = toast.type === "error" || toast.type === "warning";
          return (
            <div
              key={toast.id}
              role={isAlert ? "alert" : "status"}
              aria-live={isAlert ? "assertive" : "polite"}
              data-testid={`toast-${toast.type}`}
              className={cn(
                "pointer-events-auto flex items-start space-x-3 p-3.5 rounded-xl border shadow-xl transition-all animate-in fade-in slide-in-from-bottom-3 duration-200 text-xs",
                toast.type === "success" &&
                  "bg-emerald-50 dark:bg-slate-900 border-emerald-300 dark:border-emerald-500/40 text-emerald-900 dark:text-emerald-300 shadow-emerald-500/5",
                toast.type === "error" &&
                  "bg-rose-50 dark:bg-slate-900 border-rose-300 dark:border-rose-500/40 text-rose-900 dark:text-rose-300 shadow-rose-500/5",
                toast.type === "warning" &&
                  "bg-amber-50 dark:bg-slate-900 border-amber-300 dark:border-amber-500/40 text-amber-900 dark:text-amber-300 shadow-amber-500/5",
                toast.type === "info" &&
                  "bg-indigo-50 dark:bg-slate-900 border-indigo-300 dark:border-indigo-500/40 text-indigo-900 dark:text-indigo-300 shadow-indigo-500/5"
              )}
            >
              <div className="flex-shrink-0 mt-0.5">
                {toast.type === "success" && (
                  <CheckCircle2 className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
                )}
                {toast.type === "error" && (
                  <AlertCircle className="h-4 w-4 text-rose-600 dark:text-rose-400" />
                )}
                {toast.type === "warning" && (
                  <AlertTriangle className="h-4 w-4 text-amber-600 dark:text-amber-400" />
                )}
                {toast.type === "info" && (
                  <Info className="h-4 w-4 text-indigo-600 dark:text-indigo-400" />
                )}
              </div>

              <div className="flex-1 font-medium leading-relaxed pr-1 break-words">
                {toast.message}
              </div>

              <button
                type="button"
                onClick={() => dismissToast(toast.id)}
                aria-label="Dismiss notification"
                data-testid="toast-dismiss-btn"
                className="flex-shrink-0 p-1 -mr-1 rounded-md text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200 hover:bg-slate-200/50 dark:hover:bg-slate-800 transition-colors"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
};

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) {
    return {
      showToast: () => "",
      dismissToast: () => {},
    };
  }
  return context;
}
