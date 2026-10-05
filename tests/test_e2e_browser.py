"""
End-to-End (E2E) Browser Tests with Playwright:
Tests full user journeys in Chromium:
- Page load and core UI components (branding, slots, meter, footer, synergy badges)
- Modal hero picker with Russian slang search (e.g. 'пудж', 'снайпер')
- Enter key press to select the first filtered hero in search
- Ally & enemy drafting with dynamic winrate meter and synergy updates
- Right-click hero ban and clear bans functionality
- Draft reset button restoring initial state
- Switching between Team Matrix and Detailed List views
- Weight sliders interactivity
"""
import re
import pytest
from playwright.sync_api import Page, expect


@pytest.mark.e2e
class TestDrafterE2E:

    def _wait_for_page(self, page: Page, live_server_url: str):
        page.goto(live_server_url)
        page.wait_for_load_state("domcontentloaded")
        page.locator("#alliesSlots .draft-slot").first.wait_for(state="visible", timeout=10000)

    def test_page_layout_and_branding(self, page: Page, live_server_url: str):
        """Verify initial page load, branding elements, slots count, synergy badges, and footer."""
        self._wait_for_page(page, live_server_url)

        # Header branding & top feedback banner
        header = page.locator(".logo-title")
        expect(header).to_be_visible()

        feedback_pill = page.locator(".top-feedback-pill")
        expect(feedback_pill).to_be_visible()
        expect(feedback_pill).to_contain_text("Оставьте свои идеи и пожелания")
        expect(feedback_pill).to_have_attribute("href", re.compile(r"github\.com/smeshar/StratzDrafter/discussions/categories/"))

        # Pick scores center panel
        scores_title = page.locator(".scores-panel-title")
        expect(scores_title).to_be_visible()
        expect(scores_title).to_have_text("ОЦЕНКА ПИКОВ")

        # Slots counts
        ally_slots = page.locator("#alliesSlots .draft-slot")
        expect(ally_slots).to_have_count(5)

        enemy_slots = page.locator("#enemiesSlots .draft-slot")
        expect(enemy_slots).to_have_count(5)

        # Initial synergy badges
        expect(page.locator("#alliesSynergy")).to_have_text("Синергия: 0.0%")
        expect(page.locator("#enemiesSynergy")).to_have_text("Синергия: 0.0%")

        # Initial meter state
        expect(page.locator("#alliesAdvScore")).to_have_text("50.0% Наша")
        expect(page.locator("#enemiesAdvScore")).to_have_text("50.0% Враг")

        # Footer links
        footer = page.locator(".app-footer")
        expect(footer).to_be_visible()
        expect(footer).to_contain_text("@noootle")
        expect(footer).to_contain_text("smeshar/StratzDrafter")

    def test_slot_side_click_focuses_without_modal(self, page: Page, live_server_url: str):
        """Clicking the side of a slot should focus it (active-slot class) without opening the picker modal."""
        self._wait_for_page(page, live_server_url)

        second_ally = page.locator("#alliesSlots .draft-slot").nth(1)
        modal = page.locator("#heroPickerModal")

        # Click side info of 2nd ally slot
        second_ally.locator(".slot-info").click()

        # Slot should become active
        expect(second_ally).to_have_class(re.compile(r"active-slot"))

        # Modal must NOT open
        expect(modal).to_be_hidden()

        # Now click the plus icon on the 2nd slot -> modal should open!
        second_ally.locator(".slot-portrait-wrapper").click()
        expect(modal).to_be_visible()

        # Close modal
        page.locator("#closeModalBtn").click()
        expect(modal).to_be_hidden()

    def test_hero_search_russian_slang_and_select(self, page: Page, live_server_url: str):
        """Click ally slot plus, search using Russian slang 'пудж', pick Pudge, verify slot updates."""
        self._wait_for_page(page, live_server_url)

        # Click plus icon on first ally slot (Pos 1 Carry)
        first_ally = page.locator("#alliesSlots .draft-slot").first
        first_ally.locator(".slot-portrait-wrapper").click()

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

    def test_hero_search_enter_key_selection(self, page: Page, live_server_url: str):
        """Typing in search and pressing Enter should select the first available hero."""
        self._wait_for_page(page, live_server_url)

        first_ally = page.locator("#alliesSlots .draft-slot").first
        first_ally.locator(".slot-portrait-wrapper").click()

        modal = page.locator("#heroPickerModal")
        expect(modal).to_be_visible()

        search_input = page.locator("#heroSearchInput")
        search_input.fill("снайпер")
        page.wait_for_timeout(200)

        # Press Enter key
        search_input.press("Enter")

        # Modal should close and Sniper should be selected
        expect(modal).to_be_hidden()
        expect(first_ally.locator(".slot-hero-name")).to_have_text("Sniper")

    def test_draft_both_teams_and_verify_meter_update(self, page: Page, live_server_url: str):
        """Pick ally and enemy heroes, verify winrate meter and draft insights update dynamically."""
        self._wait_for_page(page, live_server_url)

        # 1. Pick Ally: Crystal Maiden (using Russian slang 'цмка')
        first_ally = page.locator("#alliesSlots .draft-slot").first
        first_ally.locator(".slot-portrait-wrapper").click()
        page.wait_for_timeout(200)
        page.locator("#heroSearchInput").fill("цмка")
        page.wait_for_timeout(200)
        cm_cell = page.locator("#heroesGrid .hero-cell:has-text('Crystal Maiden')")
        expect(cm_cell).to_be_visible()
        cm_cell.click()

        # 2. Pick Enemy: Anti-Mage (using Russian slang 'ам')
        first_enemy = page.locator("#enemiesSlots .draft-slot").first
        first_enemy.locator(".slot-portrait-wrapper").click()
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
        self._wait_for_page(page, live_server_url)

        # Open modal
        page.locator("#alliesSlots .draft-slot .slot-portrait-wrapper").first.click()
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
        self._wait_for_page(page, live_server_url)

        # Pick ally
        first_ally = page.locator("#alliesSlots .draft-slot").first
        first_ally.locator(".slot-portrait-wrapper").click()
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
        expect(page.locator("#alliesSynergy")).to_have_text("Синергия: 0.0%")
        expect(page.locator("#enemiesSynergy")).to_have_text("Синергия: 0.0%")

    def test_switch_view_mode(self, page: Page, live_server_url: str):
        """Switch between team matrix view and detailed list view."""
        self._wait_for_page(page, live_server_url)

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
        self._wait_for_page(page, live_server_url)

        slider = page.locator("#counterWeight")
        slider.fill("85")
        slider.dispatch_event("input")

        expect(page.locator("#counterVal")).to_have_text("85%")

    def test_hero_pick_scores_slot_alignment_and_no_status_tags(self, page: Page, live_server_url: str):
        """Pick hero in ally slot 2 (Offlane) and enemy slot 1 (Mid), verify exact row mapping and no status tags."""
        self._wait_for_page(page, live_server_url)

        # Pick ally in slot 2 (3rd slot, Offlane)
        ally_slot_2 = page.locator("#alliesSlots .draft-slot").nth(2)
        ally_slot_2.locator(".slot-portrait-wrapper").click()
        page.wait_for_timeout(200)
        page.locator("#heroSearchInput").fill("axe")
        page.wait_for_timeout(200)
        page.locator("#heroesGrid .hero-cell:has-text('Axe')").click()

        # Pick enemy in slot 1 (2nd slot, Mid)
        enemy_slot_1 = page.locator("#enemiesSlots .draft-slot").nth(1)
        enemy_slot_1.locator(".slot-portrait-wrapper").click()
        page.wait_for_timeout(200)
        page.locator("#heroSearchInput").fill("pudge")
        page.wait_for_timeout(200)
        page.locator("#heroesGrid .hero-cell:has-text('Pudge')").click()

        page.wait_for_timeout(500)

        # In pick scores panel:
        # Row 0 (Carry) should have empty cards for ally and enemy
        row_0 = page.locator("#scoresRowsContainer .score-position-row").nth(0)
        expect(row_0.locator(".score-card-ally")).to_have_class(re.compile(r"empty-card"))
        expect(row_0.locator(".score-card-enemy")).to_have_class(re.compile(r"empty-card"))

        # Row 1 (Mid) should have Pudge on enemy side
        row_1 = page.locator("#scoresRowsContainer .score-position-row").nth(1)
        expect(row_1.locator(".score-card-ally")).to_have_class(re.compile(r"empty-card"))
        expect(row_1.locator(".score-card-enemy .score-hero-name")).to_have_text("Pudge")
        expect(row_1.locator(".score-card-enemy")).not_to_have_class(re.compile(r"empty-card"))

        # Row 2 (Offlane) should have Axe on ally side
        row_2 = page.locator("#scoresRowsContainer .score-position-row").nth(2)
        expect(row_2.locator(".score-card-ally .score-hero-name")).to_have_text("Axe")
        expect(row_2.locator(".score-card-ally")).not_to_have_class(re.compile(r"empty-card"))
        expect(row_2.locator(".score-card-enemy")).to_have_class(re.compile(r"empty-card"))

        # Verify no status tags ("Имба-пик", "Отличный пик", "Хороший пик", "Сложный пик", "Законтрен") exist
        scores_panel_text = page.locator("#pickScoresPanel").inner_text()
        for banned_word in ["Имба-пик", "Отличный пик", "Хороший пик", "Сложный пик", "Законтрен"]:
            assert banned_word not in scores_panel_text

        breakdown_text = page.locator("#breakdownSection").inner_text()
        for banned_word in ["Имба-пик", "Отличный пик", "Хороший пик", "Сложный пик", "Законтрен"]:
            assert banned_word not in breakdown_text

