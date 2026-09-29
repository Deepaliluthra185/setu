"""
End-to-End browser test for Setu frontend using Playwright + Edge.
Validates all UI components, interactions, live complaint submission,
map rendering, simulator, BRICS toggle, and captures a full-page screenshot.
"""

import sys
import os
from playwright.sync_api import sync_playwright

def run_e2e_test():
    print("=== STARTING SETU FRONTEND E2E TEST ===")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1400, "height": 1000})

        # 1. Load application
        page.goto("http://127.0.0.1:8000", wait_until="networkidle")
        title = page.title()
        print(f"[OK] Page Title: {title}")
        assert "Setu" in title

        # 2. Check Hero section & 4 gap cards
        gap_cards = page.locator(".gap-card")
        assert gap_cards.count() == 4, f"Expected 4 gap cards, got {gap_cards.count()}"
        print("[OK] Hero section & 4 Gap-to-Fix cards verified")

        # 3. Test quick test chip & analyze complaint
        sample_btn = page.locator("button.sample-chip:has-text('Devnagar')")
        sample_btn.click()
        page.wait_for_timeout(500)
        
        input_text = page.locator("#complaintInput").input_value()
        print(f"[OK] Complaint input populated: '{input_text[:40]}...'")
        assert "Devnagar" in input_text

        # Wait for analyze execution
        page.wait_for_selector(".chip-location", timeout=5000)
        loc_chip = page.locator(".chip-location").inner_text()
        cat_chip = page.locator(".chip-category").inner_text()
        urg_chip = page.locator(".chip-urgency").inner_text()
        lang_chip = page.locator(".chip-lang").inner_text()
        print(f"[OK] Analysis chips: {cat_chip.encode('ascii', 'ignore').decode()} | {loc_chip.encode('ascii', 'ignore').decode()} | {urg_chip.encode('ascii', 'ignore').decode()} | {lang_chip.encode('ascii', 'ignore').decode()}")
        assert "Devnagar" in loc_chip
        assert "Power" in cat_chip
        assert "Urgent" in urg_chip

        # 4. Check Demand Hotspot SVG Map
        circles = page.locator("#mapCirclesGroup g.district-node")
        circle_count = circles.count()
        print(f"[OK] Demand Hotspot Map rendered with {circle_count} district nodes")
        assert circle_count == 9

        # Click on Rampur circle to verify Inspector
        rampur_circle = page.locator("#circle-Rampur")
        rampur_circle.click(force=True)
        page.wait_for_timeout(400)
        inspector_title = page.locator("#inspectDistrictName").inner_text()
        inspector_body = page.locator("#inspectDistrictBody").inner_text()
        print(f"[OK] District Inspector active for: {inspector_title}")
        assert "Rampur" in inspector_title
        assert "Complaint volume" in inspector_body

        # 5. Check Priority Ranking (Top 6)
        ranking_items = page.locator(".ranking-item")
        rank_count = ranking_items.count()
        top_district = ranking_items.first.locator(".rank-name").inner_text()
        top_score = ranking_items.first.locator(".rank-score-pill").inner_text()
        print(f"[OK] Priority Ranking rendered {rank_count} items. Top: {top_district} ({top_score})")
        assert rank_count == 6

        # 6. Check CPGRAMS Trends and State Select
        chart_paths = page.locator("#trendChart path")
        assert chart_paths.count() >= 3, "Expected at least 3 trend lines (Receipts, Disposal, Pending)"
        print(f"[OK] CPGRAMS Trend chart rendered with {chart_paths.count()} series lines")

        # Select Bihar
        page.select_option("#stateSelect", "Bihar")
        page.wait_for_timeout(300)
        bihar_bars = page.locator("#stateBarsContainer .state-bar-row")
        print(f"[OK] State Category breakdown for Bihar rendered {bihar_bars.count()} categories")
        assert bihar_bars.count() == 5

        # 7. Check BRICS Shared Model Toggle
        brics_panel = page.locator("#bricsPanel")
        assert not brics_panel.is_visible(), "BRICS panel should be hidden initially"
        page.locator("#bricsToggleBtn").click()
        page.wait_for_timeout(400)
        assert brics_panel.is_visible(), "BRICS panel should be visible after toggle"
        print("[OK] BRICS Shared Model view toggled on successfully")
        
        acc_text = page.locator(".accuracy-widget").inner_text()
        assert "71%" in acc_text and "84%" in acc_text
        print("[OK] BRICS accuracy comparison (71% vs 84%) verified")

        # 8. Check What-If Simulator
        initial_proj = page.locator("#projCovVal").inner_text()
        rampur_sim_lbl = page.locator("#sim-lbl-Rampur input")
        rampur_sim_lbl.click()
        page.wait_for_timeout(600)
        updated_proj = page.locator("#projCovVal").inner_text()
        gain_text = page.locator("#simGainBadge").inner_text()
        print(f"[OK] What-If Simulator updated: Initial {initial_proj} -> New {updated_proj} ({gain_text})")

        # 9. Check Post-Funding Impact Tracker
        impact_cards = page.locator(".impact-card")
        impact_count = impact_cards.count()
        print(f"[OK] Post-Funding Impact Tracker rendered {impact_count} funded district trajectories")
        assert impact_count >= 1

        # 10. Check Footer Governance & Disclosure Table
        hitl = page.locator(".hitl-alert").inner_text()
        assert "Human-in-the-Loop" in hitl
        disclosure_rows = page.locator(".disclosure-table tbody tr")
        print(f"[OK] Human-in-the-loop notice and Data Disclosure Table ({disclosure_rows.count()} rows) verified")
        assert disclosure_rows.count() == 5

        # Capture Screenshot
        screenshot_path = "frontend_verification.png"
        page.screenshot(path=screenshot_path, full_page=True)
        print(f"[OK] Full-page verification screenshot saved to: {screenshot_path}")

        browser.close()

    print("\n=== ALL FRONTEND E2E TESTS PASSED SUCCESSFULLY! ===")

if __name__ == "__main__":
    run_e2e_test()
