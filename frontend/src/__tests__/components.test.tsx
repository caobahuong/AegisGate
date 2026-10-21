import { describe, it, expect, vi } from "vitest";
import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { Header } from "../components/Header";
import { Sidebar } from "../components/Sidebar";
import { AuditLogs } from "../components/AuditLogs";
import { ExecutionResponse, PluginProfileResponse } from "../types";

describe("Frontend Component Tests", () => {
  it("renders Header with Auto Mode state and triggers toggle", () => {
    const handleToggle = vi.fn();
    const { rerender } = render(
      <Header autoMode={false} onToggleAutoMode={handleToggle} mcpOnline={true} />
    );

    expect(screen.getByText("AEGISGATE")).toBeDefined();
    expect(screen.getByText("OFF (Manual Review)")).toBeDefined();

    const toggleBtn = screen.getByTitle("Toggle Auto Approval Mode");
    fireEvent.click(toggleBtn);
    expect(handleToggle).toHaveBeenCalledTimes(1);

    // Rerender with Auto Mode ON
    rerender(<Header autoMode={true} onToggleAutoMode={handleToggle} mcpOnline={true} />);
    expect(screen.getByText("ON")).toBeDefined();
  });

  it("renders Sidebar and switches tabs", () => {
    const handleTabChange = vi.fn();
    const samplePlugins: PluginProfileResponse[] = [
      {
        id: "sqlserver_prod",
        name: "SQL Server Enterprise",
        driver: "pyodbc/mssql",
        entrypoint: "python adapter.py",
        dry_run_command: "SET SHOWPLAN_XML ON",
        abort_command: "KILL {spid}",
        config: {},
        status: "active",
        latency_ms: 15.2,
        active_sessions_count: 2,
        created_at: "2026-10-21T00:00:00Z",
        updated_at: "2026-10-21T00:00:00Z",
      },
    ];

    render(
      <Sidebar
        activeTab="monitor"
        onTabChange={handleTabChange}
        plugins={samplePlugins}
      />
    );

    expect(screen.getByText("Live Execution Monitor")).toBeDefined();
    expect(screen.getByText("Pluggable Targets")).toBeDefined();
    expect(screen.getByText("SQL Server Enterprise")).toBeDefined();

    fireEvent.click(screen.getByText("Audit Logs"));
    expect(handleTabChange).toHaveBeenCalledWith("logs");
  });

  it("renders AuditLogs table and filters by query term", () => {
    const sampleLogs: ExecutionResponse[] = [
      {
        id: "exec_1001",
        target_id: "sqlserver_prod",
        query: "SELECT * FROM Orders",
        query_type: "READ",
        reasoning: "Test fetch",
        status: "COMPLETED",
        explain_plan: {},
        violations: [],
        execution_time_ms: 45.0,
        auto_approved: true,
        approved_by: "System",
        result_summary: { count: 10 },
        error_message: null,
        spid: 55,
        created_at: "2026-10-21T10:00:00Z",
        finished_at: "2026-10-21T10:00:01Z",
      },
      {
        id: "exec_1002",
        target_id: "sqlserver_prod",
        query: "INSERT INTO Products (Name) VALUES ('Widget')",
        query_type: "WRITE",
        reasoning: "Insert item",
        status: "REJECTED",
        explain_plan: {},
        violations: ["Rule Violation: Write forbidden"],
        execution_time_ms: null,
        auto_approved: false,
        approved_by: null,
        result_summary: null,
        error_message: "Write forbidden",
        spid: null,
        created_at: "2026-10-21T11:00:00Z",
        finished_at: "2026-10-21T11:00:01Z",
      },
    ];

    render(<AuditLogs logs={sampleLogs} />);

    expect(screen.getByText("#exec_1001")).toBeDefined();
    expect(screen.getByText("#exec_1002")).toBeDefined();

    // Search filter
    const searchInput = screen.getByPlaceholderText("Search by ID or query...");
    fireEvent.change(searchInput, { target: { value: "Widget" } });

    expect(screen.queryByText("#exec_1001")).toBeNull();
    expect(screen.getByText("#exec_1002")).toBeDefined();
  });
});

