"use client";

import React from "react";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";

export interface LoadingSpinnerProps {
  label?: string;
  size?: "sm" | "md" | "lg";
  className?: string;
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  label = "Loading data...",
  size = "md",
  className,
}) => {
  const sizeMap = {
    sm: "h-3.5 w-3.5",
    md: "h-5 w-5",
    lg: "h-8 w-8",
  };

  return (
    <div
      role="status"
      aria-live="polite"
      className={cn("flex items-center justify-center space-x-2 text-slate-500 dark:text-slate-400 p-6", className)}
    >
      <Loader2 className={cn("animate-spin text-indigo-600 dark:text-indigo-400", sizeMap[size])} aria-hidden="true" />
      <span className="text-xs font-medium">{label}</span>
      <span className="sr-only">{label}</span>
    </div>
  );
};
