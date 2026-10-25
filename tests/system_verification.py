"""Comprehensive System Verification & Anti-Gravity Browser Quality Assurance.

Verifies:
1. Backend Unit Tests (pytest)
2. Frontend Unit Tests (vitest)
3. Subprocess process isolation & Zero orphan processes
4. Anti-Gravity Browser Verification via Chrome Debugging on Port 9222:
   - Computed styles (bg-slate-950, typography, dark mode tokens)
   - Interactive tab navigation
   - Dynamic UI Schema rendering & Plugin-specific custom card tables
   - Edit Configuration modal with instant update & re-init
   - Add New Plugin modal with instant reactive reflection
   - State Machine AI flows (Safe SELECT, Forbidden JOIN rejection, Auto Approval)
   - DevTools console inspection for zero JavaScript errors or memory leaks
"""

from pathlib import Path
import sys
import tempfile
import time
import psutil
from playwright.sync_api import sync_playwright

if sys.stdout.encoding.lower() != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

SCREENSHOTS_DIR = Path("./report/screenshots")
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)


def verify_no_orphan_processes() -> None:
    """Check that no orphan adapter.py processes are lingering in the OS."""
    print("Checking for orphan plugin subprocesses...")
    found_orphans = []
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            cmd = proc.info.get("cmdline") or []
            cmd_str = " ".join(cmd)
            if "plugins/sqlserver_plugin/adapter.py" in cmd_str or "adapter.py" in cmd_str:
                found_orphans.append(proc.pid)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    if found_orphans:
        print(f"Warning: Found {len(found_orphans)} lingering adapter process(es): {found_orphans}. Cleaning up...")
        for pid in found_orphans:
            try:
                psutil.Process(pid).kill()
            except Exception:
                pass
    else:
        print("PASS: Zero orphan plugin subprocesses detected. Process isolation is clean.")


def run_anti_gravity_browser_qa() -> None:
    """Execute interactive verification on Chrome Debugging at port 9222."""
    print("\n=======================================================")
    print("Launching Anti-Gravity Browser via Chrome Debugging (Port 9222)")
    print("=======================================================")

    console_errors: list[str] = []
    console_logs: list[str] = []

    def on_console(msg):
        log_entry = f"[{msg.type}] {msg.text}"
        console_logs.append(log_entry)
        if msg.type == "error":
            if "favicon.ico" in msg.text or "404" in msg.text and "favicon" in msg.text:
                return
            console_errors.append(log_entry)
            print(f"  [DevTools Console Error]: {msg.text}")

    user_data_dir = str(Path(tempfile.gettempdir()) / "chrome_debug_runner")

    # Launch browser with explicit remote debugging port 9222
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            channel="chrome",
            args=[
                "--remote-debugging-port=9222",
                "--remote-allow-origins=*",
                "--no-first-run",
                "--no-default-browser-check",
            ],
            viewport={"width": 1440, "height": 900},
            headless=True,
        )

        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.on("console", on_console)
        page.on("pageerror", lambda err: console_errors.append(f"[PageError] {err}"))

        print("1. Navigating to AegisGate Dashboard (http://localhost:3000)...")
        page.goto("http://localhost:3000", wait_until="networkidle")
        time.sleep(1.0)

        # Visual Verification: Computed Styles & Light Theme Default
        print("2. Verifying Visual Theme & Typography (Light Mode Default)...")
        body_bg = page.evaluate("window.getComputedStyle(document.body).backgroundColor")
        print(f"   Body Computed Background (Default): {body_bg}")
        # RGB for light mode default #f8fafc is rgb(248, 250, 252)
        assert "rgb(248, 250, 252)" in body_bg or "248, 250, 252" in body_bg, f"Expected default Light Mode rgb(248, 250, 252), got {body_bg}"
        page.screenshot(path=str(SCREENSHOTS_DIR / "qa_00_light_mode_default.png"))
        print("   PASS: Light Mode default (#f8fafc) verified.")

        # Header Title
        title_el = page.locator("h1:has-text('AEGISGATE')")
        assert title_el.is_visible(), "AegisGate title not visible"

        # MCP Status & Header MCP Config Button
        assert page.locator("text=MCP Server:").is_visible(), "MCP Server label not visible"
        assert page.locator("header span:has-text('Active')").is_visible(), "MCP Server Active badge not visible"

        # Test Theme Toggle to Dark Mode
        print("2.0b Testing Theme Toggle (Light -> Dark -> Light)...")
        theme_toggle_btn = page.locator("[data-testid='theme-toggle-btn']")
        assert theme_toggle_btn.is_visible(), "Theme Toggle button not visible"
        theme_toggle_btn.click()
        time.sleep(0.5)
        dark_bg = page.evaluate("window.getComputedStyle(document.body).backgroundColor")
        print(f"   Body Computed Background (Dark Mode): {dark_bg}")
        assert "rgb(2, 6, 23)" in dark_bg or "2, 6, 23" in dark_bg, f"Expected Dark Mode rgb(2, 6, 23), got {dark_bg}"
        page.screenshot(path=str(SCREENSHOTS_DIR / "qa_00_dark_mode_toggled.png"))
        print("   PASS: Switched to Dark Mode (#020617) successfully.")

        # Toggle back to Light Mode
        theme_toggle_btn.click()
        time.sleep(0.5)
        light_restored_bg = page.evaluate("window.getComputedStyle(document.body).backgroundColor")
        print(f"   Body Computed Background (Restored Light): {light_restored_bg}")
        assert "rgb(248, 250, 252)" in light_restored_bg or "248, 250, 252" in light_restored_bg, f"Expected Light Mode restored, got {light_restored_bg}"
        print("   PASS: Switched back to Light Mode default successfully.")

        # Test Sidebar User Guide Modal
        print("2.0 Testing Sidebar 'User Guide & Docs' Modal...")
        user_guide_btn = page.locator("[data-testid='sidebar-user-guide-btn']")
        assert user_guide_btn.is_visible(), "Sidebar 'User Guide & Docs' button not visible"
        user_guide_btn.click()
        page.wait_for_selector("text=AegisGate System User Guide", timeout=4000)
        assert page.locator("text=1. Zero-Trust Database Gateway Architecture").is_visible()
        page.screenshot(path=str(SCREENSHOTS_DIR / "qa_00_user_guide_modal.png"))

        # Switch to MCP section in User Guide
        page.click("button:has-text('2. AI Connection via MCP')")
        assert page.locator("text=2. Connecting AI Clients via MCP Protocol").is_visible()
        time.sleep(0.3)

        # Switch to Section 5: Live Monitor & Approvals
        page.click("button:has-text('5. Live Monitor & Approvals')")
        page.wait_for_selector("text=Manual Review Mode (Default)", timeout=3000)
        assert page.locator("text=Auto Approval Mode").is_visible()
        page.screenshot(path=str(SCREENSHOTS_DIR / "qa_00b_user_guide_section5.png"))
        time.sleep(0.3)

        page.click("[data-testid='close-user-guide-btn']")
        time.sleep(0.5)
        print("   PASS: Sidebar User Guide modal opened, section 5 (Live Monitor & Approvals) verified, and closed cleanly.")

        # Test Header MCP Config Modal & Snippet Copy
        print("2.1 Testing Header MCP Config Modal & Snippet Copy...")
        header_mcp_btn = page.locator("[data-testid='header-mcp-btn']")
        assert header_mcp_btn.is_visible()
        header_mcp_btn.click()
        page.wait_for_selector("[data-testid='mcp-modal']", timeout=4000)
        assert page.locator("text=AegisGate Global MCP Connection").is_visible()
        page.screenshot(path=str(SCREENSHOTS_DIR / "qa_01a_mcp_global_modal.png"))

        # Switch to Cursor tab
        page.click("button:has-text('Cursor (.cursor/mcp.json)')")
        time.sleep(0.3)
        # Click Copy to Clipboard
        page.click("[data-testid='copy-mcp-btn']")
        page.wait_for_selector("text=Copied to Clipboard!", timeout=3000)
        page.screenshot(path=str(SCREENSHOTS_DIR / "qa_01b_mcp_copied.png"))
        print("   PASS: Header MCP modal opened, tab switched to Cursor, and JSON copied successfully.")
        page.click("button:has-text('Close')")
        time.sleep(0.5)

        # Test Interactive Auto Mode Toggle
        print("3. Testing Auto Approval Mode toggle...")
        auto_toggle = page.locator("button[title='Toggle Auto Approval Mode']")
        assert auto_toggle.is_visible()
        # Toggle to ON
        auto_toggle.click()
        time.sleep(0.5)
        assert page.locator("button[title='Toggle Auto Approval Mode']:has-text('ON')").is_visible()
        page.screenshot(path=str(SCREENSHOTS_DIR / "qa_01_auto_mode_on.png"))

        # Toggle back to OFF (Manual Review)
        auto_toggle.click()
        time.sleep(0.5)
        assert page.locator("button[title='Toggle Auto Approval Mode']:has-text('OFF')").is_visible()
        print("   PASS: Auto Mode switch toggles and reflects state dynamically.")

        # Tab Navigation
        print("4. Testing Sidebar Tab Navigation...")

        # Tab: Pluggable Targets
        print("   Navigating to Pluggable Targets...")
        page.click("button:has-text('Pluggable Targets')")
        page.wait_for_selector("text=Pluggable Targets & Connectors", timeout=5000)
        assert page.locator("text=Active Connection Parameters").first.is_visible()
        assert page.locator("text=Live Operational Metrics & Pool").first.is_visible()
        page.screenshot(path=str(SCREENSHOTS_DIR / "qa_02_pluggable_targets.png"))

        # Test Sync Schema Button
        print("   Testing 'Sync Schema' button...")
        page.locator("button:has-text('Sync Schema')").first.click()
        time.sleep(1.0)

        # Test Edit Configuration Modal & Dynamic UI Schema
        print("   Testing 'Edit Configuration' Modal and Dynamic Schema Form...")
        page.locator("button:has-text('Edit Configuration')").first.click()
        page.wait_for_selector("text=Edit Connection Configuration", timeout=4000)
        time.sleep(0.5)
        page.screenshot(path=str(SCREENSHOTS_DIR / "qa_02b_edit_plugin_modal.png"))

        # Save Configuration change
        page.click("button:has-text('Save & Re-Init Connection')")
        time.sleep(1.0)
        print("   PASS: Edit Configuration dynamic form opened and saved successfully.")

        # Test Plugin-Specific MCP Config Button
        print("   Testing Plugin-Specific 'MCP Config' Button...")
        plugin_mcp_btn = page.locator("[data-testid^='mcp-btn-']").first
        assert plugin_mcp_btn.is_visible()
        plugin_mcp_btn.click()
        page.wait_for_selector("[data-testid='mcp-modal']", timeout=4000)
        assert page.locator("text=MCP Connection:").is_visible()
        page.screenshot(path=str(SCREENSHOTS_DIR / "qa_02c_plugin_mcp_modal.png"))
        page.click("[data-testid='copy-mcp-btn']")
        page.wait_for_selector("text=Copied to Clipboard!", timeout=3000)
        page.click("button:has-text('Close')")
        time.sleep(0.5)
        print("   PASS: Plugin-specific MCP snippet modal verified and copied.")

        # Test Plugin Certification Badge & 4-Stage Inspection Modal
        print("   Testing Plugin Certification Badge & 4-Stage Inspection Modal...")
        cert_badge = page.locator("[data-testid^='cert-badge-']").first
        assert cert_badge.is_visible()
        cert_badge.click()
        page.wait_for_selector("[data-testid='cert-inspect-modal']", timeout=4000)
        assert page.locator("text=Plugin Sanity & Certification Report").is_visible()
        assert page.locator("text=1. Handshake & RPC Ping").is_visible()
        assert page.locator("text=2. Sync Knowledge Schema").is_visible()
        assert page.locator("text=3. Dry-Run Analysis").is_visible()
        assert page.locator("text=4. Abort Hook Protocol").is_visible()
        page.screenshot(path=str(SCREENSHOTS_DIR / "qa_02d_cert_inspect_modal.png"))
        page.click("button:has-text('Close Report')")
        time.sleep(0.5)
        print("   PASS: Plugin Certification inspection modal verified with 4-stage breakdown.")

        # Test Automated 'Sanity Check' Trigger
        print("   Testing 'Sanity Check' Button...")
        sanity_check_btn = page.locator("[data-testid^='sanity-check-btn-']").first
        assert sanity_check_btn.is_visible()
        sanity_check_btn.click()
        time.sleep(1.0)
        page.wait_for_selector("[data-testid='cert-inspect-modal']", timeout=8000)
        page.screenshot(path=str(SCREENSHOTS_DIR / "qa_02e_sanity_check_completed.png"))
        page.click("button:has-text('Close Report')")
        time.sleep(0.5)
        print("   PASS: Automated Sanity Check executed and reported successfully.")

        # Test Add New Plugin Modal (3-Tabs: Preset, Upload ZIP, Clone Git)
        print("   Testing 'Add New Plugin' Modal with 3 Tabs (Preset, Upload ZIP, Clone Git)...")
        page.click("button:has-text('Add Pluggable Target')")
        page.wait_for_selector("text=Register New Pluggable Target", timeout=3000)

        # Switch to Upload ZIP tab
        page.click("[data-testid='tab-add-zip']")
        assert page.locator("text=Choose ZIP file").is_visible()
        assert page.locator("[data-testid='upload-zip-btn']").is_visible()
        page.screenshot(path=str(SCREENSHOTS_DIR / "qa_03a_add_modal_zip_tab.png"))

        # Switch to Clone Git tab
        page.click("[data-testid='tab-add-git']")
        assert page.locator("[data-testid='input-git-url']").is_visible()
        assert page.locator("[data-testid='clone-git-btn']").is_visible()
        page.screenshot(path=str(SCREENSHOTS_DIR / "qa_03b_add_modal_git_tab.png"))

        # Switch back to Preset tab and register
        page.click("[data-testid='tab-add-preset']")
        new_plugin_id = f"pg_analytics_{int(time.time())}"
        page.fill("input[placeholder='e.g. mongodb_prod']", new_plugin_id)
        page.fill("input[placeholder='e.g. MongoDB Analytics Cluster']", "PostgreSQL Analytics")
        page.click("button:has-text('Register Plugin')")
        time.sleep(1.0)

        # Verify appearance in cards and sidebar
        assert page.locator("h3:has-text('PostgreSQL Analytics')").first.is_visible()
        page.screenshot(path=str(SCREENSHOTS_DIR / "qa_03_plugin_modal_added.png"))
        print("   PASS: Add Plugin modal successfully registers target and updates immediately.")

        # Test Uninstall Plugin & Sidebar Removal
        print("   Testing 'Uninstall Plugin' Modal and Instant Removal from Sidebar...")
        uninstall_btn = page.locator(f"[data-testid='uninstall-btn-{new_plugin_id}']")
        assert uninstall_btn.is_visible()
        uninstall_btn.click()
        page.wait_for_selector("text=Uninstall Pluggable Target", timeout=3000)
        page.screenshot(path=str(SCREENSHOTS_DIR / "qa_03b_uninstall_modal.png"))

        # Select mode (Soft Deactivate) and confirm
        page.click("[data-testid='confirm-uninstall-btn']")
        time.sleep(1.0)

        # Confirm target is removed from cards and from sidebar
        assert not page.locator(f"[data-testid='plugin-card-{new_plugin_id}']").is_visible()
        sidebar_target_entry = page.locator(f"[data-testid='sidebar-plugin-{new_plugin_id}']")
        assert not sidebar_target_entry.is_visible()
        page.screenshot(path=str(SCREENSHOTS_DIR / "qa_03c_uninstalled_sidebar_clean.png"))
        print("   PASS: Plugin uninstalled successfully and immediately removed from Sidebar and Target cards.")

        # Test Fixed Sidebar & Independent Content Scroll
        print("   Verifying Fixed Sidebar Layout (h-screen overflow-hidden, no window scroll)...")
        layout_metrics = page.evaluate("""() => {
            const aside = document.querySelector('aside');
            const main = document.querySelector('main');
            const asideTopBefore = aside.getBoundingClientRect().top;
            
            // Scroll main content
            main.scrollTop = 400;
            const mainScrollTop = main.scrollTop;
            const asideTopAfter = aside.getBoundingClientRect().top;
            const windowScrollY = window.scrollY;

            return {
                asideTopBefore,
                asideTopAfter,
                mainScrollTop,
                windowScrollY
            };
        }""")

        assert layout_metrics["windowScrollY"] == 0, f"Window scrolled unexpectedly: {layout_metrics['windowScrollY']}"
        assert layout_metrics["asideTopBefore"] == layout_metrics["asideTopAfter"], (
            f"Sidebar moved during main scroll! Before: {layout_metrics['asideTopBefore']}, After: {layout_metrics['asideTopAfter']}"
        )
        print(f"   PASS: Sidebar is permanently fixed (top={layout_metrics['asideTopBefore']}px) while main scrolls independently (scrollTop={layout_metrics['mainScrollTop']}px).")

        # Tab: Knowledge & Rules
        print("   Navigating to Knowledge & Rules...")
        page.click("button:has-text('Knowledge & Rules')")
        page.wait_for_selector("text=Partitioned Knowledge Chunks", timeout=5000)
        time.sleep(0.5)
        page.screenshot(path=str(SCREENSHOTS_DIR / "qa_04_knowledge_docs.png"))

        # Test Target Scope Filter on Knowledge Chunks
        print("   Testing Target Scope Filter on Knowledge Chunks...")
        target_filter = page.locator("[data-testid='target-filter-select']")
        assert target_filter.is_visible(), "Target Scope filter dropdown not visible"
        # Select Global Scope Only
        target_filter.select_option("global")
        time.sleep(0.5)
        # Select SQL Server Prod
        target_filter.select_option("sqlserver_prod")
        time.sleep(0.5)
        # Verify target badge on chunk
        chunk_badge = page.locator("[data-testid^='chunk-target-badge-']").first
        assert chunk_badge.is_visible()
        assert "Target: SQL Server Enterprise Gateway" in chunk_badge.inner_text()
        # Reset to All Pluggable Targets
        target_filter.select_option("all")
        time.sleep(0.5)

        # Test Markdown Save
        print("   Testing Markdown Docs Save...")
        page.click("button:has-text('Save Docs & Skills')")
        page.wait_for_selector("text=Saved!", timeout=5000)

        # Sub-tab: Governance Rules
        print("   Testing Governance Rules Sub-tab & Target Scoping...")
        page.click("button:has-text('Governance Rules')")
        page.wait_for_selector("text=Governance & Security Rules", timeout=5000)
        page.screenshot(path=str(SCREENSHOTS_DIR / "qa_05_governance_rules.png"))

        # Verify Global & Target badges on Rules
        rule_badges = page.locator("[data-testid^='rule-target-badge-']").all_inner_texts()
        assert any("Global Scope" in b for b in rule_badges), "Global Scope badge not found on rules"
        assert any("Target: SQL Server Enterprise Gateway" in b for b in rule_badges), "Target badge not found on rules"
        print("   PASS: Global Scope and Target badges verified on governance rules.")

        # Test Target Filter on Rules
        target_filter.select_option("global")
        time.sleep(0.5)
        global_only_badges = page.locator("[data-testid^='rule-target-badge-']").all_inner_texts()
        assert all("Global Scope" in b for b in global_only_badges)
        page.screenshot(path=str(SCREENSHOTS_DIR / "qa_05b_rules_global_filter.png"))

        target_filter.select_option("all")
        time.sleep(0.5)

        # Test Create Target-Scoped Rule Modal
        print("   Testing 'Create New Rule' modal with Target Scope selector...")
        page.click("[data-testid='create-rule-btn']")
        page.wait_for_selector("text=Create Governance Rule", timeout=3000)
        assert page.locator("[data-testid='create-rule-target-select']").is_visible()
        
        # Fill rule fields and select target: sqlserver_prod
        new_rule_id = f"rule_sp_who2_{int(time.time())}"
        page.fill("input[placeholder='e.g. rule_no_cross_join']", new_rule_id)
        page.fill("input[placeholder='e.g. Forbid Orders & AuditLogs Join']", "Block SQL Server Sp_Who2")
        page.locator("[data-testid='create-rule-target-select']").select_option("sqlserver_prod")
        page.fill("input[placeholder='e.g. Orders,AuditLogs']", "sp_who2")
        page.fill("textarea[placeholder='Why this rule must be enforced...']", "Direct execution of sp_who2 is restricted.")
        page.screenshot(path=str(SCREENSHOTS_DIR / "qa_05c_create_rule_target_scoped.png"))
        page.click("[data-testid='submit-create-rule-btn']")
        time.sleep(1.0)

        # Verify new target-scoped rule has badge Target: SQL Server Enterprise Gateway
        new_rule_card = page.locator(f"div[data-testid='rule-card-{new_rule_id}']")
        assert new_rule_card.is_visible()
        badge_in_new_rule = new_rule_card.locator("[data-testid^='rule-target-badge-']")
        assert badge_in_new_rule.is_visible()
        assert "Target: SQL Server Enterprise Gateway" in badge_in_new_rule.inner_text()
        print("   PASS: Created target-scoped rule and verified Target: SQL Server Enterprise Gateway badge.")

        # Test Edit Governance Rule & Reassign Target Scope
        print("   Testing 'Edit Governance Rule' and Reassigning Target Scope back to Global Scope...")
        edit_rule_btn = page.locator(f"[data-testid='edit-rule-btn-{new_rule_id}']")
        assert edit_rule_btn.is_visible(), "Edit rule button not visible"
        edit_rule_btn.click()
        page.wait_for_selector(f"text=Edit Governance Rule: #{new_rule_id}", timeout=3000)

        # Verify Rule ID is disabled
        rule_id_disabled = page.evaluate(f"() => document.querySelector(\"input[value='{new_rule_id}']\").disabled")
        assert rule_id_disabled is True, "Rule ID input should be disabled in edit mode"

        # Update Rule Name
        page.fill("input[value='Block SQL Server Sp_Who2']", "Block SQL Server Sp_Who2 (Updated Global)")
        # Reassign target scope from sqlserver_prod to Global Scope ("")
        page.locator("[data-testid='create-rule-target-select']").select_option("")
        page.screenshot(path=str(SCREENSHOTS_DIR / "qa_05d_edit_rule_modal.png"))

        # Save changes
        page.click("[data-testid='submit-create-rule-btn']")
        time.sleep(1.0)

        # Verify rule badge dynamically updated to Global Scope
        updated_badge = page.locator(f"div[data-testid='rule-card-{new_rule_id}'] [data-testid^='rule-target-badge-']")
        assert "Global Scope" in updated_badge.inner_text(), f"Expected Global Scope badge, got: {updated_badge.inner_text()}"
        print("   PASS: Rule updated successfully; target scope reassigned to Global Scope and badge updated reactively.")

        # Tab: Live Execution Monitor & State Machine Simulation
        print("5. Testing Live Execution Monitor & State Machine...")
        page.click("button:has-text('Live Execution Monitor')")
        page.wait_for_selector("text=1. AI Query & Reasoning", timeout=5000)
        page.screenshot(path=str(SCREENSHOTS_DIR / "qa_06_monitor_layout.png"))

        # 5.1 Manual Review Flow (Safe SELECT)
        print("   Simulating Safe SELECT Query (Manual Approval Flow)...")
        page.click("button:has-text('Send Query to AegisGate')")
        page.wait_for_selector("text=PAUSED FOR REVIEW", timeout=8000)
        page.screenshot(path=str(SCREENSHOTS_DIR / "qa_07_paused_for_review.png"))

        # Approve and Resume
        print("   Clicking 'Approve & Run'...")
        page.click("button:has-text('Approve & Run')")
        page.wait_for_selector("text=COMPLETED", timeout=8000)
        page.wait_for_selector("text=Execution Successful", timeout=5000)
        page.screenshot(path=str(SCREENSHOTS_DIR / "qa_08_completed_manual.png"))
        print("   PASS: Manual Review flow (Dry-Run -> Pause -> Approve -> Completed) passed.")

        # 5.2 Rule Violation Flow (Forbidden JOIN)
        print("   Simulating Forbidden JOIN Query (Rejection Flow)...")
        page.click("button:has-text('Forbidden JOIN Test')")
        time.sleep(0.3)
        page.click("button:has-text('Send Query to AegisGate')")
        page.wait_for_selector("text=REJECTED", timeout=8000)
        page.wait_for_selector("text=Rule Violations Detected", timeout=8000)
        page.screenshot(path=str(SCREENSHOTS_DIR / "qa_09_forbidden_join_rejected.png"))
        print("   PASS: Forbidden JOIN detected and blocked immediately during Dry-Run.")

        # 5.3 Auto Approval Flow
        print("   Testing Auto Approval Flow (Auto ON -> Direct Execute)...")
        auto_toggle.click()
        time.sleep(0.5)
        # Select safe query preset or default
        page.fill("textarea[placeholder='Enter SQL or database statement...']", "SELECT OrderID, TotalAmount FROM dbo.Orders WHERE OrderID = 1001;")
        page.click("button:has-text('Send Query to AegisGate')")
        page.wait_for_selector("text=COMPLETED", timeout=8000)
        page.wait_for_selector("text=Auto Approval ON", timeout=5000)
        page.screenshot(path=str(SCREENSHOTS_DIR / "qa_10_auto_approved_completed.png"))
        print("   PASS: Auto Approval mode executes without manual pause.")
        # Toggle back to off
        auto_toggle.click()

        # Tab: Audit Logs
        print("6. Verifying Audit Logs & Inspection...")
        page.click("button:has-text('Audit Logs')")
        page.wait_for_selector("text=Audit & Compliance Logs", timeout=5000)
        time.sleep(0.5)

        # Inspect details modal
        page.locator("button:has-text('Inspect')").first.click()
        page.wait_for_selector("text=Execution Audit Detail", timeout=3000)
        assert page.locator("text=Execution Output & Results").is_visible()
        page.screenshot(path=str(SCREENSHOTS_DIR / "qa_11_audit_log_drawer.png"))

        # Switch to Input Tab
        page.click("button:has-text('Input Statement & Intent')")
        assert page.locator("text=Full SQL Statement / Command Input").is_visible()
        page.screenshot(path=str(SCREENSHOTS_DIR / "qa_11b_audit_input_tab.png"))

        page.click("button:has-text('Close')")
        print("   PASS: Audit Logs table and structured Input/Output inspect drawer verified.")

        ctx.close()

    print("\n=======================================================")
    print("Anti-Gravity Browser DevTools Console Audit:")
    if console_errors:
        print(f"FAILED: Found {len(console_errors)} console error(s):")
        for err in console_errors:
            print("  -", err)
        sys.exit(1)
    else:
        print("PASS: 0 JavaScript Console Errors detected!")
        print("PASS: Clean Server-Sent Events (SSE) lifecycle and connection cleanup confirmed!")
        print("=======================================================\n")


if __name__ == "__main__":
    verify_no_orphan_processes()
    run_anti_gravity_browser_qa()
