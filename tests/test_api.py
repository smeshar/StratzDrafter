"""
Integration tests for Flask API routes (app.py):
Tests page serving, heroes listing with slang search and filters,
recommendation endpoints, team matrix, draft analysis, and preloader status.
"""
import pytest


@pytest.mark.api
class TestFlaskAPI:

    def test_index_page(self, client):
        """GET / should render the main drafter web interface."""
        response = client.get("/")
        assert response.status_code == 200
        html = response.get_data(as_text=True)
        assert "logo-title" in html
        assert "WINRATE" in html
        assert "VS" in html
        assert "alliesSlots" in html
        assert "enemiesSlots" in html
        assert "teamMatrixContainer" in html
        assert "@noootle" in html

    def test_get_heroes_all(self, client):
        """GET /api/heroes returns the full list of heroes."""
        response = client.get("/api/heroes")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["count"] >= 120
        assert len(data["heroes"]) == data["count"]

    @pytest.mark.parametrize("query,expected_hero", [
        ("фура", "Nature's Prophet"),
        ("пудж", "Pudge"),
        ("папич", "Wraith King"),
        ("гуля", "Lifestealer"),
        ("ам", "Anti-Mage"),
        ("сф", "Shadow Fiend"),
        ("морф", "Morphling"),
    ])
    def test_get_heroes_search_by_slang(self, client, query, expected_hero):
        """GET /api/heroes?q=... finds heroes using Russian slang/aliases."""
        response = client.get(f"/api/heroes?q={query}")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        names = [h["displayName"] for h in data["heroes"]]
        assert expected_hero in names

    def test_get_heroes_attribute_filter(self, client):
        """GET /api/heroes?attr=str filters heroes by attribute."""
        response = client.get("/api/heroes?attr=str")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert len(data["heroes"]) > 0
        for hero in data["heroes"]:
            assert hero["attribute"].lower() == "str"

    def test_get_status(self, client):
        """GET /api/status returns database and cache information."""
        response = client.get("/api/status")
        assert response.status_code == 200
        data = response.get_json()
        assert "heroesCount" in data
        assert "cachedMatchupsCount" in data
        assert "currentBracket" in data
        assert "availableBrackets" in data
        assert data["heroesCount"] >= 120

    def test_post_recommend(self, client):
        """POST /api/recommend returns recommendations and draft analysis."""
        payload = {
            "allies": [1],       # Anti-Mage
            "enemies": [14],     # Pudge
            "bans": [2],         # Axe
            "role": "pos1",
            "weights": {"counter": 70, "synergy": 20, "meta": 10},
            "allowOffMeta": True,
            "bracket": "LOW_RANK"
        }
        response = client.post("/api/recommend", json=payload)
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "recommendations" in data
        assert "analysis" in data
        assert data["role"] == "pos1"

    def test_post_team_matrix(self, client):
        """POST /api/team_matrix returns 5 position columns simultaneously."""
        payload = {
            "allies": [1],
            "enemies": [14, 2],
            "bans": [],
            "weights": {"counter": 70, "synergy": 20, "meta": 10},
            "allowOffMeta": True,
            "bracket": "LOW_RANK"
        }
        response = client.post("/api/team_matrix", json=payload)
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "matrix" in data
        assert "analysis" in data
        for pos in ["pos1", "pos2", "pos3", "pos4", "pos5"]:
            assert pos in data["matrix"]

    def test_post_draft_analysis(self, client):
        """POST /api/draft_analysis calculates win rates and draft insight."""
        payload = {
            "allies": [1, 11],
            "enemies": [14, 2],
            "weights": {"counter": 70, "synergy": 20, "meta": 10},
            "bracket": "LOW_RANK"
        }
        response = client.post("/api/draft_analysis", json=payload)
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert "analysis" in data
        analysis = data["analysis"]
        assert "alliesWinRate" in analysis
        assert "enemiesWinRate" in analysis
        assert "insight" in analysis
        assert round(analysis["alliesWinRate"] + analysis["enemiesWinRate"], 1) == 100.0

    def test_post_preload(self, client):
        """POST /api/preload starts or triggers preloader."""
        response = client.post("/api/preload", json={"bracket": "LOW_RANK"})
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
