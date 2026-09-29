"""
Unit & Integration tests verifying:
1. Pure offline cache operation (zero Stratz API calls in anonymous mode).
2. Local disk caching integrity (heroes_cache.json, stats_cache.json, matchups_cache.json).
3. Registration, login, and SQLite users.db isolation.
4. Personalized Stratz API token workflow & live query priority.
"""

import os
import json
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@pytest.mark.api
class TestCacheAndOfflineMode:

    def test_cache_files_exist_on_disk(self):
        """Verifies that the pre-cached JSON files are present on disk and populated."""
        heroes_file = DATA_DIR / "heroes_cache.json"
        stats_file = DATA_DIR / "stats_cache.json"
        matchups_file = DATA_DIR / "matchups_cache.json"

        assert heroes_file.exists(), "heroes_cache.json must exist"
        assert stats_file.exists(), "stats_cache.json must exist"
        assert matchups_file.exists(), "matchups_cache.json must exist"

        with open(heroes_file, "r", encoding="utf-8") as f:
            heroes_data = json.load(f)
            assert len(heroes_data) >= 120, f"Expected >= 120 heroes, found {len(heroes_data)}"

        with open(matchups_file, "r", encoding="utf-8") as f:
            matchups_data = json.load(f)
            assert len(matchups_data) >= 120, f"Expected >= 120 matchups, found {len(matchups_data)}"

    def test_anonymous_requests_make_zero_api_calls(self, client):
        """
        PROVES THAT IT IS REAL CACHE:
        All recommendation, matrix, and hero browsing requests in anonymous mode
        NEVER send any HTTP requests to https://api.stratz.com/graphql.
        """
        with patch("requests.post") as mock_post:
            # 1. Browse heroes
            r_heroes = client.get("/api/heroes?q=axe")
            assert r_heroes.status_code == 200
            assert r_heroes.get_json()["success"] is True

            # 2. Calculate single position recommendations
            r_rec = client.post("/api/recommend", json={
                "allies": [1],
                "enemies": [14],
                "bans": [2],
                "role": "pos1",
                "weights": {"counter": 70, "synergy": 20, "meta": 10},
                "allowOffMeta": True,
                "bracket": "LOW_RANK"
            })
            assert r_rec.status_code == 200
            assert r_rec.get_json()["success"] is True

            # 3. Calculate full team 5-column matrix
            r_matrix = client.post("/api/team_matrix", json={
                "allies": [1, 2],
                "enemies": [14, 8],
                "bans": [],
                "weights": {"counter": 70, "synergy": 20, "meta": 10},
                "allowOffMeta": True,
                "bracket": "LOW_RANK"
            })
            assert r_matrix.status_code == 200
            assert r_matrix.get_json()["success"] is True

            # 4. Draft analysis win rate
            r_analysis = client.post("/api/draft_analysis", json={
                "allies": [1, 2],
                "enemies": [14, 8]
            })
            assert r_analysis.status_code == 200
            assert r_analysis.get_json()["success"] is True

            # ASSERTION: Exactly ZERO network requests to Stratz API were made!
            assert mock_post.call_count == 0, (
                f"Expected 0 external Stratz API requests, but {mock_post.call_count} were attempted!"
            )


@pytest.mark.api
class TestUserAuthAndPersonalToken:

    def test_registration_and_login_flow(self, client):
        """Tests user registration, session management, and login by username/email."""
        import uuid
        unique_name = f"user_{uuid.uuid4().hex[:6]}"
        unique_email = f"{unique_name}@test.com"
        password = "testPassword123"

        # 1. Register new user
        res_reg = client.post("/api/auth/register", json={
            "name": unique_name,
            "email": unique_email,
            "password": password
        })
        assert res_reg.status_code == 200
        data_reg = res_reg.get_json()
        assert data_reg["success"] is True
        assert data_reg["user"]["email"] == unique_email
        assert data_reg["user"]["name"] == unique_name

        # 2. Check /api/auth/me reflects active session
        res_me = client.get("/api/auth/me")
        assert res_me.status_code == 200
        assert res_me.get_json()["authenticated"] is True
        assert res_me.get_json()["user"]["name"] == unique_name

        # 3. Logout
        res_logout = client.post("/api/auth/logout")
        assert res_logout.status_code == 200

        # 4. Confirm logged out
        res_me_out = client.get("/api/auth/me")
        assert res_me_out.get_json()["authenticated"] is False

        # 5. Login using username (nickname)
        res_login_name = client.post("/api/auth/login", json={
            "email": unique_name,
            "password": password
        })
        assert res_login_name.status_code == 200
        assert res_login_name.get_json()["success"] is True

        # 6. Logout and login using email
        client.post("/api/auth/logout")
        res_login_email = client.post("/api/auth/login", json={
            "email": unique_email,
            "password": password
        })
        assert res_login_email.status_code == 200
        assert res_login_email.get_json()["success"] is True

    def test_save_and_delete_personal_stratz_token(self, client):
        """Tests validating, saving, and deleting a personalized STRATZ API token."""
        import uuid
        unique_email = f"token_test_{uuid.uuid4().hex[:6]}@test.com"
        client.post("/api/auth/register", json={
            "name": "TokenTester",
            "email": unique_email,
            "password": "password123"
        })

        test_token = "fake-stratz-bearer-token-1234567890"

        # Mock validate_token to return True
        with patch("stratz_client.StratzClient.validate_token", return_value=True):
            res_save = client.post("/api/auth/token", json={"token": test_token})
            assert res_save.status_code == 200
            data_save = res_save.get_json()
            assert data_save["success"] is True
            assert data_save["user"]["hasStratzToken"] is True
            assert data_save["user"]["maskedToken"] == "...7890"

        # Verify status endpoint sees the user token
        res_status = client.get("/api/status")
        assert res_status.status_code == 200
        data_status = res_status.get_json()
        assert data_status["authMode"] == "personal_token"
        assert data_status["hasUserToken"] is True

        # Delete token
        res_del = client.delete("/api/auth/token")
        assert res_del.status_code == 200
        assert res_del.get_json()["user"]["hasStratzToken"] is False

        # Status after deletion
        res_status_after = client.get("/api/status")
        assert res_status_after.get_json()["authMode"] in ["authenticated_no_token", "server_token"]

    def test_preload_uses_user_token_and_updates_cache(self, client):
        """Tests that live synchronization utilizes the user's personal token."""
        import uuid
        unique_email = f"sync_{uuid.uuid4().hex[:6]}@test.com"
        client.post("/api/auth/register", json={
            "name": "SyncTester",
            "email": unique_email,
            "password": "password123"
        })

        my_personal_token = "my-secret-personal-stratz-token"

        with patch("stratz_client.StratzClient.validate_token", return_value=True):
            client.post("/api/auth/token", json={"token": my_personal_token})

        with patch("stratz_client.StratzClient.preload_all_matchups_async") as mock_preload:
            res_preload = client.post("/api/preload", json={"bracket": "LOW_RANK", "force": True})
            assert res_preload.status_code == 200
            assert res_preload.get_json()["success"] is True

            # Verify that preload was called with the user's specific token!
            mock_preload.assert_called_once()
            _, kwargs = mock_preload.call_args
            assert kwargs["custom_token"] == my_personal_token
            assert kwargs["force_refresh"] is True
