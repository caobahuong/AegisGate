"use client";

import React, { useId } from "react";
import { cn } from "@/lib/utils";

export interface FieldProps {
  label?: React.ReactNode;
  helperText?: React.ReactNode;
  error?: string;
  required?: boolean;
  className?: string;
  children: (props: { id: string; "aria-describedby"?: string; "aria-invalid"?: boolean }) => React.ReactNode;
}

export const Field: React.FC<FieldProps> = ({
  label,
  helperText,
  error,
  required = false,
  className,
  children,
}) => {
  const generatedId = useId();
  const inputId = `field-${generatedId}`;
  const helperId = helperText ? `helper-${generatedId}` : undefined;
  const errorId = error ? `error-${generatedId}` : undefined;
  const describedBy = [errorId, helperId].filter(Boolean).join(" ") || undefined;

  return (
    <div className={cn("space-y-1.5", className)}>
      {label && (
        <label htmlFor={inputId} className="block text-xs font-semibold text-slate-700 dark:text-slate-300">
          {label}
          {required && <span className="text-rose-500 ml-1" aria-hidden="true">*</span>}
        </label>
      )}
      {children({
        id: inputId,
        "aria-describedby": describedBy,
        "aria-invalid": !!error,
      })}
      {error && (
        <p id={errorId} role="alert" className="text-[11px] font-medium text-rose-600 dark:text-rose-400">
          {error}
        </p>
      )}
      {!error && helperText && (
        <p id={helperId} className="text-[11px] text-slate-500 dark:text-slate-400">
          {helperText}
        </p>
      )}
    </div>
  );
};
