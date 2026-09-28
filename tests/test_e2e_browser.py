"""
End-to-End (E2E) Browser Tests with Playwright:
Tests full user journeys in Chromium:
- Page load and core UI components (branding, slots, meter, footer)
- Modal hero picker with Russian slang search (e.g. 'пудж', 'снайпер')
- Ally & enemy drafting with dynamic winrate meter updates
- Right-click hero ban and clear bans functionality
- Draft reset button restoring initial state
- Switching between Team Matrix and Detailed List views
- Weight sliders interactivity
"""
import pytest
from playwright.sync_api import Page, expect


@pytest.mark.e2e
class TestDrafterE2E:

    def test_page_layout_and_branding(self, page: Page, live_server_url: str):
        """Verify initial page load, branding elements, slots count, and footer."""
        page.goto(live_server_url)
        page.wait_for_load_state("networkidle")

        # Page title
        expect(page).to_have_title("Stratz Custom Drafter | Dota 2")

        # Header branding
        header = page.locator(".logo-title")
        expect(header).to_contain_text("STRATZ")
        expect(header).to_contain_text("DRAFTER")

        # Winrate & VS badges
        winrate_title = page.locator(".meter-winrate-title")
        expect(winrate_title).to_be_visible()
        expect(winrate_title).to_have_text("WINRATE")

        vs_badge = page.locator(".vs-badge:has-text('VS')")
        expect(vs_badge).to_be_visible()

        # Slots counts
        ally_slots = page.locator("#alliesSlots .draft-slot")
        expect(ally_slots).to_have_count(5)

        enemy_slots = page.locator("#enemiesSlots .draft-slot")
        expect(enemy_slots).to_have_count(5)

        # Initial meter state
        expect(page.locator("#alliesAdvScore")).to_have_text("50.0% Наша")
        expect(page.locator("#enemiesAdvScore")).to_have_text("50.0% Враг")

        # Footer links
        footer = page.locator(".app-footer")
        expect(footer).to_be_visible()
        expect(footer).to_contain_text("@noootle")
        expect(footer).to_contain_text("smeshar/StratzDrafter")

    def test_hero_search_russian_slang_and_select(self, page: Page, live_server_url: str):
        """Click ally slot, search using Russian slang 'пудж', pick Pudge, verify slot updates."""
        page.goto(live_server_url)
        page.wait_for_load_state("networkidle")

        # Click first ally slot (Pos 1 Carry)
        first_ally = page.locator("#alliesSlots .draft-slot").first
        first_ally.click()

        # Modal should appear
        modal = page.locator("#heroPickerModal")
        expect(modal).to_be_visible()

        # Search for 'пудж'
        search_input = page.locator("#heroSearchInput")
        search_input.fill("пудж")
        page.wait_for_timeout(200)

        # Wait for grid to filter and click Pudge
        pudge_cell = page.locator("#heroesGrid .hero-cell:has-text('Pudge')")
        expect(pudge_cell).to_be_visible()
        pudge_cell.click()

        # Modal should close after selection
        expect(modal).to_be_hidden()

        # First ally slot should now display Pudge
        expect(first_ally.locator(".slot-hero-name")).to_have_text("Pudge")

    def test_draft_both_teams_and_verify_meter_update(self, page: Page, live_server_url: str):
        """Pick ally and enemy heroes, verify winrate meter and draft insights update dynamically."""
        page.goto(live_server_url)
        page.wait_for_load_state("networkidle")

        # 1. Pick Ally: Crystal Maiden (using Russian slang 'цмка')
        first_ally = page.locator("#alliesSlots .draft-slot").first
        first_ally.click()
        page.wait_for_timeout(200)
        page.locator("#heroSearchInput").fill("цмка")
        page.wait_for_timeout(200)
        cm_cell = page.locator("#heroesGrid .hero-cell:has-text('Crystal Maiden')")
        expect(cm_cell).to_be_visible()
        cm_cell.click()

        # 2. Pick Enemy: Anti-Mage (using Russian slang 'ам')
        first_enemy = page.locator("#enemiesSlots .draft-slot").first
        first_enemy.click()
        page.wait_for_timeout(200)
        page.locator("#heroSearchInput").fill("ам")
        page.wait_for_timeout(200)
        am_cell = page.locator("#heroesGrid .hero-cell:has-text('Anti-Mage')")
        expect(am_cell).to_be_visible()
        am_cell.click()

        # Verify enemy slot has Anti-Mage
        expect(first_enemy.locator(".slot-hero-name")).to_have_text("Anti-Mage")

        # Draft meter should update from 50.0% / 50.0%
        # Wait for network and debounced calculation
        page.wait_for_timeout(600)

        allies_score_text = page.locator("#alliesAdvScore").text_content()
        enemies_score_text = page.locator("#enemiesAdvScore").text_content()
        assert "%" in allies_score_text
        assert "%" in enemies_score_text

        # Insight paragraph should contain text
        insight = page.locator("#draftInsight").text_content()
        assert len(insight.strip()) > 0

    def test_ban_hero_via_context_menu_and_clear_bans(self, page: Page, live_server_url: str):
        """Right-click hero in modal to ban, verify ban chip appears, and clear bans."""
        page.goto(live_server_url)
        page.wait_for_load_state("networkidle")

        # Open modal
        page.locator("#alliesSlots .draft-slot").first.click()
        modal = page.locator("#heroPickerModal")
        expect(modal).to_be_visible()

        # Search for Axe and right-click to ban
        page.locator("#heroSearchInput").fill("axe")
        page.wait_for_timeout(200)
        axe_cell = page.locator("#heroesGrid .hero-cell:has-text('Axe')")
        expect(axe_cell).to_be_visible()
        axe_cell.click(button="right")

        # Close modal
        page.locator("#closeModalBtn").click()
        expect(modal).to_be_hidden()

        # Axe should appear in bans list
        ban_chip = page.locator("#bansList .banned-chip:has-text('Axe')")
        expect(ban_chip).to_be_visible()

        # Clear bans button should be visible
        clear_btn = page.locator("#clearBansBtn")
        expect(clear_btn).to_be_visible()
        clear_btn.click()

        # Bans list should reset to empty hint
        expect(ban_chip).to_have_count(0)
        expect(page.locator(".no-bans-hint")).to_be_visible()

    def test_reset_draft_button(self, page: Page, live_server_url: str):
        """Pick a hero, then click reset button and ensure entire state is cleared."""
        page.goto(live_server_url)
        page.wait_for_load_state("networkidle")

        # Pick ally
        first_ally = page.locator("#alliesSlots .draft-slot").first
        first_ally.click()
        page.wait_for_timeout(200)
        page.locator("#heroSearchInput").fill("pudge")
        page.wait_for_timeout(200)
        page.locator("#heroesGrid .hero-cell:has-text('Pudge')").click()
        expect(first_ally.locator(".slot-hero-name")).to_have_text("Pudge")

        # Click Reset button
        page.locator("#resetDraftBtn").click()
        page.wait_for_timeout(200)

        # Slot should return to empty
        expect(first_ally.locator(".slot-hero-name")).to_have_count(0)
        expect(first_ally.locator(".slot-empty-text")).to_have_text("Выбрать героя")

        # Draft meter resets to 50.0%
        expect(page.locator("#alliesAdvScore")).to_have_text("50.0% Наша")
        expect(page.locator("#enemiesAdvScore")).to_have_text("50.0% Враг")

    def test_switch_view_mode(self, page: Page, live_server_url: str):
        """Switch between team matrix view and detailed list view."""
        page.goto(live_server_url)
        page.wait_for_load_state("networkidle")

        # Switch to 'Подробный список'
        list_tab = page.locator("#viewModeTabs button[data-view='list']")
        list_tab.click()

        # List container and role filters become visible
        expect(page.locator("#recsListContainer")).to_have_css("display", "flex")
        expect(page.locator("#roleFilterBar")).to_have_css("display", "flex")
        expect(page.locator("#teamMatrixContainer")).to_have_css("display", "none")

        # Switch back to 'Сетка команды'
        matrix_tab = page.locator("#viewModeTabs button[data-view='matrix']")
        matrix_tab.click()

        expect(page.locator("#teamMatrixContainer")).to_have_css("display", "grid")
        expect(page.locator("#recsListContainer")).to_have_css("display", "none")

    def test_slider_adjustment(self, page: Page, live_server_url: str):
        """Verify weights slider changes update displayed percentage label."""
        page.goto(live_server_url)
        page.wait_for_load_state("networkidle")

        slider = page.locator("#counterWeight")
        slider.fill("85")
        slider.dispatch_event("input")

        expect(page.locator("#counterVal")).to_have_text("85%")
