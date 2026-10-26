"use client";

import React, { useRef } from "react";
import { cn } from "@/lib/utils";

export interface TabItem {
  id: string;
  label: React.ReactNode;
  icon?: React.ReactNode;
  badge?: React.ReactNode;
}

export interface TabsProps {
  items: TabItem[];
  activeTab: string;
  onTabChange: (id: string) => void;
  className?: string;
  variant?: "pill" | "underline";
}

export const Tabs: React.FC<TabsProps> = ({
  items,
  activeTab,
  onTabChange,
  className,
  variant = "pill",
}) => {
  const tabListRef = useRef<HTMLDivElement>(null);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLButtonElement>, index: number) => {
    let nextIndex = index;
    if (e.key === "ArrowRight") {
      e.preventDefault();
      nextIndex = (index + 1) % items.length;
    } else if (e.key === "ArrowLeft") {
      e.preventDefault();
      nextIndex = (index - 1 + items.length) % items.length;
    } else if (e.key === "Home") {
      e.preventDefault();
      nextIndex = 0;
    } else if (e.key === "End") {
      e.preventDefault();
      nextIndex = items.length - 1;
    } else {
      return;
    }

    onTabChange(items[nextIndex].id);
    const buttons = tabListRef.current?.querySelectorAll<HTMLButtonElement>('[role="tab"]');
    buttons?.[nextIndex]?.focus();
  };

  return (
    <div
      ref={tabListRef}
      role="tablist"
      aria-orientation="horizontal"
      className={cn(
        "flex items-center space-x-1 p-1 select-none",
        variant === "pill" && "bg-slate-100 dark:bg-slate-950/60 rounded-xl border border-slate-200 dark:border-slate-800",
        variant === "underline" && "border-b border-slate-200 dark:border-slate-800 space-x-4",
        className
      )}
    >
      {items.map((item, index) => {
        const isSelected = activeTab === item.id;
        return (
          <button
            key={item.id}
            role="tab"
            id={`tab-${item.id}`}
            aria-selected={isSelected}
            aria-controls={`tabpanel-${item.id}`}
            tabIndex={isSelected ? 0 : -1}
            onClick={() => onTabChange(item.id)}
            onKeyDown={(e) => handleKeyDown(e, index)}
            className={cn(
              "flex items-center space-x-2 text-xs font-semibold transition-all focus:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500",
              variant === "pill" && [
                "px-3.5 py-1.5 rounded-lg",
                isSelected
                  ? "bg-white dark:bg-slate-800 text-indigo-700 dark:text-indigo-300 shadow-xs border border-slate-200 dark:border-slate-700"
                  : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-200/50 dark:hover:bg-slate-850",
              ],
              variant === "underline" && [
                "py-2.5 px-1 border-b-2 -mb-px",
                isSelected
                  ? "border-indigo-600 text-indigo-600 dark:border-indigo-400 dark:text-indigo-400"
                  : "border-transparent text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200",
              ]
            )}
          >
            {item.icon && <span className="flex-shrink-0" aria-hidden="true">{item.icon}</span>}
            <span>{item.label}</span>
            {item.badge && <span className="flex-shrink-0">{item.badge}</span>}
          </button>
        );
      })}
    </div>
  );
};

export const TabPanel: React.FC<{
  id: string;
  activeTab: string;
  children: React.ReactNode;
  className?: string;
}> = ({ id, activeTab, children, className }) => {
  if (activeTab !== id) return null;

  return (
    <div
      role="tabpanel"
      id={`tabpanel-${id}`}
      aria-labelledby={`tab-${id}`}
      tabIndex={0}
      className={cn("focus:outline-none", className)}
    >
      {children}
    </div>
  );
};
