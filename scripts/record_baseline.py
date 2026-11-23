import os
import sys
from playwright.sync_api import sync_playwright

def record_visual_audit():
    os.makedirs("screenshots/baseline", exist_ok=True)
    os.makedirs("screenshots/responsive", exist_ok=True)

    viewports = [
        {"name": "mobile_320x568", "width": 320, "height": 568},
        {"name": "mobile_360x640", "width": 360, "height": 640},
        {"name": "mobile_375x812", "width": 375, "height": 812},
        {"name": "mobile_390x844", "width": 390, "height": 844},
        {"name": "mobile_414x896", "width": 414, "height": 896},
        {"name": "mobile_430x932", "width": 430, "height": 932},
        {"name": "mobile_480x800", "width": 480, "height": 800},
        {"name": "foldable_600x900", "width": 600, "height": 900},
        {"name": "tablet_768x1024", "width": 768, "height": 1024},
        {"name": "tablet_820x1180", "width": 820, "height": 1180},
        {"name": "laptop_1024x768", "width": 1024, "height": 768},
        {"name": "laptop_1280x720", "width": 1280, "height": 720},
        {"name": "laptop_1366x768", "width": 1366, "height": 768},
        {"name": "desktop_1440x900", "width": 1440, "height": 900},
        {"name": "desktop_1600x900", "width": 1600, "height": 900},
        {"name": "desktop_1920x1080", "width": 1920, "height": 1080},
    ]

    routes = [
        {"path": "/dashboard", "name": "dashboard"},
        {"path": "/study-plan", "name": "study_plan"},
        {"path": "/add-task", "name": "add_task"},
    ]

    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        console_errors = []
        page.on("console", lambda msg: console_errors.append(f"[{msg.type}] {msg.text}") if msg.type == "error" else None)

        print("--- RUNNING AUTOMATED PLAYWRIGHT AUDIT ---")

        for vp in viewports:
            page.set_viewport_size({"width": vp["width"], "height": vp["height"]})
            for r in routes:
                url = f"http://127.0.0.1:5000{r['path']}"
                res = page.goto(url, wait_until="networkidle")
                
                # Check horizontal overflow
                has_overflow = page.evaluate("() => document.documentElement.scrollWidth > window.innerWidth")
                scroll_width = page.evaluate("() => document.documentElement.scrollWidth")
                
                screenshot_path = f"screenshots/responsive/{r['name']}_{vp['name']}.png"
                page.screenshot(path=screenshot_path, full_page=False)

                status = "PASS" if not has_overflow else "OVERFLOW"
                results.append({
                    "page": r["name"],
                    "viewport": vp["name"],
                    "width": vp["width"],
                    "scroll_width": scroll_width,
                    "overflow": has_overflow,
                    "status_code": res.status,
                    "screenshot": screenshot_path
                })
                print(f"[{status}] {r['name']} @ {vp['name']} ({vp['width']}px) -> scrollWidth: {scroll_width}px | HTTP {res.status}")

        # Test Interactive Mobile Navigation Drawer
        print("\n--- TESTING MOBILE DRAWER INTERACTION (375px) ---")
        page.set_viewport_size({"width": 375, "height": 667})
        page.goto("http://127.0.0.1:5000/dashboard", wait_until="networkidle")
        
        # Click mobile menu button
        page.click("#mobileMenuBtn")
        page.wait_for_timeout(400) # Wait for CSS transition
        is_drawer_open = page.evaluate("() => document.getElementById('mobileNavDrawer').classList.contains('drawer-open')")
        page.screenshot(path="screenshots/responsive/mobile_drawer_open.png")
        print(f"Drawer Open State: {is_drawer_open}")

        # Close mobile menu via close button or backdrop position
        page.click(".drawer-close-btn")
        page.wait_for_timeout(400)
        is_drawer_closed = page.evaluate("() => !document.getElementById('mobileNavDrawer').classList.contains('drawer-open')")
        print(f"Drawer Closed State: {is_drawer_closed}")

        # Test Focus Kitchen Pomodoro Modal
        print("\n--- TESTING FOCUS POMODORO MODAL ---")
        page.set_viewport_size({"width": 1280, "height": 800})
        page.goto("http://127.0.0.1:5000/dashboard", wait_until="networkidle")
        page.click(".nav-btn-focus")
        page.wait_for_timeout(350)
        is_modal_visible = page.evaluate("() => document.getElementById('pomodoroModal').style.display === 'flex'")
        page.screenshot(path="screenshots/responsive/pomodoro_modal.png")
        print(f"Pomodoro Modal Visible: {is_modal_visible}")

        browser.close()

    print("\n--- CONSOLE ERRORS ---")
    if console_errors:
        for err in console_errors:
            print(f"Console error: {err}")
    else:
        print("Zero console errors detected across all viewports!")

    print(f"\nAudit complete! {len(results)} viewports/routes verified.")

if __name__ == "__main__":
    record_visual_audit()
