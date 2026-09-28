"""
Unit tests for aliases.py:
Tests Russian slang dictionary, nicknames, abbreviations, and search matching.
"""
import pytest
from aliases import matches_search, HERO_ALIASES


@pytest.mark.unit
class TestAliases:

    def test_aliases_dictionary_populated(self):
        """Ensure the alias dictionary contains entries for the majority of heroes."""
        assert len(HERO_ALIASES) >= 100
        for hero_name, alias_list in HERO_ALIASES.items():
            assert isinstance(alias_list, list)
            assert len(alias_list) > 0
            for alias in alias_list:
                assert isinstance(alias, str)
                assert len(alias.strip()) > 0

    @pytest.mark.parametrize("query,name,display_name,short_name,expected", [
        # English matches
        ("pudge", "npc_dota_hero_pudge", "Pudge", "pudge", True),
        ("axe", "npc_dota_hero_axe", "Axe", "axe", True),
        ("anti", "npc_dota_hero_antimage", "Anti-Mage", "antimage", True),
        ("magina", "npc_dota_hero_antimage", "Anti-Mage", "antimage", True),

        # Russian slang matches
        ("пудж", "npc_dota_hero_pudge", "Pudge", "pudge", True),
        ("мясник", "npc_dota_hero_pudge", "Pudge", "pudge", True),
        ("ам", "npc_dota_hero_antimage", "Anti-Mage", "antimage", True),
        ("папич", "npc_dota_hero_skeleton_king", "Wraith King", "wraith_king", True),
        ("леорик", "npc_dota_hero_skeleton_king", "Wraith King", "wraith_king", True),
        ("гуля", "npc_dota_hero_life_stealer", "Lifestealer", "lifestealer", True),
        ("найкс", "npc_dota_hero_life_stealer", "Lifestealer", "lifestealer", True),
        ("фура", "npc_dota_hero_furion", "Nature's Prophet", "furion", True),
        ("фурион", "npc_dota_hero_furion", "Nature's Prophet", "furion", True),
        ("сф", "npc_dota_hero_nevermore", "Shadow Fiend", "nevermore", True),
        ("койлы", "npc_dota_hero_nevermore", "Shadow Fiend", "nevermore", True),
        ("тракса", "npc_dota_hero_drow_ranger", "Drow Ranger", "drow_ranger", True),
        ("цмка", "npc_dota_hero_crystal_maiden", "Crystal Maiden", "crystal_maiden", True),
        ("зевс", "npc_dota_hero_zuus", "Zeus", "zuus", True),
        ("инвокер", "npc_dota_hero_invoker", "Invoker", "invoker", True),
        ("вокер", "npc_dota_hero_invoker", "Invoker", "invoker", True),
        ("титан", "npc_dota_hero_elder_titan", "Elder Titan", "elder_titan", True),

        # Case-insensitivity
        ("ПУДЖ", "npc_dota_hero_pudge", "Pudge", "pudge", True),
        ("Ам", "npc_dota_hero_antimage", "Anti-Mage", "antimage", True),
        ("ФУРА", "npc_dota_hero_furion", "Nature's Prophet", "furion", True),

        # Partial prefix matching
        ("пуд", "npc_dota_hero_pudge", "Pudge", "pudge", True),
        ("фури", "npc_dota_hero_furion", "Nature's Prophet", "furion", True),

        # Non-matching queries
        ("xyzunknown", "npc_dota_hero_pudge", "Pudge", "pudge", False),
        ("123456", "npc_dota_hero_antimage", "Anti-Mage", "antimage", False),
    ])
    def test_matches_search_queries(self, query, name, display_name, short_name, expected):
        """Tests that search queries correctly identify heroes by name or alias."""
        result = matches_search(query, name, display_name, short_name)
        assert result == expected

    def test_empty_search_query(self):
        """Empty query should match everything."""
        assert matches_search("", "npc_dota_hero_pudge", "Pudge", "pudge") is True
        assert matches_search("   ", "npc_dota_hero_pudge", "Pudge", "pudge") is True
