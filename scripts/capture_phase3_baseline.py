"""Automated baseline screenshot capture for Phase 3 visual regression reference.

Captures all views and modals in both Light and Dark themes.
"""

import time
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE_URL = "http://localhost:3000"
SCREENSHOTS_DIR = Path("report/screenshots")
SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)


def set_theme(page, theme: str):
    """Ensure page is in desired theme ('light' or 'dark')."""
    is_dark = page.evaluate("document.documentElement.classList.contains('dark')")
    toggle_btn = page.locator("[data-testid='theme-toggle-btn']")
    if theme == "dark" and not is_dark:
        toggle_btn.click()
        time.sleep(0.3)
    elif theme == "light" and is_dark:
        toggle_btn.click()
        time.sleep(0.3)


def capture_all_for_theme(page, theme: str):
    print(f"\n--- Capturing Baseline Screenshots for Theme: {theme.upper()} ---")
    set_theme(page, theme)
    time.sleep(0.5)

    # 1. Live Monitor View
    page.locator("button:has-text('Live Execution Monitor')").first.click()
    time.sleep(0.5)
    page.screenshot(path=str(SCREENSHOTS_DIR / f"phase3_baseline_monitor_{theme}.png"))
    print(f"Captured: phase3_baseline_monitor_{theme}.png")

    # 2. Header MCP Modal
    mcp_btn = page.locator("[data-testid='header-mcp-btn']")
    mcp_btn.click()
    time.sleep(0.5)
    page.screenshot(path=str(SCREENSHOTS_DIR / f"phase3_baseline_modal_mcp_{theme}.png"))
    page.locator("button:has-text('Close')").first.click()
    time.sleep(0.3)
    print(f"Captured: phase3_baseline_modal_mcp_{theme}.png")

    # 3. User Guide Modal
    guide_btn = page.locator("[data-testid='sidebar-user-guide-btn']")
    guide_btn.click()
    time.sleep(0.5)
    page.screenshot(path=str(SCREENSHOTS_DIR / f"phase3_baseline_modal_user_guide_{theme}.png"))
    page.locator("button:has-text('Close Guide'), button:has-text('Close')").first.click()
    time.sleep(0.3)
    print(f"Captured: phase3_baseline_modal_user_guide_{theme}.png")

    # 4. Pluggable Targets View
    page.locator("button:has-text('Pluggable Targets')").first.click()
    time.sleep(0.5)
    page.screenshot(path=str(SCREENSHOTS_DIR / f"phase3_baseline_plugins_{theme}.png"))
    print(f"Captured: phase3_baseline_plugins_{theme}.png")

    # 5. Add Plugin Modal
    page.locator("button:has-text('Add Pluggable Target')").first.click()
    time.sleep(0.5)
    page.screenshot(path=str(SCREENSHOTS_DIR / f"phase3_baseline_modal_add_plugin_{theme}.png"))
    page.locator("button:has-text('Cancel')").first.click()
    time.sleep(0.3)
    print(f"Captured: phase3_baseline_modal_add_plugin_{theme}.png")

    # 6. Edit Config Modal
    edit_btn = page.locator("[data-testid^='edit-btn-']").first
    edit_btn.click()
    time.sleep(0.5)
    page.screenshot(path=str(SCREENSHOTS_DIR / f"phase3_baseline_modal_edit_config_{theme}.png"))
    page.locator("button:has-text('Cancel')").first.click()
    time.sleep(0.3)
    print(f"Captured: phase3_baseline_modal_edit_config_{theme}.png")

    # 7. Uninstall Modal
    uninstall_btn = page.locator("[data-testid^='uninstall-btn-']").first
    uninstall_btn.click()
    time.sleep(0.5)
    page.screenshot(path=str(SCREENSHOTS_DIR / f"phase3_baseline_modal_uninstall_{theme}.png"))
    page.locator("button:has-text('Cancel')").first.click()
    time.sleep(0.3)
    print(f"Captured: phase3_baseline_modal_uninstall_{theme}.png")

    # 8. Knowledge & Rules View
    page.locator("button:has-text('Knowledge & Rules')").first.click()
    time.sleep(0.5)
    page.screenshot(path=str(SCREENSHOTS_DIR / f"phase3_baseline_knowledge_{theme}.png"))
    print(f"Captured: phase3_baseline_knowledge_{theme}.png")

    # 9. Create Rule Modal
    page.locator("button:has-text('Governance Rules')").first.click()
    time.sleep(0.5)
    create_rule_btn = page.locator("[data-testid='create-rule-btn']")
    create_rule_btn.click()
    time.sleep(0.5)
    page.screenshot(path=str(SCREENSHOTS_DIR / f"phase3_baseline_modal_create_rule_{theme}.png"))
    page.locator("button:has-text('Cancel')").first.click()
    time.sleep(0.3)
    print(f"Captured: phase3_baseline_modal_create_rule_{theme}.png")

    # 10. Audit Logs View
    page.locator("button:has-text('Audit Logs')").first.click()
    time.sleep(0.5)
    page.screenshot(path=str(SCREENSHOTS_DIR / f"phase3_baseline_audit_{theme}.png"))
    print(f"Captured: phase3_baseline_audit_{theme}.png")

    # 11. Audit Detail Drawer / Modal
    row = page.locator("table tbody tr").first
    if row.is_visible():
        row.click()
        time.sleep(0.5)
        page.screenshot(path=str(SCREENSHOTS_DIR / f"phase3_baseline_modal_audit_detail_{theme}.png"))
        page.locator("button:has-text('Close')").first.click()
        time.sleep(0.3)
        print(f"Captured: phase3_baseline_modal_audit_detail_{theme}.png")


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        print(f"Navigating to {BASE_URL}...")
        page.goto(BASE_URL)
        page.wait_for_selector("text=AEGISGATE", timeout=10000)

        # Capture in Light theme first
        capture_all_for_theme(page, "light")

        # Capture in Dark theme
        capture_all_for_theme(page, "dark")

        # Restore Light theme
        set_theme(page, "light")

        browser.close()
        print("\n[OK] All baseline screenshots successfully captured!")


if __name__ == "__main__":
    run()
