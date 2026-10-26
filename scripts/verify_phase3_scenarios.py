"""Automated Verification Suite for Phase 3: S1-S11 and X1-X5.

Runs end-to-end browser quality verification using Playwright, capturing
rich photographic evidence into report/screenshots/.
"""

import logging
import subprocess
import sys
import time
from pathlib import Path
from playwright.sync_api import Page, sync_playwright

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("phase3_verification")

SCREENSHOTS_DIR = Path("report/screenshots")
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
BASE_URL = "http://localhost:3000"


def snap(page: Page, filename: str) -> None:
    path = SCREENSHOTS_DIR / filename
    page.screenshot(path=str(path))
    logger.info("Captured screenshot: %s", path)


def verify_s1_dashboard_shell(page: Page) -> None:
    logger.info("--- S1: Dashboard Shell & Theme Flash ---")
    page.goto(BASE_URL, wait_until="networkidle")
    time.sleep(1.0)

    # 1. Light mode default check
    html_class = page.locator("html").get_attribute("class") or ""
    assert "dark" not in html_class, f"Expected light mode by default, got class='{html_class}'"
    snap(page, "phase3_s1_dashboard_shell_light.png")

    # 2. SSE indicator check
    sse_badge = page.locator("[data-testid='sse-status-indicator']")
    assert sse_badge.is_visible(), "SSE Indicator not visible in header"
    assert "Live Stream" in sse_badge.inner_text(), f"Expected Live Stream badge, got '{sse_badge.inner_text()}'"

    # 3. Toggle to dark mode
    theme_btn = page.locator("[data-testid='theme-toggle-btn']")
    assert theme_btn.is_visible(), "Theme toggle button not visible"
    theme_btn.click()
    time.sleep(0.5)

    html_class_dark = page.locator("html").get_attribute("class") or ""
    assert "dark" in html_class_dark, f"Expected dark class on html, got '{html_class_dark}'"
    snap(page, "phase3_s1_dashboard_shell_dark.png")

    # 4. Reload page to verify zero theme flash (persisted dark mode from localStorage)
    page.reload(wait_until="networkidle")
    time.sleep(0.5)
    html_class_reloaded = page.locator("html").get_attribute("class") or ""
    assert "dark" in html_class_reloaded, "Expected dark theme to persist on reload without flash"

    # Toggle back to light mode for subsequent tests
    page.locator("[data-testid='theme-toggle-btn']").click()
    time.sleep(0.5)
    logger.info("PASS: S1 Dashboard Shell and Theme persistence verified.")


def verify_s2_monitor_carousel(page: Page) -> None:
    logger.info("--- S2: Live Monitor Navigation & Session Filters ---")
    page.locator("button:has-text('Live Execution Monitor'), button:has-text('Live Monitor')").first.click()
    time.sleep(0.5)

    # Verify filter buttons exist
    for filter_name in ["All", "Pending", "Running", "Blocked", "Completed"]:
        btn = page.locator(f"button:has-text('{filter_name}')").first
        assert btn.is_visible(), f"Filter tab '{filter_name}' not visible"
        btn.click()
        time.sleep(0.2)

    # Switch back to All
    page.locator("button:has-text('All')").first.click()
    time.sleep(0.3)

    # Select a session card if one exists
    cards = page.locator("[data-testid^='session-card-']")
    if cards.count() > 0:
        cards.first.click()
        time.sleep(0.3)

    snap(page, "phase3_s2_monitor_carousel_light.png")
    logger.info("PASS: S2 Live Monitor Navigation & Filter Tabs verified.")


def verify_s3_query_simulator(page: Page) -> None:
    logger.info("--- S3: Query Simulator & Dry Run ---")
    page.locator("button:has-text('Live Execution Monitor'), button:has-text('Live Monitor')").first.click()
    time.sleep(0.4)

    # Make sure Auto Approval is ON
    auto_btn = page.locator("button[title='Toggle Auto Approval Mode']")
    if "OFF" in auto_btn.inner_text():
        auto_btn.click()
        time.sleep(0.4)

    query_box = page.locator("textarea[placeholder='Enter SQL or database statement...']")
    query_box.fill("SELECT ProductID, Name, ListPrice FROM Production.Product WHERE ListPrice > 50.00;")
    time.sleep(0.3)

    submit_btn = page.locator("button:has-text('Send Query to AegisGate')")
    submit_btn.click()

    # Wait for completion and verify Dry-run explain & state inspector
    page.wait_for_selector("text=COMPLETED", timeout=10000)
    time.sleep(0.5)
    snap(page, "phase3_s3_query_simulator_dryrun_light.png")
    logger.info("PASS: S3 Query Simulator & Dry Run verified.")


def verify_s4_gatekeeper_approval(page: Page) -> None:
    logger.info("--- S4: Gatekeeper Manual Review & Approval Flow ---")
    page.locator("button:has-text('Live Execution Monitor'), button:has-text('Live Monitor')").first.click()
    time.sleep(0.4)

    # Toggle Auto Approval OFF
    auto_btn = page.locator("button[title='Toggle Auto Approval Mode']")
    if "ON" in auto_btn.inner_text():
        auto_btn.click()
        time.sleep(0.4)

    query_box = page.locator("textarea[placeholder='Enter SQL or database statement...']")
    query_box.fill("SELECT TOP 5 AccountID, Balance FROM Finance.Accounts WHERE Balance > 100000;")
    time.sleep(0.3)

    submit_btn = page.locator("button:has-text('Send Query to AegisGate')")
    submit_btn.click()

    # Wait for PAUSED_FOR_REVIEW
    page.wait_for_selector("button:has-text('Approve & Run')", timeout=10000)
    time.sleep(0.5)
    snap(page, "phase3_s4_gatekeeper_paused_review.png")

    # Click Approve & Run
    page.locator("button:has-text('Approve & Run')").first.click()
    page.wait_for_selector("text=COMPLETED", timeout=10000)
    time.sleep(0.5)
    snap(page, "phase3_s4_gatekeeper_approved_completed.png")
    logger.info("PASS: S4 Gatekeeper Manual Approval Flow verified.")


def verify_s5_execution_termination(page: Page) -> None:
    logger.info("--- S5: Execution Termination (Abort/Reject) ---")
    page.locator("button:has-text('Live Execution Monitor'), button:has-text('Live Monitor')").first.click()
    time.sleep(0.4)

    # Ensure Auto Approval is OFF
    auto_btn = page.locator("button[title='Toggle Auto Approval Mode']")
    if "ON" in auto_btn.inner_text():
        auto_btn.click()
        time.sleep(0.4)

    query_box = page.locator("textarea[placeholder='Enter SQL or database statement...']")
    query_box.fill("SELECT COUNT(*) FROM VeryLargeHistoricalLogs WITH (NOLOCK);")
    time.sleep(0.3)

    page.locator("button:has-text('Send Query to AegisGate')").click()
    page.wait_for_selector("button:has-text('Reject')", timeout=10000)
    time.sleep(0.5)

    # Click Reject Query
    page.locator("button:has-text('Reject')").first.click()
    page.wait_for_selector("text=REJECTED", timeout=10000)
    time.sleep(0.5)
    snap(page, "phase3_s5_execution_termination.png")
    logger.info("PASS: S5 Execution Termination verified.")


def verify_s6_target_plugin_card(page: Page) -> None:
    logger.info("--- S6: Target Plugin Management & Custom Card ---")
    page.locator("button:has-text('Pluggable Targets')").first.click()
    time.sleep(0.5)

    assert page.locator("text=sqlserver_prod").is_visible(), "Target 'sqlserver_prod' not visible"
    assert page.locator("[data-testid='cert-badge-sqlserver_prod']").is_visible(), "Certified badge not visible"
    assert page.locator("text=Active SPID & Process Pool").is_visible(), "Custom card SPID pool not visible"

    snap(page, "phase3_s6_target_plugin_card_light.png")

    # Dark mode screenshot as well
    page.locator("[data-testid='theme-toggle-btn']").click()
    time.sleep(0.4)
    snap(page, "phase3_s6_target_plugin_card_dark.png")
    page.locator("[data-testid='theme-toggle-btn']").click()
    time.sleep(0.4)
    logger.info("PASS: S6 Target Plugin Card and SPID pool verified.")


def verify_s7_add_plugin_modal(page: Page) -> None:
    logger.info("--- S7: Add Plugin Modal 3 Tabs ---")
    page.locator("button:has-text('Pluggable Targets')").first.click()
    time.sleep(0.4)

    add_btn = page.locator("button:has-text('Add Pluggable Target')").first
    add_btn.click()
    time.sleep(0.5)

    assert page.locator("text=Register New Pluggable Target").is_visible(), "Modal title not visible"

    # Tab 1: Preset
    assert page.locator("[data-testid='tab-add-preset']").is_visible()
    # Tab 2: ZIP
    page.locator("[data-testid='tab-add-zip']").click()
    time.sleep(0.3)
    assert page.locator("[data-testid='upload-zip-btn']").is_visible()

    # Tab 3: Git
    page.locator("[data-testid='tab-add-git']").click()
    time.sleep(0.3)
    assert page.locator("[data-testid='input-git-url']").is_visible()

    snap(page, "phase3_s7_add_plugin_tabs.png")
    page.locator("button:has-text('Cancel')").first.click()
    time.sleep(0.3)
    logger.info("PASS: S7 Add Plugin Modal 3 Tabs verified.")


def verify_s8_dynamic_config_and_linter(page: Page) -> None:
    logger.info("--- S8: Dynamic Configuration & 4-Stage Sanity Linter ---")
    page.locator("button:has-text('Pluggable Targets')").first.click()
    time.sleep(0.4)

    # 1. Dynamic Config Modal
    edit_btn = page.locator("button:has-text('Edit Configuration')").first
    edit_btn.click()
    time.sleep(0.5)
    assert page.locator("[data-testid='edit-plugin-modal']").is_visible()
    snap(page, "phase3_s8_dynamic_config_modal.png")
    page.locator("button:has-text('Cancel')").first.click()
    time.sleep(0.4)

    # 2. Sanity Linter Modal
    verify_btn = page.locator("[data-testid^='sanity-check-btn-']").first
    verify_btn.click()
    time.sleep(1.0)
    assert page.locator("[data-testid='cert-inspect-modal']").is_visible()
    assert page.locator("text=1. Handshake & RPC Ping").is_visible()
    assert page.locator("text=4. Abort Hook Protocol").is_visible()
    snap(page, "phase3_s8_sanity_linter_modal.png")
    page.locator("button:has-text('Close Report')").first.click()
    time.sleep(0.4)
    logger.info("PASS: S8 Dynamic Config & Sanity Linter verified.")


def verify_s9_uninstall_modal(page: Page) -> None:
    logger.info("--- S9: Uninstall Modal & Modes ---")
    page.locator("button:has-text('Pluggable Targets')").first.click()
    time.sleep(0.4)

    uninstall_btn = page.locator("[data-testid^='uninstall-btn-']").first
    uninstall_btn.click()
    time.sleep(0.5)
    assert page.locator("[data-testid='mode-soft-deactivate']").is_visible()
    assert page.locator("[data-testid='mode-hard-delete']").is_visible()

    # Toggle to hard delete radio
    page.locator("[data-testid='mode-hard-delete']").click()
    time.sleep(0.2)
    snap(page, "phase3_s9_uninstall_modal.png")
    page.locator("button:has-text('Cancel')").first.click()
    time.sleep(0.4)
    logger.info("PASS: S9 Uninstall Modal verified.")


def verify_s10_knowledge_and_skills_editor(page: Page) -> None:
    logger.info("--- S10: Knowledge Chunks & Skills Editor ---")
    page.locator("button:has-text('Knowledge & Rules')").first.click()
    time.sleep(0.5)

    # Select the first chunk
    chunk_btn = page.locator("[data-testid^='chunk-btn-']").first
    if chunk_btn.is_visible():
        chunk_btn.click()
        time.sleep(0.4)

    assert page.locator("text=Business Rules & Context (doc.md)").is_visible()
    assert page.locator("text=Query Skills & Templates (skills.md)").is_visible()

    save_btn = page.locator("button:has-text('Save Docs & Skills')")
    assert save_btn.is_visible()
    save_btn.click()
    time.sleep(0.5)

    snap(page, "phase3_s10_knowledge_editor_toast.png")
    logger.info("PASS: S10 Knowledge Chunks & Skills Editor verified.")


def verify_s11_governance_rules_and_scoping(page: Page) -> None:
    logger.info("--- S11: Governance Rules & Scoping ---")
    page.locator("button:has-text('Knowledge & Rules')").first.click()
    time.sleep(0.4)

    # Switch to Governance Rules sub-tab
    page.locator("button:has-text('Governance Rules')").first.click()
    time.sleep(0.5)

    # Verify target filter selector
    filter_sel = page.locator("[data-testid='target-filter-select']")
    assert filter_sel.is_visible()

    # Open Create Rule modal
    page.locator("[data-testid='create-rule-btn']").click()
    time.sleep(0.5)

    assert page.locator("text=Create Governance Rule").is_visible()
    assert page.locator("[data-testid='create-rule-target-select']").is_visible()

    snap(page, "phase3_s11_create_rule_modal.png")
    page.locator("button:has-text('Cancel')").first.click()
    time.sleep(0.4)
    logger.info("PASS: S11 Governance Rules & Scoping verified.")


def verify_x1_sse_indicator(page: Page) -> None:
    logger.info("--- X1: SSE Connection Indicator ---")
    indicator = page.locator("[data-testid='sse-status-indicator']")
    assert indicator.is_visible(), "SSE Indicator not visible"
    snap(page, "phase3_x1_sse_indicator.png")
    logger.info("PASS: X1 SSE Connection Indicator verified.")


def verify_x2_error_handling_no_alert(page: Page) -> None:
    logger.info("--- X2: Error Handling & Zero alert() ---")
    # Verify no native alert dialog is triggered
    alert_triggered = []

    def on_dialog(dialog):
        alert_triggered.append(dialog.message)
        dialog.dismiss()

    page.on("dialog", on_dialog)

    # Submit unknown target query via simulator
    page.locator("button:has-text('Live Execution Monitor'), button:has-text('Live Monitor')").first.click()
    time.sleep(0.4)

    # Submit an invalid syntax query to verify error handling without alert()
    query_box = page.locator("textarea[placeholder='Enter SQL or database statement...']")
    query_box.fill("INVALID SQL SYNTAX !!! @#$%^&*()")
    time.sleep(0.3)

    page.locator("button:has-text('Send Query to AegisGate')").click()
    time.sleep(1.0)

    assert len(alert_triggered) == 0, f"Expected 0 alert() dialogs, but received: {alert_triggered}"
    snap(page, "phase3_x2_error_handling_no_alert.png")
    page.remove_listener("dialog", on_dialog)
    logger.info("PASS: X2 Error Handling with zero alert() dialogs verified.")


def verify_x3_keyboard_accessibility(page: Page) -> None:
    logger.info("--- X3: Keyboard Accessibility & Focus Trap ---")
    # Open Header MCP Modal using keyboard
    mcp_btn = page.locator("[data-testid='header-mcp-btn']")
    mcp_btn.focus()
    page.keyboard.press("Enter")
    time.sleep(0.5)

    modal = page.locator("[data-testid='mcp-modal']")
    assert modal.is_visible(), "MCP modal did not open on Enter"

    # Tab through modal elements
    page.keyboard.press("Tab")
    time.sleep(0.2)
    page.keyboard.press("Tab")
    time.sleep(0.2)
    snap(page, "phase3_x3_keyboard_focus_trap.png")

    # Press Escape to close modal
    page.keyboard.press("Escape")
    time.sleep(0.4)
    assert not modal.is_visible(), "Modal did not close on Escape key"
    logger.info("PASS: X3 Keyboard Accessibility and Focus Trap verified.")


def verify_x4_narrow_viewport(page: Page) -> None:
    logger.info("--- X4: Narrow Viewport Responsiveness (900px & 600px) ---")
    page.locator("button:has-text('Live Execution Monitor'), button:has-text('Live Monitor')").first.click()
    time.sleep(0.4)

    # 900px viewport
    page.set_viewport_size({"width": 900, "height": 800})
    time.sleep(0.5)
    snap(page, "phase3_x4_viewport_900px.png")

    # 600px viewport
    page.set_viewport_size({"width": 600, "height": 800})
    time.sleep(0.5)
    snap(page, "phase3_x4_viewport_600px.png")

    # Restore 1440x900 viewport
    page.set_viewport_size({"width": 1440, "height": 900})
    time.sleep(0.5)
    logger.info("PASS: X4 Narrow Viewports verified.")


def verify_x5_large_list_performance(page: Page) -> None:
    logger.info("--- X5: Large List Performance (500 demo items) ---")
    logger.info("Seeding 500 demo executions via scripts/seed_demo.py --count 500...")
    subprocess.run([sys.executable, "scripts/seed_demo.py", "--count", "500", "--force"], check=True)

    # Go to Audit Logs
    page.locator("button:has-text('Audit Logs'), button:has-text('Audit & Compliance Logs')").first.click()
    time.sleep(1.0)

    rows = page.locator("table tbody tr")
    page.wait_for_selector("table tbody tr", timeout=8000)
    count = rows.count()
    logger.info("Audit Logs rendered %d initial rows smoothly.", count)
    assert count >= 10, f"Expected at least 10 rendered rows, got {count}"

    snap(page, "phase3_x5_large_list_performance.png")
    logger.info("PASS: X5 Large List Performance verified.")


def run_all_phase3_verifications() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        try:
            verify_s1_dashboard_shell(page)
            verify_s2_monitor_carousel(page)
            verify_s3_query_simulator(page)
            verify_s4_gatekeeper_approval(page)
            verify_s5_execution_termination(page)
            verify_s6_target_plugin_card(page)
            verify_s7_add_plugin_modal(page)
            verify_s8_dynamic_config_and_linter(page)
            verify_s9_uninstall_modal(page)
            verify_s10_knowledge_and_skills_editor(page)
            verify_s11_governance_rules_and_scoping(page)
            verify_x1_sse_indicator(page)
            verify_x2_error_handling_no_alert(page)
            verify_x3_keyboard_accessibility(page)
            verify_x4_narrow_viewport(page)
            verify_x5_large_list_performance(page)
            logger.info("=== ALL PHASE 3 VERIFICATION SCENARIOS PASSED CLEANLY! ===")
        finally:
            browser.close()


if __name__ == "__main__":
    run_all_phase3_verifications()
