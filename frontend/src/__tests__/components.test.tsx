import { describe, it, expect, vi } from "vitest";
import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { Header } from "../components/Header";
import { Sidebar } from "../components/Sidebar";
import { AuditLogs } from "../components/AuditLogs";
import { PluginManagement } from "../components/PluginManagement";
import { McpConfigModal } from "../components/McpConfigModal";
import { UserGuideModal } from "../components/UserGuideModal";
import { KnowledgeAndRules } from "../components/KnowledgeAndRules";
import { LiveExecutionMonitor } from "../components/LiveExecutionMonitor";
import {
  ExecutionResponse,
  KnowledgeChunkResponse,
  McpConfigResponse,
  PluginProfileResponse,
  RuleResponse,
} from "../types";

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

  it("renders AuditLogs with structured Input and Output views in the Inspect modal", () => {
    const sampleLogs: ExecutionResponse[] = [
      {
        id: "exec_prod_99",
        target_id: "sqlserver_prod",
        query: "SELECT ProductID, Name, Price FROM dbo.Products WHERE ProductID = 101;",
        query_type: "READ",
        reasoning: "Checking server stock for customer inquiry",
        status: "COMPLETED",
        explain_plan: {
          QueryPlan: { RelOp: [{ PhysicalOp: "Clustered Index Seek" }] },
        },
        violations: [],
        execution_time_ms: 48.5,
        auto_approved: true,
        approved_by: "System/Auto",
        result_summary: {
          data: [
            { ProductID: 101, Name: "Server Rack 42U", Price: 1299.99 },
            { ProductID: 102, Name: "Switch 48-Port", Price: 549.50 },
          ],
          rows_affected: 2,
        },
        error_message: null,
        spid: 54,
        created_at: "2026-10-22T08:00:00Z",
        finished_at: "2026-10-22T08:00:01Z",
      },
    ];

    render(<AuditLogs logs={sampleLogs} />);

    // Table view assertions
    expect(screen.getByText("#exec_prod_99")).toBeDefined();
    expect(screen.getByText("2 rows returned")).toBeDefined();
    expect(screen.getByText("Checking server stock for customer inquiry")).toBeDefined();

    // Click Inspect to open modal
    fireEvent.click(screen.getByText("Inspect"));
    expect(screen.getByText("Execution Audit Detail: #exec_prod_99")).toBeDefined();
    expect(screen.getByText("Execution Output & Results")).toBeDefined();
    expect(screen.getByText("Server Rack 42U")).toBeDefined();
    expect(screen.getByText("Switch 48-Port")).toBeDefined();

    // Switch to Input Tab
    fireEvent.click(screen.getByText("Input Statement & Intent"));
    expect(screen.getByText("AI Intent & Purpose Reasoning")).toBeDefined();
    expect(screen.getByText("Full SQL Statement / Command Input")).toBeDefined();

    // Switch to Governance Tab
    fireEvent.click(screen.getByText("Dry-Run & Governance Plan"));
    expect(screen.getByText(/Passed all active governance policies/)).toBeDefined();

    // Close modal
    fireEvent.click(screen.getByText("Close"));
    expect(screen.queryByText("Execution Audit Detail: #exec_prod_99")).toBeNull();
  });

  it("renders Dynamic Plugin UI with custom card and opens Edit Configuration modal", async () => {
    const handleRegister = vi.fn();
    const handleUpdate = vi.fn().mockResolvedValue(undefined);
    const handleSync = vi.fn();

    const samplePlugins: PluginProfileResponse[] = [
      {
        id: "sqlserver_prod",
        name: "SQL Server Enterprise",
        driver: "pyodbc/mssql",
        entrypoint: "python adapter.py",
        dry_run_command: "SET SHOWPLAN_XML ON",
        abort_command: "KILL {spid}",
        config: {
          server: "10.0.0.1",
          port: 1433,
          database: "EnterpriseDB",
          username: "sa",
        },
        ui_schema: [
          {
            key: "server",
            label: "Server Host / Address",
            type: "text",
            default: "localhost",
            required: true,
          },
          {
            key: "port",
            label: "TCP Port",
            type: "number",
            default: 1433,
            required: true,
          },
          {
            key: "password",
            label: "Database Password",
            type: "password",
            required: false,
          },
          {
            key: "auth_mode",
            label: "Authentication Mode",
            type: "select",
            options: ["SQL Auth", "Windows Auth"],
            default: "SQL Auth",
          },
        ],
        custom_card: {
          type: "sqlserver_spid",
          title: "Active SPID & Process Pool",
          badge: "sys.dm_exec_requests",
          columns: ["SPID", "Status", "Login"],
          sample_data: [
            { SPID: 52, Status: "RUNNABLE", Login: "sa" },
            { SPID: 53, Status: "SUSPENDED", Login: "etl_user" },
          ],
        },
        status: "active",
        latency_ms: 12.5,
        active_sessions_count: 2,
        created_at: "2026-10-21T00:00:00Z",
        updated_at: "2026-10-21T00:00:00Z",
      },
    ];

    render(
      <PluginManagement
        plugins={samplePlugins}
        onRegisterPlugin={handleRegister}
        onUpdatePlugin={handleUpdate}
        onSyncPlugin={handleSync}
      />
    );

    // 1. Verify plugin card and dialect-specific custom card rendered
    expect(screen.getByText("SQL Server Enterprise")).toBeDefined();
    expect(screen.getByText("Active SPID & Process Pool")).toBeDefined();
    expect(screen.getByText("sys.dm_exec_requests")).toBeDefined();
    expect(screen.getByText("RUNNABLE")).toBeDefined();

    // 2. Click Edit Configuration button
    const editBtn = screen.getByTestId("edit-btn-sqlserver_prod");
    fireEvent.click(editBtn);

    // 3. Verify Edit Modal opened and rendered dynamic schema fields
    expect(screen.getByTestId("edit-plugin-modal")).toBeDefined();
    expect(screen.getByText("Server Host / Address")).toBeDefined();
    expect(screen.getByText("TCP Port")).toBeDefined();
    expect(screen.getByText("Database Password")).toBeDefined();
    expect(screen.getByText("Authentication Mode")).toBeDefined();

    // 4. Change Host address and submit
    const serverInput = screen.getByDisplayValue("10.0.0.1");
    fireEvent.change(serverInput, { target: { value: "192.168.1.100" } });

    const submitBtn = screen.getByText("Save & Re-Init Connection");
    fireEvent.click(submitBtn);

    expect(handleUpdate).toHaveBeenCalledTimes(1);
    expect(handleUpdate).toHaveBeenCalledWith(
      "sqlserver_prod",
      expect.objectContaining({
        config: expect.objectContaining({
          server: "192.168.1.100",
        }),
      })
    );
  });

  it("renders Uninstall button, opens modal, toggles deletion mode, and calls onUninstallPlugin", () => {
    const handleRegister = vi.fn();
    const handleUpdate = vi.fn();
    const handleSync = vi.fn();
    const handleUninstall = vi.fn();

    const samplePlugins: PluginProfileResponse[] = [
      {
        id: "mongodb_prod",
        name: "MongoDB Enterprise",
        driver: "motor/mongo",
        entrypoint: "python adapter.py",
        dry_run_command: "db.runCommand({explain:...})",
        abort_command: "db.killOp({opid})",
        config: { connection_uri: "mongodb://localhost:27017" },
        status: "active",
        latency_ms: 8.5,
        active_sessions_count: 1,
        created_at: "2026-10-21T00:00:00Z",
        updated_at: "2026-10-21T00:00:00Z",
      },
    ];

    render(
      <PluginManagement
        plugins={samplePlugins}
        onRegisterPlugin={handleRegister}
        onUpdatePlugin={handleUpdate}
        onSyncPlugin={handleSync}
        onUninstallPlugin={handleUninstall}
      />
    );

    // 1. Verify Uninstall button rendered
    const uninstallBtn = screen.getByTestId("uninstall-btn-mongodb_prod");
    expect(uninstallBtn).toBeDefined();

    // 2. Open confirmation modal
    fireEvent.click(uninstallBtn);
    expect(screen.getByText("Uninstall Pluggable Target")).toBeDefined();
    expect(screen.getByText("Soft Deactivate (Recommended)")).toBeDefined();
    expect(screen.getByText("Permanent Hard Delete")).toBeDefined();

    // 3. Select Hard Delete mode
    const hardDeleteOption = screen.getByTestId("mode-hard-delete");
    fireEvent.click(hardDeleteOption);

    // 4. Click Confirm Uninstall
    const confirmBtn = screen.getByTestId("confirm-uninstall-btn");
    fireEvent.click(confirmBtn);

    expect(handleUninstall).toHaveBeenCalledTimes(1);
    expect(handleUninstall).toHaveBeenCalledWith("mongodb_prod", true);
  });

  it("renders Header MCP Config button and triggers modal opener", () => {
    const handleMcpOpen = vi.fn();
    render(
      <Header
        autoMode={false}
        onToggleAutoMode={vi.fn()}
        mcpOnline={true}
        onOpenMcpModal={handleMcpOpen}
      />
    );

    const mcpBtn = screen.getByTestId("header-mcp-btn");
    expect(mcpBtn).toBeDefined();
    fireEvent.click(mcpBtn);
    expect(handleMcpOpen).toHaveBeenCalledTimes(1);
  });

  it("renders McpConfigModal, switches client tabs, and copies JSON snippet", async () => {
    const handleClose = vi.fn();
    const writeTextMock = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, {
      clipboard: {
        writeText: writeTextMock,
      },
    });
    const sampleConfig: McpConfigResponse = {
      server_name: "aegisgate-sqlserver",
      plugin_id: "sqlserver",
      command: "python",
      args: ["-m", "core.gateway.mcp_server", "--plugin", "sqlserver"],
      env: { AEGISGATE_API_URL: "http://localhost:8000" },
      mcpServers: {
        "aegisgate-sqlserver": {
          command: "python",
          args: ["-m", "core.gateway.mcp_server", "--plugin", "sqlserver"],
          env: { AEGISGATE_API_URL: "http://localhost:8000" },
        },
      },
    };

    render(
      <McpConfigModal
        isOpen={true}
        onClose={handleClose}
        configData={sampleConfig}
      />
    );

    // 1. Verify modal title and JSON snippet
    expect(screen.getByTestId("mcp-modal")).toBeDefined();
    expect(screen.getByText("MCP Connection Configuration")).toBeDefined();
    const snippetPre = screen.getByTestId("mcp-json-snippet");
    expect(snippetPre.textContent).toContain("aegisgate-sqlserver");
    expect(snippetPre.textContent).toContain("http://localhost:8000");

    // 2. Click Cursor tab
    fireEvent.click(screen.getByText("Cursor (.cursor/mcp.json)"));
    expect(screen.getByText(".cursor/mcp.json (Project root) or Cursor Settings > Features > MCP")).toBeDefined();

    // 3. Click Copy to Clipboard
    const copyBtn = screen.getByTestId("copy-mcp-btn");
    fireEvent.click(copyBtn);

    await waitFor(() => {
      expect(writeTextMock).toHaveBeenCalled();
      expect(screen.getByText("Copied to Clipboard!")).toBeDefined();
    });
  });

  it("renders KnowledgeAndRules with target filter, displays scoping badges, and creates target-scoped rule", () => {
    const handleSaveDocs = vi.fn();
    const handleCreateRule = vi.fn();
    const handleDeleteRule = vi.fn();

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
        latency_ms: 12.0,
        active_sessions_count: 3,
        created_at: "2026-10-21T00:00:00Z",
        updated_at: "2026-10-21T00:00:00Z",
      },
    ];

    const sampleChunks: KnowledgeChunkResponse[] = [
      {
        id: "chunk_orders",
        target_id: "sqlserver_prod",
        partition_key: "Sales",
        title: "Sales Orders Data",
        catalog: { tables: ["Orders", "Customers"] },
        doc_content: "# Sales Orders Context",
        skills_content: "# Select Orders Query",
        created_at: "2026-10-21T00:00:00Z",
        updated_at: "2026-10-21T00:00:00Z",
      },
    ];

    const sampleRules: RuleResponse[] = [
      {
        id: "rule_global_1",
        name: "Global Limit",
        target_id: null,
        rule_type: "MAX_EXECUTION_TIME",
        expression: "15",
        description: "Enforced across all targets",
        severity: "HIGH",
        is_active: true,
        created_at: "2026-10-21T00:00:00Z",
      },
      {
        id: "rule_sql_1",
        name: "SQL Server No Cross Join",
        target_id: "sqlserver_prod",
        rule_type: "FORBID_JOIN",
        expression: "Orders,AuditLogs",
        description: "Block join for SQL Server",
        severity: "CRITICAL",
        is_active: true,
        created_at: "2026-10-21T00:00:00Z",
      },
    ];

    render(
      <KnowledgeAndRules
        chunks={sampleChunks}
        rules={sampleRules}
        plugins={samplePlugins}
        onSaveDocs={handleSaveDocs}
        onCreateRule={handleCreateRule}
        onDeleteRule={handleDeleteRule}
      />
    );

    // 1. Verify Target Badge on Knowledge Chunk
    const chunkBadge = screen.getByTestId("chunk-target-badge-chunk_orders");
    expect(chunkBadge).toBeDefined();
    expect(chunkBadge.textContent).toContain("Target: SQL Server Enterprise");

    // 2. Switch to Governance Rules sub-tab
    fireEvent.click(screen.getByText(/Governance Rules/i));

    // 3. Verify Scoping Badges on Rules: Global vs Target-Scoped
    const globalBadge = screen.getByTestId("rule-target-badge-rule_global_1");
    expect(globalBadge.textContent).toContain("Global Scope");
    const sqlBadge = screen.getByTestId("rule-target-badge-rule_sql_1");
    expect(sqlBadge.textContent).toContain("Target: SQL Server Enterprise");

    // 4. Test Target Filter Dropdown
    const filterSelect = screen.getByTestId("target-filter-select");
    expect(filterSelect).toBeDefined();

    // Filter by Global Scope Only
    fireEvent.change(filterSelect, { target: { value: "global" } });
    expect(screen.queryByTestId("rule-card-rule_sql_1")).toBeNull();
    expect(screen.getByTestId("rule-card-rule_global_1")).toBeDefined();

    // 5. Open Create Rule Modal and select Target Scope
    fireEvent.click(screen.getByTestId("create-rule-btn"));
    expect(screen.getByTestId("create-rule-target-select")).toBeDefined();

    // Select SQL Server Target Scope
    const targetSelect = screen.getByTestId("create-rule-target-select");
    fireEvent.change(targetSelect, { target: { value: "sqlserver_prod" } });

    // Fill required fields
    fireEvent.change(screen.getByPlaceholderText("e.g. rule_no_cross_join"), {
      target: { value: "rule_sql_custom" },
    });
    fireEvent.change(screen.getByPlaceholderText("e.g. Forbid Orders & AuditLogs Join"), {
      target: { value: "Custom SQL Rule" },
    });

    // Submit rule
    fireEvent.click(screen.getByTestId("submit-create-rule-btn"));

    expect(handleCreateRule).toHaveBeenCalledTimes(1);
    expect(handleCreateRule).toHaveBeenCalledWith(
      expect.objectContaining({
        id: "rule_sql_custom",
        name: "Custom SQL Rule",
        target_id: "sqlserver_prod",
      })
    );
  });

  it("renders Sidebar and triggers User Guide modal callback", () => {
    const handleOpenUserGuide = vi.fn();
    render(
      <Sidebar
        activeTab="monitor"
        onTabChange={vi.fn()}
        plugins={[]}
        onOpenUserGuide={handleOpenUserGuide}
      />
    );

    const guideBtn = screen.getByTestId("sidebar-user-guide-btn");
    expect(guideBtn).toBeDefined();
    fireEvent.click(guideBtn);
    expect(handleOpenUserGuide).toHaveBeenCalledTimes(1);
  });

  it("renders UserGuideModal, switches sections, and copies config snippet", async () => {
    const handleClose = vi.fn();
    const writeTextMock = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, {
      clipboard: {
        writeText: writeTextMock,
      },
    });

    render(<UserGuideModal isOpen={true} onClose={handleClose} />);
    expect(screen.getByText("AegisGate System User Guide")).toBeDefined();
    expect(screen.getByText("1. Zero-Trust Database Gateway Architecture")).toBeDefined();

    // Click section 2: AI Connection via MCP
    fireEvent.click(screen.getByText("2. AI Connection via MCP"));
    expect(screen.getByText("2. Connecting AI Clients via MCP Protocol")).toBeDefined();

    // Click section 3: Pluggable Targets
    fireEvent.click(screen.getByText("3. Pluggable Targets"));
    expect(screen.getByText("3. Managing Pluggable Targets (Database Connectors)")).toBeDefined();

    // Click section 4: Governance Rules & Scope
    fireEvent.click(screen.getByText("4. Governance Rules & Scope"));
    expect(screen.getByText(/4\. Governance Rules & Target Scoping/i)).toBeDefined();

    // Click section 5: Live Monitor & Approvals
    fireEvent.click(screen.getByText("5. Live Monitor & Approvals"));
    expect(screen.getByText(/5\. Live Execution Monitor/i)).toBeDefined();
    expect(screen.getByText("Manual Review Mode (Default)")).toBeDefined();
    expect(screen.getByText("Auto Approval Mode")).toBeDefined();

    // Click section 6: Audit Logs Input / Output
    fireEvent.click(screen.getByText("6. Audit Logs Input / Output"));
    expect(screen.getByText("6. Audit Logs & Detailed Input / Output Inspection")).toBeDefined();

    // Click copy snippet button
    const copyBtns = screen.getAllByRole("button");
    const mcpCopyBtn = copyBtns.find((b) => b.textContent?.includes("Copy Snippet"));
    if (mcpCopyBtn) {
      fireEvent.click(mcpCopyBtn);
      await waitFor(() => {
        expect(writeTextMock).toHaveBeenCalled();
      });
    }

    // Close button
    fireEvent.click(screen.getByTestId("close-user-guide-btn"));
    expect(handleClose).toHaveBeenCalled();
  });

  it("edits an existing governance rule and reassigns target scope", () => {
    const handleUpdateRule = vi.fn();
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
        latency_ms: 12.0,
        active_sessions_count: 3,
        created_at: "2026-10-21T00:00:00Z",
        updated_at: "2026-10-21T00:00:00Z",
      },
      {
        id: "mongodb_prod",
        name: "MongoDB Production",
        driver: "pymongo",
        entrypoint: "python adapter.py",
        dry_run_command: "explain()",
        abort_command: "killOp({opid})",
        config: {},
        status: "active",
        latency_ms: 10.0,
        active_sessions_count: 1,
        created_at: "2026-10-21T00:00:00Z",
        updated_at: "2026-10-21T00:00:00Z",
      },
    ];

    const sampleRules: RuleResponse[] = [
      {
        id: "rule_global_1",
        name: "Global Limit",
        target_id: null,
        rule_type: "MAX_EXECUTION_TIME",
        expression: "15",
        description: "Enforced across all targets",
        severity: "HIGH",
        is_active: true,
        created_at: "2026-10-21T00:00:00Z",
      },
    ];

    render(
      <KnowledgeAndRules
        chunks={[]}
        rules={sampleRules}
        plugins={samplePlugins}
        onSaveDocs={vi.fn()}
        onCreateRule={vi.fn()}
        onUpdateRule={handleUpdateRule}
        onDeleteRule={vi.fn()}
      />
    );

    // Switch to Rules tab
    fireEvent.click(screen.getByText(/Governance Rules/i));

    // Click Edit button
    const editBtn = screen.getByTestId("edit-rule-btn-rule_global_1");
    expect(editBtn).toBeDefined();
    fireEvent.click(editBtn);

    // Verify modal title contains rule ID and input is disabled
    expect(screen.getByText("Edit Governance Rule: #rule_global_1")).toBeDefined();
    const idInput = screen.getByDisplayValue("rule_global_1") as HTMLInputElement;
    expect(idInput.disabled).toBe(true);

    // Change Rule Name
    const nameInput = screen.getByDisplayValue("Global Limit");
    fireEvent.change(nameInput, { target: { value: "Updated Global Limit" } });

    // Change Target Scope to MongoDB
    const targetSelect = screen.getByTestId("create-rule-target-select");
    fireEvent.change(targetSelect, { target: { value: "mongodb_prod" } });

    // Submit
    const submitBtn = screen.getByTestId("submit-create-rule-btn");
    expect(submitBtn.textContent).toContain("Save Rule Changes");
    fireEvent.click(submitBtn);

    expect(handleUpdateRule).toHaveBeenCalledTimes(1);
    expect(handleUpdateRule).toHaveBeenCalledWith("rule_global_1", {
      name: "Updated Global Limit",
      target_id: "mongodb_prod",
      rule_type: "MAX_EXECUTION_TIME",
      severity: "HIGH",
      expression: "15",
      description: "Enforced across all targets",
      is_active: true,
    });
  });

  it("renders LiveExecutionMonitor operational hub with categorized sessions and filters", async () => {
    const handleSelect = vi.fn();
    const handleSubmit = vi.fn();
    const handleApprove = vi.fn().mockResolvedValue(undefined);
    const handleReject = vi.fn().mockResolvedValue(undefined);
    const handleAbort = vi.fn().mockResolvedValue(undefined);

    const sampleExecutions: ExecutionResponse[] = [
      {
        id: "exec_pending_1",
        target_id: "sqlserver_prod",
        query: "SELECT TOP 10 * FROM dbo.Orders;",
        query_type: "READ",
        reasoning: "Checking pending review flow",
        status: "PAUSED_FOR_REVIEW",
        explain_plan: { QueryPlan: { RelOp: [] } },
        violations: [],
        execution_time_ms: null,
        auto_approved: false,
        approved_by: null,
        result_summary: null,
        error_message: null,
        spid: 51,
        created_at: "2026-10-22T10:00:00Z",
        finished_at: null,
      },
      {
        id: "exec_running_1",
        target_id: "mongodb_prod",
        query: "db.inventory.find({ qty: { $gt: 20 } })",
        query_type: "READ",
        reasoning: "Long running inventory aggregation",
        status: "EXECUTING",
        explain_plan: {},
        violations: [],
        execution_time_ms: null,
        auto_approved: true,
        approved_by: "System",
        result_summary: null,
        error_message: null,
        spid: 99,
        created_at: "2026-10-22T10:01:00Z",
        finished_at: null,
      },
      {
        id: "exec_blocked_1",
        target_id: "sqlserver_prod",
        query: "SELECT * FROM Orders CROSS JOIN AuditLogs",
        query_type: "READ",
        reasoning: "Malicious cross join attempt",
        status: "REJECTED",
        explain_plan: {},
        violations: ["Rule Violation: FORBID_JOIN Orders,AuditLogs"],
        execution_time_ms: null,
        auto_approved: false,
        approved_by: null,
        result_summary: null,
        error_message: "Policy Violation: Cross Join forbidden",
        spid: null,
        created_at: "2026-10-22T10:02:00Z",
        finished_at: "2026-10-22T10:02:01Z",
      },
      {
        id: "exec_completed_1",
        target_id: "sqlserver_prod",
        query: "SELECT OrderID FROM dbo.Orders WHERE OrderID = 100;",
        query_type: "READ",
        reasoning: "Normal query",
        status: "COMPLETED",
        explain_plan: {},
        violations: [],
        execution_time_ms: 18.5,
        auto_approved: true,
        approved_by: "System",
        result_summary: { count: 1 },
        error_message: null,
        spid: 52,
        created_at: "2026-10-22T10:03:00Z",
        finished_at: "2026-10-22T10:03:01Z",
      },
    ];

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
        latency_ms: 12.0,
        active_sessions_count: 2,
        created_at: "2026-10-21T00:00:00Z",
        updated_at: "2026-10-21T00:00:00Z",
      },
    ];

    const { rerender } = render(
      <LiveExecutionMonitor
        executions={sampleExecutions}
        selectedExecution={sampleExecutions[0]}
        onSelectExecution={handleSelect}
        onSubmitQuery={handleSubmit}
        onApprove={handleApprove}
        onReject={handleReject}
        onAbort={handleAbort}
        plugins={samplePlugins}
      />
    );

    // 1. Verify Header and Total Count
    expect(screen.getByText("Live Operational Sessions")).toBeDefined();
    expect(screen.getByText("(4 total)")).toBeDefined();

    // 2. Verify State Category Filter Badges
    const filterAllBtn = screen.getByTestId("filter-all-btn");
    const filterPendingBtn = screen.getByTestId("filter-pending-btn");
    const filterRunningBtn = screen.getByTestId("filter-running-btn");
    const filterBlockedBtn = screen.getByTestId("filter-blocked-btn");
    const filterCompletedBtn = screen.getByTestId("filter-completed-btn");

    expect(filterAllBtn).toBeDefined();
    expect(filterPendingBtn.textContent).toContain("Pending Review");
    expect(filterRunningBtn.textContent).toContain("Running");
    expect(filterBlockedBtn.textContent).toContain("Blocked / Failed");
    expect(filterCompletedBtn.textContent).toContain("Completed");

    // 3. Test Filter: Clicking 'Pending Review' shows only pending sessions
    fireEvent.click(filterPendingBtn);
    expect(screen.getByTestId("session-pill-exec_pending_1")).toBeDefined();
    expect(screen.queryByTestId("session-pill-exec_running_1")).toBeNull();
    expect(screen.queryByTestId("session-pill-exec_blocked_1")).toBeNull();
    expect(screen.queryByTestId("session-pill-exec_completed_1")).toBeNull();

    // 4. Test Filter: Clicking 'Running' shows only running sessions
    fireEvent.click(filterRunningBtn);
    expect(screen.getByTestId("session-pill-exec_running_1")).toBeDefined();
    expect(screen.queryByTestId("session-pill-exec_pending_1")).toBeNull();

    // 5. Switch back to 'All' and select a session
    fireEvent.click(filterAllBtn);
    const sessionCard = screen.getByTestId("session-pill-exec_running_1");
    fireEvent.click(sessionCard);
    expect(handleSelect).toHaveBeenCalledWith(sampleExecutions[1]);

    // 6. Test Approve action button on Pending session
    rerender(
      <LiveExecutionMonitor
        executions={sampleExecutions}
        selectedExecution={sampleExecutions[0]}
        onSelectExecution={handleSelect}
        onSubmitQuery={handleSubmit}
        onApprove={handleApprove}
        onReject={handleReject}
        onAbort={handleAbort}
        plugins={samplePlugins}
      />
    );
    const approveBtn = screen.getByText("Approve & Run");
    fireEvent.click(approveBtn);
    await waitFor(() => {
      expect(handleApprove).toHaveBeenCalledWith("exec_pending_1");
    });

    // 7. Test Abort action button on Running session
    rerender(
      <LiveExecutionMonitor
        executions={sampleExecutions}
        selectedExecution={sampleExecutions[1]}
        onSelectExecution={handleSelect}
        onSubmitQuery={handleSubmit}
        onApprove={handleApprove}
        onReject={handleReject}
        onAbort={handleAbort}
        plugins={samplePlugins}
      />
    );
    const stopBtn = screen.getByText("Stop & KILL Session Now");
    fireEvent.click(stopBtn);
    await waitFor(() => {
      expect(handleAbort).toHaveBeenCalledWith("exec_running_1");
    });
  });

  it("renders PluginManagement with 3-tab Add Modal (Preset, ZIP, Git) and verifies certification inspection", async () => {
    const handleRegister = vi.fn();
    const handleInstallZip = vi.fn();
    const handleInstallGit = vi.fn();
    const handleVerify = vi.fn().mockResolvedValue({
      plugin_id: "sqlserver_certified",
      certified: true,
      badge: "CERTIFIED_READY",
      checks: {
        handshake: { status: "PASSED", latency_ms: 5.2 },
        sync_knowledge: { status: "PASSED", latency_ms: 12.0 },
        dry_run: { status: "PASSED", latency_ms: 15.1 },
        abort: { status: "PASSED", latency_ms: 3.0 },
      },
      verified_at: "2026-10-22T22:00:00Z",
    });

    const samplePlugins: PluginProfileResponse[] = [
      {
        id: "sqlserver_certified",
        name: "SQL Server Enterprise",
        driver: "pyodbc/mssql",
        entrypoint: "python adapter.py",
        dry_run_command: "SET SHOWPLAN_XML ON",
        abort_command: "KILL {spid}",
        config: { server: "localhost" },
        status: "active",
        latency_ms: 10.0,
        active_sessions_count: 1,
        is_certified: true,
        certification_report: {
          plugin_id: "sqlserver_certified",
          certified: true,
          badge: "CERTIFIED_READY",
          checks: {
            handshake: { status: "PASSED", latency_ms: 5.2, details: "OK" },
            sync_knowledge: { status: "PASSED", latency_ms: 12.0, details: "2 tables" },
            dry_run: { status: "PASSED", latency_ms: 15.1, details: "Plan OK" },
            abort: { status: "PASSED", latency_ms: 3.0, details: "Kill OK" },
          },
          verified_at: "2026-10-22T22:00:00Z",
        },
        created_at: "2026-10-22T00:00:00Z",
        updated_at: "2026-10-22T00:00:00Z",
      },
    ];

    render(
      <PluginManagement
        plugins={samplePlugins}
        onRegisterPlugin={handleRegister}
        onInstallZip={handleInstallZip}
        onInstallGit={handleInstallGit}
        onVerifyPlugin={handleVerify}
        onSyncPlugin={vi.fn()}
      />
    );

    // 1. Verify Certified Badge is displayed
    const certBadge = screen.getByTestId("cert-badge-sqlserver_certified");
    expect(certBadge).toBeDefined();
    expect(certBadge.textContent).toContain("Certified & Ready");

    // 2. Click Badge to open Certification Inspection Modal
    fireEvent.click(certBadge);
    expect(screen.getByTestId("cert-inspect-modal")).toBeDefined();
    expect(screen.getByText("Plugin Sanity & Certification Report")).toBeDefined();
    expect(screen.getByText("1. Handshake & RPC Ping")).toBeDefined();
    expect(screen.getByText("2. Sync Knowledge Schema")).toBeDefined();
    expect(screen.getByText("3. Dry-Run Analysis")).toBeDefined();
    expect(screen.getByText("4. Abort Hook Protocol")).toBeDefined();

    // Close Modal
    fireEvent.click(screen.getByText("Close Report"));
    expect(screen.queryByTestId("cert-inspect-modal")).toBeNull();

    // 3. Click Sanity Check button
    const sanityBtn = screen.getByTestId("sanity-check-btn-sqlserver_certified");
    fireEvent.click(sanityBtn);
    await waitFor(() => {
      expect(handleVerify).toHaveBeenCalledWith("sqlserver_certified");
    });

    // 4. Open Add Pluggable Target Modal and switch tabs
    fireEvent.click(screen.getByText("Add Pluggable Target"));
    expect(screen.getByText("Register New Pluggable Target")).toBeDefined();

    // Switch to Upload ZIP tab
    const tabZip = screen.getByTestId("tab-add-zip");
    fireEvent.click(tabZip);
    expect(screen.getByText("Choose ZIP file")).toBeDefined();
    expect(screen.getByTestId("upload-zip-btn")).toBeDefined();

    // Switch to Clone Git tab
    const tabGit = screen.getByTestId("tab-add-git");
    fireEvent.click(tabGit);
    expect(screen.getByTestId("input-git-url")).toBeDefined();
    expect(screen.getByTestId("clone-git-btn")).toBeDefined();

    // Switch back to Preset tab
    const tabPreset = screen.getByTestId("tab-add-preset");
    fireEvent.click(tabPreset);
    expect(screen.getByText("Target Architecture Preset")).toBeDefined();
  });

});
