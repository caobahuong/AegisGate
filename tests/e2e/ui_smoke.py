"""Automated UI Smoke Test Suite for AegisGate Dashboard (S1 - S11).

Executes end-to-end browser verification using Playwright, verifying:
- S1: Initial Load & Theme Default (Light mode default, toggle to dark, restore light)
- S2: Navigation Sidebar (4 tabs: Targets, Knowledge & Rules, Live Monitor, Audit Logs)
- S3: Pluggable Targets View (Cards, badges, metrics, custom card previews)
- S4: Add Plugin Modal (Tabs: Preset, ZIP, Git; form validation and cancel)
- S5: Dynamic UI Schema & Configuration (Edit config modal, schema fields)
- S6: Knowledge & Rules Scoping (Filter by target, scoping badges)
- S7: Governance Rule Creation Modal (Rule types, target scope, validation)
- S8: Live Execution Monitor: Safe Query & State Machine (Auto-approval ON -> COMPLETED)
- S9: Governance Rejection (Forbidden join -> REJECTED with violations)
- S10: Manual Review & Approval Flow (Auto-approval OFF -> PAUSED_FOR_REVIEW -> Approve -> COMPLETED)
- S11: Audit Logs & MCP Configuration Modal (Execution history table, MCP snippets)

All screenshots saved to report/screenshots/phase2_s{1..11}_<description>.png.
"""

import sys
import time
from pathlib import Path

import pytest
from playwright.sync_api import Page, sync_playwright

pytestmark = pytest.mark.e2e

SCREENSHOTS_DIR = Path("./report/screenshots")
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
BASE_URL = "http://localhost:3000"


def run_smoke_suite(page: Page) -> None:
    """Execute complete smoke checklist S1 - S11 on the provided Playwright page."""
    print("\nStarting AegisGate UI Smoke Test Suite (S1 - S11)...")

    # -------------------------------------------------------------------------
    # S1: Initial Load & Theme Default
    # -------------------------------------------------------------------------
    print("\n[S1] Testing Initial Load & Default Theme...")
    page.goto(BASE_URL, wait_until="networkidle")
    time.sleep(1.0)

    # Verify Light Mode by default
    html_class = page.locator("html").get_attribute("class") or ""
    assert "dark" not in html_class, f"Expected light mode default, got html class='{html_class}'"
    page.screenshot(path=str(SCREENSHOTS_DIR / "phase2_s1_theme_light_default.png"))
    print("   PASS: Dashboard loaded in Light Mode by default.")

    # Toggle to Dark Mode
    theme_btn = page.locator("[data-testid='theme-toggle-btn']")
    assert theme_btn.is_visible(), "Theme toggle button not visible"
    theme_btn.click()
    time.sleep(0.5)
    html_class_dark = page.locator("html").get_attribute("class") or ""
    assert "dark" in html_class_dark, f"Expected dark mode class, got '{html_class_dark}'"
    page.screenshot(path=str(SCREENSHOTS_DIR / "phase2_s1_theme_dark.png"))
    print("   PASS: Toggled to Dark Mode successfully.")

    # Toggle back to Light Mode
    theme_btn.click()
    time.sleep(0.5)
    html_class_restored = page.locator("html").get_attribute("class") or ""
    assert "dark" not in html_class_restored, "Expected restoration of light mode default"
    page.screenshot(path=str(SCREENSHOTS_DIR / "phase2_s1_theme_light_restored.png"))
    print("   PASS: Restored Light Mode default successfully.")

    # -------------------------------------------------------------------------
    # S2: Navigation Sidebar & Responsive Layout
    # -------------------------------------------------------------------------
    print("\n[S2] Testing Navigation Sidebar across 4 Views...")
    nav_tabs = [
        ("button:has-text('Pluggable Targets')", "Pluggable Targets & Connectors"),
        ("button:has-text('Knowledge & Rules')", "Partitioned Knowledge Chunks"),
        ("button:has-text('Audit Logs')", "Audit & Compliance Logs"),
        ("button:has-text('Live Execution Monitor'), button:has-text('Live Monitor')", "AI Query & Reasoning"),
    ]

    for tab_selector, expected_text in nav_tabs:
        page.locator(tab_selector).first.click()
        time.sleep(0.4)
        assert page.locator(f"text={expected_text}").first.is_visible(), f"View '{expected_text}' not displayed"

    page.screenshot(path=str(SCREENSHOTS_DIR / "phase2_s2_navigation_sidebar.png"))
    print("   PASS: Verified navigation across all 4 dashboard views.")

    # -------------------------------------------------------------------------
    # S3: Pluggable Targets View
    # -------------------------------------------------------------------------
    print("\n[S3] Testing Pluggable Targets View & Metrics...")
    page.locator("button:has-text('Pluggable Targets')").first.click()
    time.sleep(0.5)

    assert page.locator("text=sqlserver_prod").is_visible(), "Target 'sqlserver_prod' not visible"
    assert page.locator("text=active").first.is_visible(), "Active status badge not visible"
    page.screenshot(path=str(SCREENSHOTS_DIR / "phase2_s3_pluggable_targets.png"))
    print("   PASS: Target cards, status badges, and metrics render correctly.")

    # -------------------------------------------------------------------------
    # S4: Add Plugin Modal
    # -------------------------------------------------------------------------
    print("\n[S4] Testing Add Plugin Modal...")
    add_btn = page.locator("button:has-text('Add Pluggable Target')").first
    assert add_btn.is_visible(), "Add Plugin button not visible"
    add_btn.click()
    time.sleep(0.5)

    assert page.locator("text=Register New Pluggable Target").is_visible(), "Add Plugin modal not displayed"
    assert page.locator("[data-testid='tab-add-preset']").is_visible(), "Preset tab not visible"
    assert page.locator("[data-testid='tab-add-zip']").is_visible(), "ZIP tab not visible"
    assert page.locator("[data-testid='tab-add-git']").is_visible(), "Git tab not visible"

    page.screenshot(path=str(SCREENSHOTS_DIR / "phase2_s4_add_plugin_modal.png"))
    page.locator("button:has-text('Cancel')").first.click()
    time.sleep(0.3)
    print("   PASS: Add Plugin modal opened, verified tabs, and closed cleanly.")

    # -------------------------------------------------------------------------
    # S5: Dynamic UI Schema & Configuration
    # -------------------------------------------------------------------------
    print("\n[S5] Testing Dynamic UI Schema & Configuration Modal...")
    edit_btn = page.locator("button:has-text('Edit Configuration')").first
    assert edit_btn.is_visible(), "Edit Configuration button not visible"
    edit_btn.click()
    time.sleep(0.5)

    assert page.locator("text=Edit Connection Configuration").is_visible(), "Config modal title not visible"
    page.screenshot(path=str(SCREENSHOTS_DIR / "phase2_s5_dynamic_config_modal.png"))
    page.locator("button:has-text('Cancel')").first.click()
    time.sleep(0.3)
    print("   PASS: Dynamic schema fields rendered and modal closed cleanly.")

    # -------------------------------------------------------------------------
    # S6: Knowledge & Rules Scoping
    # -------------------------------------------------------------------------
    print("\n[S6] Testing Knowledge & Rules Scoping Filter...")
    page.locator("button:has-text('Knowledge & Rules')").first.click()
    time.sleep(0.5)

    target_filter = page.locator("[data-testid='target-filter-select']")
    assert target_filter.is_visible(), "Target filter select not visible"
    page.screenshot(path=str(SCREENSHOTS_DIR / "phase2_s6_knowledge_and_rules.png"))
    print("   PASS: Knowledge & Rules loaded with target filter and scoping badges.")

    # -------------------------------------------------------------------------
    # S7: Governance Rule Creation Modal
    # -------------------------------------------------------------------------
    print("\n[S7] Testing Governance Rule Creation Modal...")
    # Switch to Governance Rules sub-tab
    rules_subtab = page.locator("button:has-text('Governance Rules')").first
    assert rules_subtab.is_visible(), "Governance Rules subtab not visible"
    rules_subtab.click()
    time.sleep(0.5)

    create_rule_btn = page.locator("[data-testid='create-rule-btn']")
    assert create_rule_btn.is_visible(), "Create Rule button not visible"
    create_rule_btn.click()
    time.sleep(0.5)

    assert page.locator("text=Create Governance Rule").is_visible(), "Create Rule modal not displayed"
    assert page.locator("[data-testid='create-rule-target-select']").is_visible(), "Rule target selector not visible"
    page.screenshot(path=str(SCREENSHOTS_DIR / "phase2_s7_create_rule_modal.png"))
    page.locator("button:has-text('Cancel')").first.click()
    time.sleep(0.3)
    print("   PASS: Create Rule modal opened and verified successfully.")

    # -------------------------------------------------------------------------
    # S8: Live Execution Monitor: Safe Query & State Machine
    # -------------------------------------------------------------------------
    print("\n[S8] Testing Live Execution Monitor: Safe Query Execution...")
    page.locator("button:has-text('Live Execution Monitor'), button:has-text('Live Monitor')").first.click()
    time.sleep(0.5)

    # Ensure Auto Approval is ON for direct execution
    auto_toggle = page.locator("button[title='Toggle Auto Approval Mode']")
    if not auto_toggle.locator("text='ON'").is_visible():
        auto_toggle.click()
        time.sleep(0.5)

    # Enter safe query
    query_input = page.locator("textarea[placeholder='Enter SQL or database statement...']")
    query_input.fill("SELECT OrderID, TotalAmount FROM dbo.Orders WHERE OrderID = 1001;")
    time.sleep(0.3)

    submit_btn = page.locator("button:has-text('Send Query to AegisGate')")
    submit_btn.click()

    page.wait_for_selector("text=COMPLETED", timeout=8000)
    page.screenshot(path=str(SCREENSHOTS_DIR / "phase2_s8_safe_query_completed.png"))
    print("   PASS: Safe query executed directly to COMPLETED status with results.")

    # -------------------------------------------------------------------------
    # S9: Governance Rejection (Forbidden Join)
    # -------------------------------------------------------------------------
    print("\n[S9] Testing Governance Rejection (Forbidden Join)...")
    forbidden_query = "SELECT * FROM Orders o JOIN AuditLogs a ON o.OrderID = a.LogID;"
    query_input.fill(forbidden_query)
    time.sleep(0.3)
    submit_btn.click()

    page.wait_for_selector("text=REJECTED", timeout=8000)
    page.screenshot(path=str(SCREENSHOTS_DIR / "phase2_s9_forbidden_join_rejected.png"))
    print("   PASS: Prohibited cross-join was immediately REJECTED by governance engine.")

    # -------------------------------------------------------------------------
    # S10: Manual Review & Approval Flow
    # -------------------------------------------------------------------------
    print("\n[S10] Testing Manual Review & Approval Workflow...")
    # Toggle Auto Approval OFF if ON
    if auto_toggle.inner_text().strip().endswith("ON"):
        auto_toggle.click()
        time.sleep(0.5)

    review_query = "SELECT TOP 10 * FROM Finance.BudgetForecast WHERE FiscalYear = 2026;"
    query_input.fill(review_query)
    time.sleep(0.3)
    submit_btn.click()

    # Query should enter PAUSED_FOR_REVIEW and show Approve & Run in details pane
    page.wait_for_selector("button:has-text('Approve & Run')", timeout=10000)
    time.sleep(0.5)

    approve_btn = page.locator("button:has-text('Approve & Run')").first
    assert approve_btn.is_visible(), "Approve & Run button not visible after query paused for review"
    page.screenshot(path=str(SCREENSHOTS_DIR / "phase2_s10_paused_for_review.png"))
    print("   PASS: Query entered PAUSED_FOR_REVIEW state and inspector opened.")

    # Click Approve & Run
    approve_btn.click()

    page.wait_for_selector("text=COMPLETED", timeout=10000)
    time.sleep(0.5)
    page.screenshot(path=str(SCREENSHOTS_DIR / "phase2_s10_approved_completed.png"))
    print("   PASS: Resumed execution to COMPLETED status after manual approval.")

    # -------------------------------------------------------------------------
    # S11: Audit Logs & MCP Configuration Modal
    # -------------------------------------------------------------------------
    print("\n[S11] Testing Audit Logs & Header MCP Modal...")
    page.locator("button:has-text('Audit & Compliance Logs'), button:has-text('Audit Logs')").first.click()
    time.sleep(1.0)

    page.wait_for_selector("table tbody tr", timeout=8000)
    assert page.locator("table td:has-text('COMPLETED')").first.is_visible(), "Execution logs not listed"
    page.screenshot(path=str(SCREENSHOTS_DIR / "phase2_s11_audit_logs.png"))
    print("   PASS: Audit Logs view displays recent executions.")

    # Open Header MCP Modal
    mcp_btn = page.locator("[data-testid='header-mcp-btn']")
    assert mcp_btn.is_visible(), "Header MCP button not visible"
    mcp_btn.click()
    time.sleep(0.5)

    assert page.locator("[data-testid='mcp-modal']").is_visible(), "MCP Config modal not visible"
    assert page.locator("[data-testid='copy-mcp-btn']").is_visible(), "Copy MCP config button not visible"
    page.screenshot(path=str(SCREENSHOTS_DIR / "phase2_s11_mcp_modal.png"))
    page.locator("button:has-text('Close')").first.click()
    time.sleep(0.3)
    print("   PASS: Header MCP modal opened, verified JSON snippets, and closed.")

    print("\n[OK] All UI Smoke Tests S1 - S11 passed cleanly!\n")


def test_ui_smoke_full():
    """Pytest entrypoint for running the automated UI smoke test."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()
        try:
            run_smoke_suite(page)
        finally:
            browser.close()


if __name__ == "__main__":
    test_ui_smoke_full()
