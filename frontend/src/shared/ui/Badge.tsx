"use client";

import React from "react";
import { cn } from "@/lib/utils";

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: "success" | "warning" | "danger" | "info" | "neutral";
  size?: "sm" | "md";
  dot?: boolean;
  icon?: React.ReactNode;
}

export const Badge: React.FC<BadgeProps> = ({
  className,
  variant = "neutral",
  size = "md",
  dot = false,
  icon,
  children,
  ...props
}) => {
  const baseStyles =
    "inline-flex items-center font-semibold rounded-md border font-mono select-none tracking-wide";

  const sizeStyles = {
    sm: "text-[10px] px-1.5 py-0.5 space-x-1",
    md: "text-xs px-2 py-0.5 space-x-1.5",
  };

  const variantStyles = {
    success:
      "bg-emerald-50 dark:bg-emerald-500/10 text-emerald-800 dark:text-emerald-400 border-emerald-300 dark:border-emerald-500/30",
    warning:
      "bg-amber-50 dark:bg-amber-500/10 text-amber-800 dark:text-amber-400 border-amber-300 dark:border-amber-500/30",
    danger:
      "bg-rose-50 dark:bg-rose-500/10 text-rose-800 dark:text-rose-400 border-rose-300 dark:border-rose-500/30",
    info:
      "bg-indigo-50 dark:bg-indigo-500/10 text-indigo-800 dark:text-indigo-400 border-indigo-300 dark:border-indigo-500/30",
    neutral:
      "bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-300 border-slate-300 dark:border-slate-700",
  };

  const dotColors = {
    success: "bg-emerald-600 dark:bg-emerald-400",
    warning: "bg-amber-600 dark:bg-amber-400",
    danger: "bg-rose-600 dark:bg-rose-400",
    info: "bg-indigo-600 dark:bg-indigo-400",
    neutral: "bg-slate-500 dark:bg-slate-400",
  };

  return (
    <span className={cn(baseStyles, sizeStyles[size], variantStyles[variant], className)} {...props}>
      {dot && <span className={cn("h-1.5 w-1.5 rounded-full flex-shrink-0", dotColors[variant])} aria-hidden="true" />}
      {icon && <span className="flex-shrink-0" aria-hidden="true">{icon}</span>}
      <span>{children}</span>
    </span>
  );
};
