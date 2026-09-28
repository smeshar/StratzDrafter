"""
Unit tests for stratz_client.py:
Tests local JSON caching, role viability checks, draft score algorithms,
matrix recommendations, and draft analysis calculations.
"""
import pytest
from stratz_client import StratzClient


@pytest.mark.unit
class TestStratzClient:

    def test_cache_loaded(self, stratz_client: StratzClient):
        """Verify that heroes, position stats, and matchup caches are properly loaded from disk."""
        assert len(stratz_client.heroes) >= 120, "Should have loaded at least 120 heroes from disk cache"
        
        # Verify hero schema
        for hero_id, hero in list(stratz_client.heroes.items())[:10]:
            assert isinstance(hero_id, int)
            assert "displayName" in hero
            assert "shortName" in hero
            assert "attribute" in hero
            assert "iconUrl" in hero

        assert len(stratz_client.position_stats) > 0, "Position stats should not be empty"
        assert len(stratz_client.matchups) > 0, "Matchups cache should not be empty"

    def test_hero_role_viability(self, stratz_client: StratzClient):
        """Test position filtering and off-meta classification."""
        # Role 'all' should always be viable
        allowed, is_off_meta, share = stratz_client.is_hero_viable_for_position(1, "all")
        assert allowed is True
        assert share == 100.0

        # Anti-Mage (ID 1) is traditionally a pos1 carry
        allowed_pos1, is_off_meta_pos1, share_pos1 = stratz_client.is_hero_viable_for_position(
            1, "pos1", allow_off_meta=False
        )
        assert allowed_pos1 is True
        assert is_off_meta_pos1 is False
        assert share_pos1 > 50.0

        # Anti-Mage is NOT a standard pos5 full support
        allowed_pos5, _, _ = stratz_client.is_hero_viable_for_position(
            1, "pos5", allow_off_meta=False
        )
        assert allowed_pos5 is False

    def test_recommendations_exclude_taken_and_banned(self, stratz_client: StratzClient):
        """Ensure allies, enemies, and banned heroes are strictly excluded from recommendations."""
        # Hero IDs: 1 (Anti-Mage), 2 (Axe), 14 (Pudge), 8 (Juggernaut)
        allies = [1]
        enemies = [14]
        bans = [2, 8]
        taken_set = {1, 2, 8, 14}

        recs = stratz_client.calculate_recommendations(
            allies=allies,
            enemies=enemies,
            bans=bans,
            role="all",
            allow_off_meta=True
        )

        assert len(recs) > 0
        for rec in recs:
            assert rec["id"] not in taken_set, f"Hero {rec['id']} should have been excluded"

    def test_recommendations_sorting_and_breakdown(self, stratz_client: StratzClient):
        """Check that recommendations are sorted by totalScore descending and include detailed breakdowns."""
        allies = [11]  # Crystal Maiden
        enemies = [1]  # Anti-Mage

        recs = stratz_client.calculate_recommendations(
            allies=allies,
            enemies=enemies,
            bans=[],
            weights={"counter": 70, "synergy": 20, "meta": 10},
            role="all"
        )

        assert len(recs) > 0
        # Check scores are sorted in descending order
        scores = [r["totalScore"] for r in recs]
        assert scores == sorted(scores, reverse=True)

        # Check candidate structure
        first = recs[0]
        assert "id" in first
        assert "displayName" in first
        assert "totalScore" in first
        assert "counterScore" in first
        assert "synergyScore" in first
        assert "metaScore" in first
        assert "counterBreakdown" in first
        assert "synergyBreakdown" in first

    def test_calculate_draft_analysis_empty(self, stratz_client: StratzClient):
        """When no heroes are drafted, draft meter should be balanced at 50% vs 50%."""
        analysis = stratz_client.calculate_draft_analysis(allies=[], enemies=[])
        assert analysis["alliesWinRate"] == 50.0
        assert analysis["enemiesWinRate"] == 50.0
        assert "insight" in analysis
        assert isinstance(analysis["insight"], str)

    def test_calculate_draft_analysis_full(self, stratz_client: StratzClient):
        """With drafted heroes, winrates should sum to 100% and stay within [15.0, 85.0]."""
        allies = [1, 11, 25, 44, 86]     # 5 allies
        enemies = [2, 14, 35, 74, 99]    # 5 enemies

        analysis = stratz_client.calculate_draft_analysis(
            allies=allies,
            enemies=enemies,
            weights={"counter": 70, "synergy": 20, "meta": 10}
        )

        assert 15.0 <= analysis["alliesWinRate"] <= 85.0
        assert 15.0 <= analysis["enemiesWinRate"] <= 85.0
        assert round(analysis["alliesWinRate"] + analysis["enemiesWinRate"], 1) == 100.0

        assert "bestCounters" in analysis
        assert "biggestThreats" in analysis
        assert "counterAdvantage" in analysis
        assert "synergyAdvantage" in analysis
        assert "metaAdvantage" in analysis
        assert len(analysis["insight"]) > 0

    def test_team_recommendations_matrix(self, stratz_client: StratzClient):
        """Matrix recommendations should return 5 positions without taken heroes."""
        allies = [1]
        enemies = [2]
        bans = [14]
        taken_set = {1, 2, 14}

        matrix = stratz_client.get_team_recommendations_matrix(
            allies=allies,
            enemies=enemies,
            bans=bans,
            allow_off_meta=True
        )

        positions = ["pos1", "pos2", "pos3", "pos4", "pos5"]
        for pos in positions:
            assert pos in matrix
            assert isinstance(matrix[pos], list)
            assert len(matrix[pos]) > 0
            for item in matrix[pos]:
                assert item["id"] not in taken_set
