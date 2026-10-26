"use client";

import React, { useState } from "react";
import { Eye, EyeOff } from "lucide-react";
import { UiFieldSchema } from "@/types";

export interface DynamicFormFieldProps {
  field: UiFieldSchema;
  value: unknown;
  onChange: (val: unknown) => void;
}

export const DynamicFormField: React.FC<DynamicFormFieldProps> = ({ field, value, onChange }) => {
  const [showPassword, setShowPassword] = useState<boolean>(false);
  const stringVal = value !== undefined && value !== null ? String(value) : "";
  const fieldId = `field-${field.key}`;

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between">
        <label
          htmlFor={fieldId}
          className="text-[11px] font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider flex items-center space-x-1"
        >
          <span>{field.label}</span>
          {field.required && <span className="text-amber-500 font-bold">*</span>}
        </label>
        {field.type === "password" && (
          <button
            type="button"
            onClick={() => setShowPassword(!showPassword)}
            className="text-[10px] text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200 flex items-center space-x-1 focus:outline-none"
          >
            {showPassword ? <EyeOff className="h-3 w-3" /> : <Eye className="h-3 w-3" />}
            <span>{showPassword ? "Hide" : "Show"}</span>
          </button>
        )}
      </div>

      {field.type === "select" ? (
        <select
          id={fieldId}
          value={stringVal}
          onChange={(e) => onChange(e.target.value)}
          required={field.required}
          className="w-full bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-900 dark:text-slate-100 focus:outline-none focus:border-indigo-500 shadow-xs"
        >
          {field.options?.map((opt) => (
            <option key={opt} value={opt} className="bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100">
              {opt}
            </option>
          ))}
        </select>
      ) : field.type === "password" ? (
        <input
          id={fieldId}
          type={showPassword ? "text" : "password"}
          value={stringVal}
          onChange={(e) => onChange(e.target.value)}
          placeholder={field.placeholder || "••••••••"}
          required={field.required}
          className="w-full bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-900 dark:text-slate-100 font-mono focus:outline-none focus:border-indigo-500 shadow-xs"
        />
      ) : field.type === "number" ? (
        <input
          id={fieldId}
          type="number"
          value={stringVal}
          onChange={(e) => onChange(e.target.value === "" ? "" : Number(e.target.value))}
          placeholder={field.placeholder}
          required={field.required}
          className="w-full bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-900 dark:text-slate-100 font-mono focus:outline-none focus:border-indigo-500 shadow-xs"
        />
      ) : field.type === "textarea" ? (
        <textarea
          id={fieldId}
          rows={3}
          value={stringVal}
          onChange={(e) => onChange(e.target.value)}
          placeholder={field.placeholder}
          required={field.required}
          className="w-full bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-900 dark:text-slate-100 font-mono focus:outline-none focus:border-indigo-500 resize-y shadow-xs"
        />
      ) : (
        <input
          id={fieldId}
          type="text"
          value={stringVal}
          onChange={(e) => onChange(e.target.value)}
          placeholder={field.placeholder}
          required={field.required}
          className="w-full bg-white dark:bg-slate-950 border border-slate-300 dark:border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-900 dark:text-slate-100 font-mono focus:outline-none focus:border-indigo-500 shadow-xs"
        />
      )}

      {field.description && (
        <p className="text-[10px] text-slate-500 dark:text-slate-400 leading-tight">{field.description}</p>
      )}
    </div>
  );
};
