import os
import json
import time
import threading
import requests
from pathlib import Path
from dotenv import load_dotenv

# Ensure environment is loaded
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

HEROES_CACHE_FILE = DATA_DIR / "heroes_cache.json"
STATS_CACHE_FILE = DATA_DIR / "stats_cache.json"
MATCHUPS_CACHE_FILE = DATA_DIR / "matchups_cache.json"
DURATIONS_CACHE_FILE = DATA_DIR / "durations_cache.json"

STRATZ_GRAPHQL_URL = "https://api.stratz.com/graphql"

# Available rank bracket configurations
BRACKET_CONFIGS = {
    # Individual Dota 2 ranks
    "HERALD": ["HERALD_GUARDIAN"],
    "GUARDIAN": ["HERALD_GUARDIAN"],
    "CRUSADER": ["CRUSADER_ARCHON"],
    "ARCHON": ["CRUSADER_ARCHON"],
    "LEGEND": ["LEGEND_ANCIENT"],
    "ANCIENT": ["LEGEND_ANCIENT"],
    "DIVINE": ["DIVINE_IMMORTAL"],
    "IMMORTAL": ["DIVINE_IMMORTAL"],
    "ALL": ["ALL"],
    # Legacy paired & aggregate keys for full backwards compatibility
    "HERALD_GUARDIAN": ["HERALD_GUARDIAN"],
    "CRUSADER_ARCHON": ["CRUSADER_ARCHON"],
    "LOW_RANK": ["HERALD_GUARDIAN", "CRUSADER_ARCHON"],
    "LEGEND_ANCIENT": ["LEGEND_ANCIENT"],
    "DIVINE_IMMORTAL": ["DIVINE_IMMORTAL"],
}

POSITION_MAP = {
    "pos1": "POSITION_1",
    "pos2": "POSITION_2",
    "pos3": "POSITION_3",
    "pos4": "POSITION_4",
    "pos5": "POSITION_5"
}

POSITION_LABELS = {
    "pos1": "Позиция 1 (Керри)",
    "pos2": "Позиция 2 (Мид)",
    "pos3": "Позиция 3 (Оффлейн / Тройка)",
    "pos4": "Позиция 4 (Семи-саппорт)",
    "pos5": "Позиция 5 (Фулл-саппорт)"
}

# Strategic matchup weights based on lane alignment and Core vs Support priority (Variant 3)
ROLE_MATCHUP_WEIGHTS = {
    # Safe lane Carry: Highest danger from enemy offlaner (pos3) and lane support (pos4), then mid (pos2)
    "pos1": {
        "pos3": 1.6,  # Enemy offlaner (direct laning opponent)
        "pos4": 1.3,  # Enemy soft support (lane harasser)
        "pos2": 1.3,  # Enemy midlaner (early ganks / midgame tempo)
        "pos1": 1.2,  # Enemy carry (late game scaling counterpart)
        "pos5": 0.7,  # Enemy hard support (opposite lane)
    },
    # Midlaner: Extreme 1v1 lane priority (pos2) and roamers (pos4)
    "pos2": {
        "pos2": 1.8,  # Enemy mid (direct 1v1 matchup)
        "pos4": 1.3,  # Enemy roamer / 4 (mid ganks)
        "pos1": 1.2,  # Enemy carry (target/rival)
        "pos3": 1.1,  # Enemy offlaner
        "pos5": 0.7,  # Enemy hard support
    },
    # Offlaner: Highest priority is shutting down enemy carry (pos1) and trading with 5 (pos5)
    "pos3": {
        "pos1": 1.6,  # Enemy carry (direct lane opponent)
        "pos5": 1.3,  # Enemy hard support (lane protector)
        "pos2": 1.2,  # Enemy mid
        "pos3": 1.1,  # Enemy offlaner
        "pos4": 0.8,  # Enemy soft support
    },
    # Soft Support (pos4): Assists offlane against enemy carry & trades with 5
    "pos4": {
        "pos1": 1.5,  # Enemy carry
        "pos5": 1.3,  # Enemy hard support
        "pos2": 1.2,  # Enemy mid (rune control/ganks)
        "pos3": 1.0,  # Enemy offlaner
        "pos4": 1.0,  # Enemy soft support
    },
    # Hard Support (pos5): Protects carry from enemy offlaner (pos3) and trades with pos4
    "pos5": {
        "pos3": 1.6,  # Enemy offlaner
        "pos4": 1.4,  # Enemy soft support (lane trading)
        "pos2": 1.1,  # Enemy mid (midgame saves)
        "pos1": 1.0,  # Enemy carry
        "pos5": 0.8,  # Enemy hard support
    },
    # General / role "all": Cores prioritized over supports
    "all": {
        "pos1": 1.3,
        "pos2": 1.3,
        "pos3": 1.2,
        "pos4": 0.8,
        "pos5": 0.7,
    }
}

# Lane alignment and matchups for Laning stage analysis
LANE_CONFIG = {
    # Safe lane Carry: faces enemy Offlaner (pos3) & Soft Support (pos4). Partner: Hard Support (pos5).
    "pos1": {
        "opponents": {"pos3": 0.65, "pos4": 0.35},
        "partner": "pos5",
        "name": "Легкая линия"
    },
    # Midlaner: 1v1 against enemy Mid (pos2). Solo lane.
    "pos2": {
        "opponents": {"pos2": 1.0},
        "partner": None,
        "name": "Мид 1v1"
    },
    # Offlaner: faces enemy Carry (pos1) & Hard Support (pos5). Partner: Soft Support (pos4).
    "pos3": {
        "opponents": {"pos1": 0.65, "pos5": 0.35},
        "partner": "pos4",
        "name": "Сложная линия"
    },
    # Soft Support: lanes with Offlaner (pos3) vs enemy Carry (pos1) & Hard Support (pos5).
    "pos4": {
        "opponents": {"pos1": 0.65, "pos5": 0.35},
        "partner": "pos3",
        "name": "Сложная линия"
    },
    # Hard Support: lanes with Carry (pos1) vs enemy Offlaner (pos3) & Soft Support (pos4).
    "pos5": {
        "opponents": {"pos3": 0.65, "pos4": 0.35},
        "partner": "pos1",
        "name": "Легкая линия"
    }
}

class StratzClient:
    def __init__(self):
        self.api_token = os.getenv("STRATZ_API", "").strip()
        if not self.api_token:
            print("WARNING: STRATZ_API environment variable not found in .env!")

        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "User-Agent": "STRATZ_API",
            "Content-Type": "application/json"
        }

        # Memory caches
        self.heroes = {}          # id -> hero dict
        self.position_stats = {}  # (heroId, pos) -> { matchCount, winCount, winRate }
        self.hero_totals = {}     # heroId -> { matchCount, winCount, winRate }
        self.matchups = {}        # heroId -> { 'vs': {heroId2: {synergy, winCount, matchCount}}, 'with': {...} }
        self.hero_durations = {}   # heroId -> { baseWinRate, totalMatches, peakMinute, peakDelta, points: [...] }
        self.is_preloading = False
        self.preload_progress = 0
        self.current_bracket = "LOW_RANK"

        # Load from disk cache first
        self._load_disk_cache()

    def _execute_query(self, query: str, variables: dict = None, custom_token: str = None) -> dict:
        """Executes a GraphQL query against Stratz API, optionally using a personalized token."""
        try:
            token = (custom_token or "").strip() or self.api_token
            if not token:
                return {}
            headers = {
                "Authorization": f"Bearer {token}",
                "User-Agent": "STRATZ_API",
                "Content-Type": "application/json"
            }
            payload = {"query": query}
            if variables:
                payload["variables"] = variables
            res = requests.post(STRATZ_GRAPHQL_URL, json=payload, headers=headers, timeout=20)
            if res.status_code == 200:
                data = res.json()
                if "errors" in data:
                    print("GraphQL Errors:", data["errors"])
                return data
            else:
                print(f"Stratz API Error HTTP {res.status_code}: {res.text[:200]}")
                return {}
        except Exception as e:
            print(f"Exception querying Stratz API: {e}")
            return {}

    def validate_token(self, token: str) -> bool:
        """Validates a STRATZ API token with a lightweight query."""
        if not token or len(token.strip()) < 10:
            return False
        test_query = """
        query TestToken {
            constants {
                gameVersions {
                    id
                }
            }
        }
        """
        data = self._execute_query(test_query, custom_token=token)
        return bool(data and "data" in data and "constants" in data["data"])

    def _load_disk_cache(self):
        """Loads heroes and cached stats from local JSON files if they exist."""
        if HEROES_CACHE_FILE.exists():
            try:
                with open(HEROES_CACHE_FILE, "r", encoding="utf-8") as f:
                    self.heroes = {int(k): v for k, v in json.load(f).items()}
                print(f"Loaded {len(self.heroes)} heroes from cache.")
            except Exception as e:
                print(f"Failed to read heroes cache: {e}")

        if STATS_CACHE_FILE.exists():
            try:
                with open(STATS_CACHE_FILE, "r", encoding="utf-8") as f:
                    cached_stats = json.load(f)
                    self.hero_totals = {int(k): v for k, v in cached_stats.get("totals", {}).items()}
                    pos_raw = cached_stats.get("positions", {})
                    self.position_stats = {
                        (int(k.split(":")[0]), k.split(":")[1]): v
                        for k, v in pos_raw.items()
                        if ":" in k
                    }
                print(f"Loaded {len(self.position_stats)} position stats from cache.")
            except Exception as e:
                print(f"Failed to read stats cache: {e}")

        if MATCHUPS_CACHE_FILE.exists():
            try:
                with open(MATCHUPS_CACHE_FILE, "r", encoding="utf-8") as f:
                    raw_matchups = json.load(f)
                    for h_str, h_data in raw_matchups.items():
                        h_id = int(h_str)
                        vs_map = {int(k): v for k, v in h_data.get("vs", {}).items()}
                        with_map = {int(k): v for k, v in h_data.get("with", {}).items()}
                        self.matchups[h_id] = {"vs": vs_map, "with": with_map}
                print(f"Loaded {len(self.matchups)} hero matchups from cache.")
            except Exception as e:
                print(f"Failed to read matchups cache: {e}")

        if DURATIONS_CACHE_FILE.exists():
            try:
                with open(DURATIONS_CACHE_FILE, "r", encoding="utf-8") as f:
                    raw_durations = json.load(f)
                    self.hero_durations = {int(k): v for k, v in raw_durations.items()}
                print(f"Loaded duration curves for {len(self.hero_durations)} heroes from cache.")
            except Exception as e:
                print(f"Failed to read durations cache: {e}")

    def _save_disk_cache(self):
        """Saves current state to local JSON cache files safely."""
        try:
            if self.heroes:
                with open(HEROES_CACHE_FILE, "w", encoding="utf-8") as f:
                    json.dump(self.heroes, f, ensure_ascii=False, indent=2)

            if self.position_stats or self.hero_totals:
                pos_formatted = {f"{k[0]}:{k[1]}": v for k, v in self.position_stats.items()}
                with open(STATS_CACHE_FILE, "w", encoding="utf-8") as f:
                    json.dump({"totals": self.hero_totals, "positions": pos_formatted}, f, ensure_ascii=False, indent=2)

            # Safeguard: never overwrite a full 127-hero matchup cache with an empty or partial dictionary
            if self.matchups and len(self.matchups) >= 50:
                matchups_serializable = {}
                for h_id, data in self.matchups.items():
                    matchups_serializable[str(h_id)] = {
                        "vs": {str(k): v for k, v in data["vs"].items()},
                        "with": {str(k): v for k, v in data["with"].items()}
                    }
                with open(MATCHUPS_CACHE_FILE, "w", encoding="utf-8") as f:
                    json.dump(matchups_serializable, f, ensure_ascii=False)

            if self.hero_durations:
                durations_serializable = {str(k): v for k, v in self.hero_durations.items()}
                with open(DURATIONS_CACHE_FILE, "w", encoding="utf-8") as f:
                    json.dump(durations_serializable, f, ensure_ascii=False, indent=2)

            print("Disk cache successfully saved.")
        except Exception as e:
            print(f"Failed to save disk cache: {e}")

    def fetch_heroes(self, force_refresh: bool = False) -> dict:
        """Fetches all hero constants from Stratz."""
        if self.heroes and not force_refresh:
            return self.heroes

        query = """
        query {
          constants {
            heroes {
              id
              name
              displayName
              shortName
              aliases
              roles {
                roleId
                level
              }
              stats {
                primaryAttribute
                complexity
              }
            }
          }
        }
        """
        res = self._execute_query(query)
        heroes_list = res.get("data", {}).get("constants", {}).get("heroes", [])
        if not heroes_list:
            print("Failed to fetch heroes from Stratz.")
            return self.heroes

        for h in heroes_list:
            h_id = h["id"]
            short_name = h.get("shortName", "")
            # CDN hero portrait URLs
            icon_url = f"https://cdn.cloudflare.steamstatic.com/apps/dota2/images/dota_react/heroes/{short_name}.png"
            vert_url = f"https://cdn.stratz.com/images/dota2/heroes/{short_name}_vert.png"

            self.heroes[h_id] = {
                "id": h_id,
                "name": h.get("name", ""),
                "displayName": h.get("displayName", ""),
                "shortName": short_name,
                "aliases": h.get("aliases", []),
                "attribute": (h.get("stats") or {}).get("primaryAttribute", "str"),
                "complexity": (h.get("stats") or {}).get("complexity", 1),
                "roles": [r["roleId"] for r in h.get("roles", [])],
                "iconUrl": icon_url,
                "vertUrl": vert_url
            }

        self._save_disk_cache()
        return self.heroes

    def fetch_stats(self, bracket_key: str = "LOW_RANK", force_refresh: bool = False):
        """Fetches position stats and general winrates for all heroes in specified bracket."""
        if len(self.position_stats) >= 500 and not force_refresh:
            return

        brackets = BRACKET_CONFIGS.get(bracket_key, BRACKET_CONFIGS["LOW_RANK"])
        bracket_str = f"[{', '.join(brackets)}]"

        query = f"""
        query {{
          heroStats {{
            stats(bracketBasicIds: {bracket_str}, groupByPosition: true) {{
              heroId
              position
              matchCount
              winCount
            }}
            winGameVersion(take: 150) {{
              heroId
              gameVersionId
              winCount
              matchCount
            }}
          }}
        }}
        """
        res = self._execute_query(query)
        data = res.get("data", {}).get("heroStats", {})
        stats_list = data.get("stats", [])
        win_versions = data.get("winGameVersion", [])

        # Process winGameVersion for overall winrate in latest patch
        if win_versions:
            latest_v = max(v["gameVersionId"] for v in win_versions)
            for v in win_versions:
                if v["gameVersionId"] == latest_v:
                    h_id = v["heroId"]
                    mc = v["matchCount"]
                    wc = v["winCount"]
                    wr = (wc / mc * 100) if mc > 0 else 50.0
                    self.hero_totals[h_id] = {
                        "matchCount": mc,
                        "winCount": wc,
                        "winRate": round(wr, 2)
                    }

        # Process position-specific stats
        for s in stats_list:
            h_id = s["heroId"]
            pos = s["position"]
            mc = s["matchCount"]
            wc = s["winCount"]
            wr = (wc / mc * 100) if mc > 0 else 50.0
            self.position_stats[(h_id, pos)] = {
                "matchCount": mc,
                "winCount": wc,
                "winRate": round(wr, 2)
            }

        self._save_disk_cache()

    def fetch_matchups_batch(self, hero_ids: list, bracket_key: str = "LOW_RANK", custom_token: str = None):
        """Fetches matchup matrix for a list of heroes in a single GraphQL query."""
        if not hero_ids:
            return

        brackets = BRACKET_CONFIGS.get(bracket_key, BRACKET_CONFIGS["LOW_RANK"])
        bracket_str = f"[{', '.join(brackets)}]"

        query = f"""
        query {{
          heroStats {{
            matchUp(bracketBasicIds: {bracket_str}, heroIds: {json.dumps(hero_ids)}, take: 150) {{
              heroId
              vs {{
                heroId2
                synergy
                winCount
                matchCount
              }}
              with {{
                heroId2
                synergy
                winCount
                matchCount
              }}
            }}
          }}
        }}
        """
        res = self._execute_query(query, custom_token=custom_token)
        matchup_list = res.get("data", {}).get("heroStats", {}).get("matchUp", [])

        for item in matchup_list:
            h_id = item["heroId"]
            vs_dict = {}
            for vs_entry in item.get("vs", []):
                vs_dict[vs_entry["heroId2"]] = {
                    "synergy": float(vs_entry.get("synergy") or 0.0),
                    "winCount": vs_entry.get("winCount", 0),
                    "matchCount": vs_entry.get("matchCount", 0)
                }

            with_dict = {}
            for with_entry in item.get("with", []):
                with_dict[with_entry["heroId2"]] = {
                    "synergy": float(with_entry.get("synergy") or 0.0),
                    "winCount": with_entry.get("winCount", 0),
                    "matchCount": with_entry.get("matchCount", 0)
                }

            self.matchups[h_id] = {
                "vs": vs_dict,
                "with": with_dict
            }

        self._save_disk_cache()

    def ensure_matchups(self, hero_ids: list, bracket_key: str = "LOW_RANK", custom_token: str = None):
        """Ensures that the given hero IDs have their matchup data cached."""
        missing = [h_id for h_id in hero_ids if h_id not in self.matchups]
        if missing:
            print(f"Fetching matchups for missing heroes: {missing}")
            self.fetch_matchups_batch(missing, bracket_key=bracket_key, custom_token=custom_token)

    def fetch_durations(self, bracket_key: str = "LOW_RANK", custom_token: str = None, force_refresh: bool = False):
        """Fetches minute-by-minute stats for all heroes from Stratz GraphQL API and computes power curves."""
        if len(self.hero_durations) >= 120 and not force_refresh:
            return

        brackets = BRACKET_CONFIGS.get(bracket_key, BRACKET_CONFIGS["LOW_RANK"])
        bracket_str = f"[{', '.join(brackets)}]"

        query = f"""
        query {{
          heroStats {{
            stats(bracketBasicIds: {bracket_str}, groupByTime: true, minTime: 0, maxTime: 65) {{
              heroId
              time
              matchCount
              winCount
              networth
              heroDamage
              kills
              deaths
            }}
          }}
        }}
        """
        res = self._execute_query(query, custom_token=custom_token)
        stats_list = res.get("data", {}).get("heroStats", {}).get("stats", [])
        if not stats_list:
            print("Failed to fetch hero duration stats from Stratz.")
            return

        # Group by heroId
        hero_raw = {}
        for item in stats_list:
            hid = item["heroId"]
            if hid not in hero_raw:
                hero_raw[hid] = {}
            hero_raw[hid][item["time"]] = item

        # Global benchmarks per minute
        global_avg_nw = {}
        global_avg_dmg = {}
        for m in range(0, 66):
            nw_vals = [hero_raw[hid][m]["networth"] for hid in hero_raw if m in hero_raw[hid] and hero_raw[hid][m].get("networth")]
            dmg_vals = [hero_raw[hid][m]["heroDamage"] for hid in hero_raw if m in hero_raw[hid] and hero_raw[hid][m].get("heroDamage")]
            global_avg_nw[m] = sum(nw_vals) / len(nw_vals) if nw_vals else 1.0
            global_avg_dmg[m] = sum(dmg_vals) / len(dmg_vals) if dmg_vals else 1.0

        for hid, minute_map in hero_raw.items():
            m0 = minute_map.get(0) or minute_map.get(min(minute_map.keys()))
            base_matches = m0["matchCount"] if m0 else 0
            base_wins = m0["winCount"] if m0 else 0
            base_wr = (base_wins / base_matches * 100) if base_matches > 0 else 50.0

            points = []
            for m in range(0, 61):
                cur = minute_map.get(m)
                if not cur:
                    closest_m = min(minute_map.keys(), key=lambda k: abs(k - m))
                    cur = minute_map[closest_m]

                cumul_matches = cur["matchCount"]
                cumul_wins = cur["winCount"]
                cumul_wr = (cumul_wins / cumul_matches * 100) if cumul_matches > 0 else base_wr

                m_start = max(0, m - 2)
                m_end = min(65, m + 2)
                cur_start = minute_map.get(m_start, cur)
                cur_end = minute_map.get(m_end, cur)

                ended_matches = cur_start["matchCount"] - cur_end["matchCount"]
                ended_wins = cur_start["winCount"] - cur_end["winCount"]

                if ended_matches >= 80:
                    finish_wr = (ended_wins / ended_matches * 100)
                else:
                    avg_nw = global_avg_nw.get(m, 1.0)
                    avg_dmg = global_avg_dmg.get(m, 1.0)
                    hero_nw = cur.get("networth", 0)
                    hero_dmg = cur.get("heroDamage", 0)
                    nw_ratio = (hero_nw / avg_nw) if avg_nw > 0 else 1.0
                    dmg_ratio = (hero_dmg / avg_dmg) if avg_dmg > 0 else 1.0
                    early_strength_bias = ((nw_ratio - 1.0) * 1.5 + (dmg_ratio - 1.0) * 1.5)
                    weight = max(0.0, min(1.0, (20 - m) / 20))
                    finish_wr = (base_wr + early_strength_bias) * weight + cumul_wr * (1 - weight)

                delta_wr = round(finish_wr - base_wr, 2)
                points.append({
                    "minute": m,
                    "cumulWinRate": round(cumul_wr, 2),
                    "finishWinRate": round(finish_wr, 2),
                    "deltaWinRate": delta_wr,
                    "networth": round(cur.get("networth", 0), 1),
                    "heroDamage": round(cur.get("heroDamage", 0), 1)
                })

            peak_pt = max(points, key=lambda p: p["deltaWinRate"])
            trough_pt = min(points, key=lambda p: p["deltaWinRate"])

            self.hero_durations[hid] = {
                "heroId": hid,
                "baseWinRate": round(base_wr, 2),
                "totalMatches": base_matches,
                "peakMinute": peak_pt["minute"],
                "peakDelta": peak_pt["deltaWinRate"],
                "troughMinute": trough_pt["minute"],
                "troughDelta": trough_pt["deltaWinRate"],
                "points": points
            }

        self._save_disk_cache()
        print(f"[StratzClient] Successfully fetched and cached real duration curves for {len(self.hero_durations)} heroes.")

    def preload_all_matchups_async(self, bracket_key: str = "LOW_RANK", custom_token: str = None, force_refresh: bool = False):
        """Background worker to download the entire Dota 2 matchup matrix in batches of 25 heroes."""
        if self.is_preloading:
            return

        def _worker():
            self.is_preloading = True
            if not self.heroes:
                self.fetch_heroes()

            # Ensure duration curves from Stratz are present
            if len(self.hero_durations) < 120 or force_refresh:
                print("[Preloader] Updating hero duration curves from Stratz API...")
                try:
                    self.fetch_durations(bracket_key=bracket_key, custom_token=custom_token, force_refresh=force_refresh)
                except Exception as ex:
                    print(f"[Preloader] Error fetching duration curves: {ex}")

            all_hero_ids = list(self.heroes.keys())
            total = len(all_hero_ids)
            batch_size = 25
            print(f"[Preloader] Starting preloading {total} heroes in background (force_refresh={force_refresh})...")

            for i in range(0, total, batch_size):
                batch = all_hero_ids[i:i + batch_size]
                needed = batch if force_refresh else [h_id for h_id in batch if h_id not in self.matchups]
                if needed:
                    self.fetch_matchups_batch(needed, bracket_key=bracket_key, custom_token=custom_token)
                self.preload_progress = min(100, int((i + len(batch)) / total * 100))
                time.sleep(0.5)

            self.is_preloading = False
            self.preload_progress = 100
            print("[Preloader] Preloading complete! 100% of heroes are cached.")

        thread = threading.Thread(target=_worker, daemon=True)
        thread.start()

    def is_hero_viable_for_position(self, hero_id: int, pos_key: str, allow_off_meta: bool = True) -> tuple[bool, bool, float]:
        """
        Determines if a hero fits a role.
        Returns: (is_allowed, is_off_meta, role_share_pct)
        """
        if pos_key == "all":
            return True, False, 100.0

        pos_str = POSITION_MAP.get(pos_key)
        if not pos_str:
            return True, False, 100.0

        stat = self.position_stats.get((hero_id, pos_str))
        pos_matches = stat["matchCount"] if stat else 0

        # Total matches for hero across all roles
        total_matches = sum(
            self.position_stats.get((hero_id, p), {}).get("matchCount", 0)
            for p in POSITION_MAP.values()
        )

        share = (pos_matches / total_matches) if total_matches > 0 else 0.0
        share_pct = round(share * 100, 1)

        # Standard role: at least 15% of hero's games or 2000+ games in this position
        is_standard = (share >= 0.15 or pos_matches >= 2000)

        # Viable off-meta: at least 4% of hero's games and 150+ games (e.g. carry Furion, mid Rubick)
        is_viable_off_meta = (share >= 0.04 and pos_matches >= 150)

        if is_standard:
            return True, False, share_pct
        elif is_viable_off_meta and allow_off_meta:
            return True, True, share_pct
        else:
            return False, True, share_pct

    def get_hero_primary_position(self, hero_id: int) -> str:
        """Returns the most played position key ('pos1'..'pos5') for a hero based on cached stats."""
        best_pos = "pos1"
        max_matches = -1
        for pos_key, pos_str in POSITION_MAP.items():
            stat = self.position_stats.get((hero_id, pos_str))
            if stat and stat.get("matchCount", 0) > max_matches:
                max_matches = stat["matchCount"]
                best_pos = pos_key
        return best_pos

    def calculate_recommendations(
        self,
        allies: list[int],
        enemies: list[int],
        bans: list[int],
        weights: dict = None,
        role: str = "all",
        allow_off_meta: bool = True,
        bracket_key: str = "LOW_RANK",
        enemies_roles: list[dict] = None,
        use_role_weights: bool = True,
        allies_roles: list[dict] = None
    ) -> list[dict]:
        """
        Calculates draft recommendations based on custom weights:
        - counter_weight (default 70%)
        - synergy_weight (default 20%)
        - meta_weight (default 10%)
        - enemies_roles and use_role_weights (Variant 3: prioritize lane opponents and core matchups)
        - allies_roles & lane_score: early-game laning advantage against lane opponents and synergy with lane partner
        """
        if weights is None:
            weights = {"counter": 100, "synergy": 50, "meta": 25}

        w_c = max(0.0, float(weights.get("counter", 100)))
        w_s = max(0.0, float(weights.get("synergy", 50)))
        w_m = max(0.0, float(weights.get("meta", 25)))

        # Ensure matchups for all drafted heroes are in cache
        needed_heroes = set(allies + enemies)
        self.ensure_matchups(list(needed_heroes), bracket_key=bracket_key)

        # Excluded heroes
        taken_heroes = set(allies + enemies + bans)

        # Adjust weights dynamically if no enemies or no allies
        eff_wc = w_c if enemies else 0.0
        eff_ws = w_s if allies else 0.0
        eff_wm = w_m

        total_weight = eff_wc + eff_ws + eff_wm
        if total_weight > 0:
            norm_wc = eff_wc / total_weight
            norm_ws = eff_ws / total_weight
            norm_wm = eff_wm / total_weight
        else:
            norm_wc, norm_ws, norm_wm = 0.7, 0.2, 0.1

        # Map of enemy_id -> role_key ('pos1'..'pos5')
        enemy_roles_dict = {}
        if enemies_roles and isinstance(enemies_roles, list):
            for er in enemies_roles:
                if isinstance(er, dict) and "id" in er and "role" in er:
                    enemy_roles_dict[er["id"]] = er["role"]
        for e_id in enemies:
            if e_id not in enemy_roles_dict:
                enemy_roles_dict[e_id] = self.get_hero_primary_position(e_id)

        # Map of ally_id -> role_key ('pos1'..'pos5')
        ally_roles_dict = {}
        if allies_roles and isinstance(allies_roles, list):
            for ar in allies_roles:
                if isinstance(ar, dict) and "id" in ar and "role" in ar:
                    ally_roles_dict[ar["id"]] = ar["role"]
        for a_id in allies:
            if a_id not in ally_roles_dict:
                ally_roles_dict[a_id] = self.get_hero_primary_position(a_id)

        weights_table = ROLE_MATCHUP_WEIGHTS.get(role, ROLE_MATCHUP_WEIGHTS["all"])

        candidates = []

        for h_id, hero in self.heroes.items():
            if h_id in taken_heroes:
                continue

            # Role filter check
            allowed, is_off_meta, role_share = self.is_hero_viable_for_position(h_id, role, allow_off_meta=allow_off_meta)
            if not allowed:
                continue

            # 1. Counter Score Calculation (Variant 3: Role-weighted matchup calculation)
            counter_advantages = []
            counter_weights = []
            counter_breakdown = []

            for enemy_id in enemies:
                enemy_matchup = self.matchups.get(enemy_id, {}).get("vs", {})
                entry = enemy_matchup.get(h_id)

                if entry:
                    # Enemy's synergy vs H is positive when Enemy counters H.
                    # Therefore, H's advantage over Enemy is -entry['synergy']
                    h_advantage = -entry["synergy"]
                    m_count = entry.get("matchCount", 0)
                    w_count = entry.get("winCount", 0)
                    # H winrate vs Enemy
                    h_wr = round((1.0 - (w_count / m_count)) * 100, 1) if m_count > 0 else 50.0
                else:
                    h_advantage = 0.0
                    h_wr = 50.0

                enemy_pos = enemy_roles_dict.get(enemy_id) or self.get_hero_primary_position(enemy_id)
                w_enemy = weights_table.get(enemy_pos, 1.0) if use_role_weights else 1.0

                counter_advantages.append(h_advantage)
                counter_weights.append(w_enemy)
                counter_breakdown.append({
                    "enemyId": enemy_id,
                    "enemyName": self.heroes.get(enemy_id, {}).get("displayName", f"Hero {enemy_id}"),
                    "enemyShortName": self.heroes.get(enemy_id, {}).get("shortName", ""),
                    "advantage": round(h_advantage, 2),
                    "winRate": h_wr,
                    "enemyRole": enemy_pos,
                    "roleWeight": w_enemy
                })

            if counter_advantages:
                weighted_sum = sum(w * adv for w, adv in zip(counter_weights, counter_advantages))
                total_w = sum(counter_weights)
                avg_advantage = (weighted_sum / total_w) if total_w > 0 else 0.0
                min_advantage = min(counter_advantages)

                # Combined:
                # Role-weighted average incorporates lane priorities and cores,
                # while worst-case penalty ensures critical counterpicks are not masked.
                if min_advantage < 0:
                    counter_score = 0.70 * avg_advantage + 0.30 * min_advantage
                else:
                    counter_score = 0.85 * avg_advantage + 0.15 * min_advantage
            else:
                counter_score = 0.0
                min_advantage = 0.0

            # 2. Synergy Score Calculation
            synergy_values = []
            synergy_breakdown = []

            for ally_id in allies:
                ally_matchup = self.matchups.get(ally_id, {}).get("with", {})
                entry = ally_matchup.get(h_id)

                if entry:
                    h_syn = entry["synergy"]
                    m_count = entry.get("matchCount", 0)
                    w_count = entry.get("winCount", 0)
                    h_wr = round((w_count / m_count) * 100, 1) if m_count > 0 else 50.0
                else:
                    h_syn = 0.0
                    h_wr = 50.0

                synergy_values.append(h_syn)
                synergy_breakdown.append({
                    "allyId": ally_id,
                    "allyName": self.heroes.get(ally_id, {}).get("displayName", f"Hero {ally_id}"),
                    "allyShortName": self.heroes.get(ally_id, {}).get("shortName", ""),
                    "synergy": round(h_syn, 2),
                    "winRate": h_wr
                })

            synergy_score = (sum(synergy_values) / len(synergy_values)) if synergy_values else 0.0

            # 3. Meta Score Calculation
            # Position-specific winrate if role chosen, else overall winrate
            pos_str = POSITION_MAP.get(role) if role != "all" else None
            if pos_str and (h_id, pos_str) in self.position_stats:
                base_wr = self.position_stats[(h_id, pos_str)]["winRate"]
                pos_matches = self.position_stats[(h_id, pos_str)]["matchCount"]
            else:
                base_wr = self.hero_totals.get(h_id, {}).get("winRate", 50.0)
                pos_matches = self.hero_totals.get(h_id, {}).get("matchCount", 0)

            # Meta score is winrate relative to 50%
            meta_score = (base_wr - 50.0)

            # 4. Lane Advantage Calculation (Линия)
            effective_lane_role = role if role != "all" else self.get_hero_primary_position(h_id)
            lane_cfg = LANE_CONFIG.get(effective_lane_role)
            lane_score = None
            lane_breakdown = None

            if lane_cfg:
                target_opponents = lane_cfg.get("opponents", {})
                target_partner = lane_cfg.get("partner")

                # Opponents on this lane
                lane_opponents = []
                for enemy_id in enemies:
                    e_pos = enemy_roles_dict.get(enemy_id) or self.get_hero_primary_position(enemy_id)
                    if e_pos in target_opponents:
                        base_w = target_opponents[e_pos]
                        enemy_matchup = self.matchups.get(enemy_id, {}).get("vs", {})
                        entry = enemy_matchup.get(h_id)
                        h_adv = -entry["synergy"] if entry else 0.0
                        m_count = entry.get("matchCount", 0) if entry else 0
                        w_count = entry.get("winCount", 0) if entry else 0
                        h_wr = round((1.0 - (w_count / m_count)) * 100, 1) if m_count > 0 else 50.0

                        lane_opponents.append({
                            "enemyId": enemy_id,
                            "enemyName": self.heroes.get(enemy_id, {}).get("displayName", f"Hero {enemy_id}"),
                            "role": e_pos,
                            "advantage": round(h_adv, 2),
                            "winRate": h_wr,
                            "weight": base_w
                        })

                # Partner on this lane
                lane_partner = None
                if target_partner:
                    for ally_id in allies:
                        a_pos = ally_roles_dict.get(ally_id) or self.get_hero_primary_position(ally_id)
                        if a_pos == target_partner:
                            ally_matchup = self.matchups.get(ally_id, {}).get("with", {})
                            entry = ally_matchup.get(h_id)
                            h_syn = entry["synergy"] if entry else 0.0
                            m_count = entry.get("matchCount", 0) if entry else 0
                            w_count = entry.get("winCount", 0) if entry else 0
                            h_wr = round((w_count / m_count) * 100, 1) if m_count > 0 else 50.0

                            lane_partner = {
                                "allyId": ally_id,
                                "allyName": self.heroes.get(ally_id, {}).get("displayName", f"Hero {ally_id}"),
                                "role": a_pos,
                                "synergy": round(h_syn, 2),
                                "winRate": h_wr
                            }
                            break

                opp_avg = None
                if lane_opponents:
                    lane_opponents.sort(key=lambda x: x["weight"], reverse=True)
                    tot_w = sum(op["weight"] for op in lane_opponents)
                    opp_avg = sum(op["weight"] * op["advantage"] for op in lane_opponents) / tot_w if tot_w > 0 else 0.0

                partner_syn = lane_partner["synergy"] if lane_partner else None

                if opp_avg is not None and partner_syn is not None:
                    lane_score = round(0.70 * opp_avg + 0.30 * partner_syn, 2)
                elif opp_avg is not None:
                    lane_score = round(opp_avg, 2)
                elif partner_syn is not None:
                    lane_score = round(partner_syn, 2)
                else:
                    lane_score = None

                if lane_score is not None or lane_opponents or lane_partner:
                    lane_breakdown = {
                        "role": effective_lane_role,
                        "laneName": lane_cfg.get("name", "Линия"),
                        "opponents": lane_opponents,
                        "partner": lane_partner
                    }

            # 5. Final Weighted Score
            total_score = (norm_wc * counter_score) + (norm_ws * synergy_score) + (norm_wm * meta_score)

            # Sort breakdowns for nice presentation (best counter first)
            counter_breakdown.sort(key=lambda x: x["advantage"], reverse=True)
            synergy_breakdown.sort(key=lambda x: x["synergy"], reverse=True)

            candidates.append({
                "id": h_id,
                "displayName": hero["displayName"],
                "shortName": hero["shortName"],
                "iconUrl": hero["iconUrl"],
                "vertUrl": hero["vertUrl"],
                "attribute": hero["attribute"],
                "roles": hero["roles"],
                "isOffMeta": is_off_meta,
                "roleShare": role_share,
                "baseWinRate": base_wr,
                "posMatches": pos_matches,
                "counterScore": round(counter_score, 2),
                "worstAdvantage": round(min_advantage, 2) if counter_advantages else 0.0,
                "synergyScore": round(synergy_score, 2),
                "laneScore": lane_score,
                "laneBreakdown": lane_breakdown,
                "metaScore": round(meta_score, 2),
                "totalScore": round(total_score, 2),
                "counterBreakdown": counter_breakdown,
                "synergyBreakdown": synergy_breakdown
            })

        # Sort candidate heroes by total weighted score descending
        candidates.sort(key=lambda x: x["totalScore"], reverse=True)
        return candidates

    def get_team_recommendations_matrix(
        self,
        allies: list[int],
        enemies: list[int],
        bans: list[int],
        weights: dict = None,
        allow_off_meta: bool = True,
        bracket_key: str = "LOW_RANK",
        enemies_roles: list[dict] = None,
        use_role_weights: bool = True,
        allies_roles: list[dict] = None
    ) -> dict:
        """
        Returns top picks for ALL 5 positions simultaneously,
        so the user can immediately advise each friend according to their role!
        """
        matrix = {}
        for role_key in ["pos1", "pos2", "pos3", "pos4", "pos5"]:
            recs = self.calculate_recommendations(
                allies=allies,
                enemies=enemies,
                bans=bans,
                weights=weights,
                role=role_key,
                allow_off_meta=allow_off_meta,
                bracket_key=bracket_key,
                enemies_roles=enemies_roles,
                use_role_weights=use_role_weights,
                allies_roles=allies_roles
            )
            matrix[role_key] = recs[:50]  # Return top 50 so client can search across all viable picks
        return matrix

    def _get_empty_timeline(self) -> dict:
        """Returns balanced empty timeline (0 to 60 min) when no heroes are drafted."""
        points = []
        for m in [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60]:
            if m <= 10:
                stage = "Линии"
                stage_key = "laning"
            elif m <= 20:
                stage = "Тайминги"
                stage_key = "timings"
            elif m <= 35:
                stage = "Мидгейм"
                stage_key = "midgame"
            elif m <= 50:
                stage = "Лейтгейм"
                stage_key = "lategame"
            else:
                stage = "Ультра-лейт"
                stage_key = "ultralate"

            points.append({
                "minute": m,
                "alliesAdvantage": 0.0,
                "alliesWinRate": 50.0,
                "enemiesWinRate": 50.0,
                "stage": stage,
                "stageKey": stage_key
            })

        return {
            "points": points,
            "peakAlly": {"minute": 30, "advantage": 0.0, "winRate": 50.0, "stage": "Мидгейм"},
            "peakEnemy": {"minute": 30, "advantage": 0.0, "winRate": 50.0, "stage": "Мидгейм"},
            "peakSide": "equal",
            "laningAdvantage": 0.0,
            "midgameAdvantage": 0.0,
            "lateGameAdvantage": 0.0,
            "ultraLateAdvantage": 0.0,
            "timingAdvice": "Выберите героев союзников и врагов, чтобы увидеть прогноз преимущества по минутам."
        }

    def get_hero_timing_profile(self, hero_id: int, role: str = None) -> list[float]:
        """Returns hero power profile at milestones [0m, 10m, 20m, 35m, 50m, 60m] from Stratz API."""
        h_pts = self.hero_durations.get(hero_id, {}).get("points")
        if not h_pts:
            return [1.0, 1.0, 1.0, 1.0, 1.0, 1.0]
        milestones = [0, 10, 20, 35, 50, 60]
        base_wr = self.hero_durations.get(hero_id, {}).get("baseWinRate", 50.0) or 50.0
        return [
            round(1.0 + (h_pts[m]["deltaWinRate"] / base_wr), 3) if len(h_pts) > m else 1.0
            for m in milestones
        ]

    def calculate_timeline_advantage(
        self,
        allies: list[int],
        enemies: list[int],
        allies_roles: list[dict] = None,
        enemies_roles: list[dict] = None,
        net_adv: float = 0.0,
        avg_counter_adv: float = 0.0,
        synergy_adv: float = 0.0
    ) -> dict:
        """
        Calculates expected team advantage progression from minute 0 to 60
        directly from real Stratz duration statistics and match winrates.
        """
        allies = [int(x) for x in allies if x is not None]
        enemies = [int(x) for x in enemies if x is not None]

        if not allies and not enemies:
            return self._get_empty_timeline()

        # Map roles
        ally_roles_dict = {}
        if allies_roles and isinstance(allies_roles, list):
            for ar in allies_roles:
                if isinstance(ar, dict) and "id" in ar and "role" in ar:
                    ally_roles_dict[ar["id"]] = ar["role"]

        enemy_roles_dict = {}
        if enemies_roles and isinstance(enemies_roles, list):
            for er in enemies_roles:
                if isinstance(er, dict) and "id" in er and "role" in er:
                    enemy_roles_dict[er["id"]] = er["role"]

        # Laning matchup advantage (Safe, Mid, Offlane) from direct counter matchups
        lane_adv = 0.0
        if allies and enemies:
            lane_scores = []
            for lane_role, weight in [("pos1", 0.35), ("pos2", 0.35), ("pos3", 0.30)]:
                cfg = LANE_CONFIG.get(lane_role, {})
                ally_hero = next((a for a in allies if ally_roles_dict.get(a) == lane_role or self.get_hero_primary_position(a) == lane_role), None)
                if ally_hero:
                    opps = cfg.get("opponents", {})
                    for enemy_hero in enemies:
                        e_role = enemy_roles_dict.get(enemy_hero) or self.get_hero_primary_position(enemy_hero)
                        if e_role in opps:
                            w = opps[e_role]
                            matchup = self.matchups.get(ally_hero, {}).get("vs", {}).get(enemy_hero)
                            if matchup:
                                lane_scores.append(matchup.get("synergy", 0.0) * weight * w)
            if lane_scores:
                lane_adv = sum(lane_scores) / len(lane_scores)

        sample_minutes = [0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60]
        points = []

        for m in sample_minutes:
            # Real Stratz deltaWinRate for picked heroes at minute m
            ally_deltas = []
            for a in allies:
                h_pts = self.hero_durations.get(a, {}).get("points")
                if h_pts and len(h_pts) > m:
                    ally_deltas.append(h_pts[m]["deltaWinRate"])
                else:
                    ally_deltas.append(0.0)

            enemy_deltas = []
            for e in enemies:
                h_pts = self.hero_durations.get(e, {}).get("points")
                if h_pts and len(h_pts) > m:
                    enemy_deltas.append(h_pts[m]["deltaWinRate"])
                else:
                    enemy_deltas.append(0.0)

            avg_a_delta = (sum(ally_deltas) / len(ally_deltas)) if ally_deltas else 0.0
            avg_e_delta = (sum(enemy_deltas) / len(enemy_deltas)) if enemy_deltas else 0.0

            if allies and enemies:
                timing_diff = avg_a_delta - avg_e_delta
            elif allies:
                timing_diff = avg_a_delta
            else:
                timing_diff = -avg_e_delta

            # Laning impact: strong in early minutes, smoothly transitions out by minute 15
            if m <= 10:
                lane_fade = 1.0 - 0.2 * (m / 10.0)
            elif m <= 15:
                lane_fade = 0.8 * (15.0 - m) / 5.0
            else:
                lane_fade = 0.0
            lane_contrib = lane_adv * lane_fade * 1.5

            total_adv = net_adv + timing_diff + lane_contrib
            allies_wr = max(15.0, min(85.0, 50.0 + total_adv))
            enemies_wr = 100.0 - allies_wr

            if m <= 10:
                stage = "Линии"
                stage_key = "laning"
            elif m <= 35:
                stage = "Мидгейм"
                stage_key = "midgame"
            elif m <= 50:
                stage = "Лейтгейм"
                stage_key = "lategame"
            else:
                stage = "Ультра-лейт"
                stage_key = "ultralate"

            points.append({
                "minute": m,
                "alliesAdvantage": round(total_adv, 1),
                "alliesWinRate": round(allies_wr, 1),
                "enemiesWinRate": round(enemies_wr, 1),
                "stage": stage,
                "stageKey": stage_key
            })

        best_ally_pt = max(points, key=lambda x: x["alliesAdvantage"])
        worst_ally_pt = min(points, key=lambda x: x["alliesAdvantage"])

        peak_ally = {
            "minute": best_ally_pt["minute"],
            "advantage": best_ally_pt["alliesAdvantage"],
            "winRate": best_ally_pt["alliesWinRate"],
            "stage": best_ally_pt["stage"]
        }
        peak_enemy = {
            "minute": worst_ally_pt["minute"],
            "advantage": round(-worst_ally_pt["alliesAdvantage"], 1),
            "winRate": worst_ally_pt["enemiesWinRate"],
            "stage": worst_ally_pt["stage"]
        }

        laning_pts = [p["alliesAdvantage"] for p in points if p["minute"] <= 10]
        mid_pts = [p["alliesAdvantage"] for p in points if 10 < p["minute"] <= 35]
        late_pts = [p["alliesAdvantage"] for p in points if 35 < p["minute"] <= 50]
        ultra_pts = [p["alliesAdvantage"] for p in points if p["minute"] > 50]

        laning_adv = round(sum(laning_pts) / len(laning_pts), 1) if laning_pts else 0.0
        mid_adv = round(sum(mid_pts) / len(mid_pts), 1) if mid_pts else 0.0
        late_adv = round(sum(late_pts) / len(late_pts), 1) if late_pts else 0.0
        ultra_adv = round(sum(ultra_pts) / len(ultra_pts), 1) if ultra_pts else 0.0

        # Smart timing insight with hero power spikes from real Stratz data
        best_hero_name = None
        if allies:
            def ally_spike(a):
                pts = self.hero_durations.get(a, {}).get("points")
                return pts[best_ally_pt["minute"]]["deltaWinRate"] if (pts and len(pts) > best_ally_pt["minute"]) else 0.0
            best_a = max(allies, key=ally_spike)
            best_hero_name = self.heroes.get(best_a, {}).get("displayName")

        worst_hero_name = None
        if enemies:
            def enemy_spike(e):
                pts = self.hero_durations.get(e, {}).get("points")
                return pts[worst_ally_pt["minute"]]["deltaWinRate"] if (pts and len(pts) > worst_ally_pt["minute"]) else 0.0
            worst_e = max(enemies, key=enemy_spike)
            worst_hero_name = self.heroes.get(worst_e, {}).get("displayName")

        if best_ally_pt["alliesAdvantage"] >= worst_ally_pt["alliesAdvantage"] + 2.5:
            hero_suffix = f" (пик силы: {best_hero_name})" if best_hero_name else ""
            if best_ally_pt["minute"] <= 20:
                advice = f"Пик силы нашей команды: {best_ally_pt['minute']} мин (+{best_ally_pt['alliesAdvantage']}%){hero_suffix}. Закрывайте игру до 30-35 минуты!"
            elif best_ally_pt["minute"] <= 35:
                advice = f"Пик силы: {best_ally_pt['minute']} мин (+{best_ally_pt['alliesAdvantage']}%){hero_suffix}. Оптимальное окно для Рошана и осады базы."
            else:
                advice = f"Доминация в поздней игре: пик силы на {best_ally_pt['minute']} мин (+{best_ally_pt['alliesAdvantage']}%){hero_suffix}. Затягивайте в лейт!"
        elif worst_ally_pt["alliesAdvantage"] <= -2.5:
            e_hero_suffix = f" (давление от {worst_hero_name})" if worst_hero_name else ""
            if worst_ally_pt["minute"] <= 20:
                advice = f"Опасная ранняя игра (враг +{-worst_ally_pt['alliesAdvantage']}% на {worst_ally_pt['minute']} мин){e_hero_suffix}. Фармите и избегайте стычек!"
            else:
                advice = f"Враг имеет перевес в лейте (на {worst_ally_pt['minute']} мин +{-worst_ally_pt['alliesAdvantage']}%){e_hero_suffix}. Забирайте объекты раньше!"
        else:
            advice = "Ровный баланс сил на всех стадиях (~50%). Исход решат тимфайты и ключевые тайминги артефактов."

        peak_side = "allies" if best_ally_pt["alliesAdvantage"] > 2.0 else ("enemies" if worst_ally_pt["alliesAdvantage"] < -2.0 else "equal")

        return {
            "points": points,
            "peakAlly": peak_ally,
            "peakEnemy": peak_enemy,
            "peakSide": peak_side,
            "laningAdvantage": laning_adv,
            "midgameAdvantage": mid_adv,
            "lateGameAdvantage": late_adv,
            "ultraLateAdvantage": ultra_adv,
            "timingAdvice": advice
        }

    def _get_empty_hero_pick_scores(self) -> dict:
        """Returns empty default template for 5 ally slots and 5 enemy slots."""
        allies_empty = []
        enemies_empty = []
        for i in range(5):
            role_k = f"pos{i+1}"
            allies_empty.append({
                "slotIndex": i,
                "heroId": None,
                "displayName": None,
                "role": role_k,
                "roleLabel": POSITION_LABELS.get(role_k, f"Поз {i+1}"),
                "team": "allies",
                "score": None,
                "status": "Ожидание",
                "statusClass": "empty",
                "teammateSynergies": [],
                "opponentMatchups": []
            })
            enemies_empty.append({
                "slotIndex": i,
                "heroId": None,
                "displayName": None,
                "role": role_k,
                "roleLabel": POSITION_LABELS.get(role_k, f"Поз {i+1}"),
                "team": "enemies",
                "score": None,
                "status": "Ожидание",
                "statusClass": "empty",
                "teammateSynergies": [],
                "opponentMatchups": []
            })
        return {
            "allies": allies_empty,
            "enemies": enemies_empty,
            "alliesAvgScore": None,
            "enemiesAvgScore": None,
            "detailedBreakdown": []
        }

    def calculate_hero_pick_scores(
        self,
        allies: list[int],
        enemies: list[int],
        allies_roles: list[dict] = None,
        enemies_roles: list[dict] = None,
        bracket_key: str = "LOW_RANK"
    ) -> dict:
        """
        Calculates 100-point individual pick strength scores for each hero in the draft,
        including pairwise teammate synergy and individual enemy counterpick deltas.
        """
        allies_clean = [int(x) for x in allies if x is not None]
        enemies_clean = [int(x) for x in enemies if x is not None]

        needed = set(allies_clean + enemies_clean)
        if needed:
            self.ensure_matchups(list(needed), bracket_key=bracket_key)

        # Build role maps
        ally_roles_map = {}
        if allies_roles and isinstance(allies_roles, list):
            for idx, item in enumerate(allies_roles):
                if isinstance(item, dict):
                    h_id = item.get("id")
                    r = item.get("role") or f"pos{idx+1}"
                    if h_id is not None:
                        ally_roles_map[int(h_id)] = r
                elif isinstance(item, str) and idx < len(allies_clean):
                    ally_roles_map[allies_clean[idx]] = item

        enemy_roles_map = {}
        if enemies_roles and isinstance(enemies_roles, list):
            for idx, item in enumerate(enemies_roles):
                if isinstance(item, dict):
                    h_id = item.get("id")
                    r = item.get("role") or f"pos{idx+1}"
                    if h_id is not None:
                        enemy_roles_map[int(h_id)] = r
                elif isinstance(item, str) and idx < len(enemies_clean):
                    enemy_roles_map[enemies_clean[idx]] = item

        def evaluate_hero(hero_id: int, role: str, team_side: str) -> dict:
            if not hero_id or hero_id not in self.heroes:
                return None

            hero_info = self.heroes[hero_id]
            is_ally = (team_side == "allies")
            teammates = [a for a in allies_clean if a != hero_id] if is_ally else [e for e in enemies_clean if e != hero_id]
            opponents = enemies_clean if is_ally else allies_clean

            # Pairwise synergies with teammates
            teammate_synergies = []
            for t_id in teammates:
                t_info = self.heroes.get(t_id, {})
                s1 = self.matchups.get(hero_id, {}).get("with", {}).get(t_id, {}).get("synergy")
                s2 = self.matchups.get(t_id, {}).get("with", {}).get(hero_id, {}).get("synergy")
                syn = ((s1 + s2) / 2.0) if (s1 is not None and s2 is not None) else (s1 if s1 is not None else (s2 if s2 is not None else 0.0))
                teammate_synergies.append({
                    "heroId": t_id,
                    "displayName": t_info.get("displayName", f"Hero {t_id}"),
                    "shortName": t_info.get("shortName", ""),
                    "iconUrl": t_info.get("iconUrl", ""),
                    "synergy": round(syn, 2)
                })
            teammate_synergies.sort(key=lambda x: x["synergy"], reverse=True)

            # Pairwise matchups against opponents
            opponent_matchups = []
            for o_id in opponents:
                o_info = self.heroes.get(o_id, {})
                adv1 = self.matchups.get(hero_id, {}).get("vs", {}).get(o_id, {}).get("synergy")
                adv2 = self.matchups.get(o_id, {}).get("vs", {}).get(hero_id, {}).get("synergy")
                if adv1 is not None and adv2 is not None:
                    adv_eff = (adv1 - adv2) / 2.0
                elif adv1 is not None:
                    adv_eff = adv1
                elif adv2 is not None:
                    adv_eff = -adv2
                else:
                    adv_eff = 0.0

                opponent_matchups.append({
                    "heroId": o_id,
                    "displayName": o_info.get("displayName", f"Hero {o_id}"),
                    "shortName": o_info.get("shortName", ""),
                    "iconUrl": o_info.get("iconUrl", ""),
                    "advantage": round(adv_eff, 2)
                })
            opponent_matchups.sort(key=lambda x: x["advantage"], reverse=True)

            avg_counter = (sum(m["advantage"] for m in opponent_matchups) / len(opponent_matchups)) if opponent_matchups else 0.0
            avg_synergy = (sum(s["synergy"] for s in teammate_synergies) / len(teammate_synergies)) if teammate_synergies else 0.0

            # Meta winrate
            pos_str = POSITION_MAP.get(role) if role else None
            if pos_str and (hero_id, pos_str) in self.position_stats and self.position_stats[(hero_id, pos_str)].get("matchCount", 0) >= 100:
                base_wr = self.position_stats[(hero_id, pos_str)]["winRate"]
            else:
                base_wr = self.hero_totals.get(hero_id, {}).get("winRate", 50.0)
            meta_delta = base_wr - 50.0

            # Weighted composite advantage
            if opponents and teammates:
                net_adv = 0.55 * avg_counter + 0.25 * avg_synergy + 0.20 * meta_delta
            elif opponents:
                net_adv = 0.70 * avg_counter + 0.30 * meta_delta
            elif teammates:
                net_adv = 0.60 * avg_synergy + 0.40 * meta_delta
            else:
                net_adv = meta_delta

            raw_score = 50.0 + (net_adv * 4.5)
            final_score = max(10, min(99, int(round(raw_score))))

            if final_score >= 80:
                status_text = "Имба-пик"
                status_class = "super"
            elif final_score >= 68:
                status_text = "Отличный пик"
                status_class = "high"
            elif final_score >= 56:
                status_text = "Хороший пик"
                status_class = "good"
            elif final_score >= 46:
                status_text = "Нейтрально"
                status_class = "neutral"
            elif final_score >= 35:
                status_text = "Сложный пик"
                status_class = "low"
            else:
                status_text = "Законтрен"
                status_class = "bad"

            return {
                "heroId": hero_id,
                "displayName": hero_info.get("displayName", f"Hero {hero_id}"),
                "shortName": hero_info.get("shortName", ""),
                "iconUrl": hero_info.get("iconUrl", ""),
                "vertUrl": hero_info.get("vertUrl", ""),
                "role": role,
                "roleLabel": POSITION_LABELS.get(role, f"Поз {role.replace('pos', '') if role else ''}"),
                "team": team_side,
                "score": final_score,
                "status": status_text,
                "statusClass": status_class,
                "netAdvantage": round(net_adv, 2),
                "counterScore": round(avg_counter, 2),
                "synergyScore": round(avg_synergy, 2),
                "metaWinRate": round(base_wr, 1),
                "teammateSynergies": teammate_synergies,
                "opponentMatchups": opponent_matchups
            }

        allies_scored = []
        for i in range(5):
            role_key = f"pos{i+1}"
            h_id = allies[i] if i < len(allies) else None
            if h_id is not None:
                h_role = ally_roles_map.get(int(h_id), role_key)
                scored = evaluate_hero(int(h_id), h_role, "allies")
                if scored:
                    scored["slotIndex"] = i
                    allies_scored.append(scored)
                    continue
            allies_scored.append({
                "slotIndex": i,
                "heroId": None,
                "displayName": None,
                "role": role_key,
                "roleLabel": POSITION_LABELS.get(role_key, f"Поз {i+1}"),
                "team": "allies",
                "score": None,
                "status": "Ожидание",
                "statusClass": "empty",
                "teammateSynergies": [],
                "opponentMatchups": []
            })

        enemies_scored = []
        for i in range(5):
            role_key = f"pos{i+1}"
            h_id = enemies[i] if i < len(enemies) else None
            if h_id is not None:
                h_role = enemy_roles_map.get(int(h_id), role_key)
                scored = evaluate_hero(int(h_id), h_role, "enemies")
                if scored:
                    scored["slotIndex"] = i
                    enemies_scored.append(scored)
                    continue
            enemies_scored.append({
                "slotIndex": i,
                "heroId": None,
                "displayName": None,
                "role": role_key,
                "roleLabel": POSITION_LABELS.get(role_key, f"Поз {i+1}"),
                "team": "enemies",
                "score": None,
                "status": "Ожидание",
                "statusClass": "empty",
                "teammateSynergies": [],
                "opponentMatchups": []
            })

        valid_ally_scores = [s["score"] for s in allies_scored if s["score"] is not None]
        valid_enemy_scores = [s["score"] for s in enemies_scored if s["score"] is not None]
        avg_ally = int(round(sum(valid_ally_scores) / len(valid_ally_scores))) if valid_ally_scores else None
        avg_enemy = int(round(sum(valid_enemy_scores) / len(valid_enemy_scores))) if valid_enemy_scores else None

        breakdown_list = [s for s in allies_scored if s["heroId"] is not None] + [s for s in enemies_scored if s["heroId"] is not None]

        return {
            "allies": allies_scored,
            "enemies": enemies_scored,
            "alliesAvgScore": avg_ally,
            "enemiesAvgScore": avg_enemy,
            "detailedBreakdown": breakdown_list
        }

    def calculate_draft_analysis(
        self,
        allies: list[int],
        enemies: list[int],
        weights: dict = None,
        bracket_key: str = "LOW_RANK",
        allies_roles: list[dict] = None,
        enemies_roles: list[dict] = None
    ) -> dict:
        """
        Calculates realistic draft win rate prediction, analytical breakdown,
        and 0-60 min expected advantage timeline.
        """
        if weights is None:
            weights = {"counter": 100, "synergy": 50, "meta": 25}

        w_c = max(0.0, float(weights.get("counter", 100)))
        w_s = max(0.0, float(weights.get("synergy", 50)))
        w_m = max(0.0, float(weights.get("meta", 25)))

        allies = [int(x) for x in allies if x is not None]
        enemies = [int(x) for x in enemies if x is not None]

        if not allies and not enemies:
            return {
                "alliesWinRate": 50.0,
                "enemiesWinRate": 50.0,
                "counterAdvantage": 0.0,
                "synergyAdvantage": 0.0,
                "metaAdvantage": 0.0,
                "bestCounters": [],
                "biggestThreats": [],
                "insight": "Выберите героев врага или союзников для получения умных рекомендаций.",
                "timeline": self._get_empty_timeline(),
                "heroPickScores": self._get_empty_hero_pick_scores()
            }

        needed_heroes = set(allies + enemies)
        self.ensure_matchups(list(needed_heroes), bracket_key=bracket_key)

        # 1. Counter (Matchup) Advantage between Allies and Enemies
        pair_advantages = []
        best_counters = []
        biggest_threats = []

        for a_id in allies:
            a_name = self.heroes.get(a_id, {}).get("displayName", f"Hero {a_id}")
            for e_id in enemies:
                e_name = self.heroes.get(e_id, {}).get("displayName", f"Hero {e_id}")

                adv_a = None
                adv_e = None
                if a_id in self.matchups and "vs" in self.matchups[a_id]:
                    entry = self.matchups[a_id]["vs"].get(e_id)
                    if entry:
                        adv_a = entry.get("synergy", 0.0)

                if e_id in self.matchups and "vs" in self.matchups[e_id]:
                    entry = self.matchups[e_id]["vs"].get(a_id)
                    if entry:
                        adv_e = -entry.get("synergy", 0.0)

                if adv_a is not None and adv_e is not None:
                    adv = (adv_a + adv_e) / 2.0
                elif adv_a is not None:
                    adv = adv_a
                elif adv_e is not None:
                    adv = adv_e
                else:
                    adv = 0.0

                pair_advantages.append((a_id, e_id, adv))

                if adv >= 0.4:
                    best_counters.append({
                        "allyId": a_id,
                        "allyName": a_name,
                        "enemyId": e_id,
                        "enemyName": e_name,
                        "advantage": round(adv, 1)
                    })
                elif adv <= -0.4:
                    biggest_threats.append({
                        "allyId": a_id,
                        "allyName": a_name,
                        "enemyId": e_id,
                        "enemyName": e_name,
                        "advantage": round(abs(adv), 1)
                    })

        best_counters.sort(key=lambda x: x["advantage"], reverse=True)
        biggest_threats.sort(key=lambda x: x["advantage"], reverse=True)

        avg_counter_adv = (sum(adv for _, _, adv in pair_advantages) / len(pair_advantages)) if pair_advantages else 0.0

        # 2. Synergies within Allies and within Enemies
        ally_syns = []
        if len(allies) >= 2:
            for i in range(len(allies)):
                for j in range(i + 1, len(allies)):
                    a1, a2 = allies[i], allies[j]
                    s1 = self.matchups.get(a1, {}).get("with", {}).get(a2, {}).get("synergy")
                    s2 = self.matchups.get(a2, {}).get("with", {}).get(a1, {}).get("synergy")
                    if s1 is not None and s2 is not None:
                        ally_syns.append((s1 + s2) / 2.0)
                    elif s1 is not None:
                        ally_syns.append(s1)
                    elif s2 is not None:
                        ally_syns.append(s2)

        avg_ally_syn = (sum(ally_syns) / len(ally_syns)) if ally_syns else 0.0

        enemy_syns = []
        if len(enemies) >= 2:
            for i in range(len(enemies)):
                for j in range(i + 1, len(enemies)):
                    e1, e2 = enemies[i], enemies[j]
                    s1 = self.matchups.get(e1, {}).get("with", {}).get(e2, {}).get("synergy")
                    s2 = self.matchups.get(e2, {}).get("with", {}).get(e1, {}).get("synergy")
                    if s1 is not None and s2 is not None:
                        enemy_syns.append((s1 + s2) / 2.0)
                    elif s1 is not None:
                        enemy_syns.append(s1)
                    elif s2 is not None:
                        enemy_syns.append(s2)

        avg_enemy_syn = (sum(enemy_syns) / len(enemy_syns)) if enemy_syns else 0.0
        synergy_adv = avg_ally_syn - avg_enemy_syn

        # 3. Meta Win Rates
        roles_dict = {}
        if allies_roles and isinstance(allies_roles, list):
            for ar in allies_roles:
                if isinstance(ar, dict) and "id" in ar and "role" in ar:
                    roles_dict[ar["id"]] = ar["role"]

        ally_wrs = []
        for a in allies:
            r = roles_dict.get(a)
            pos_str = POSITION_MAP.get(r) if r else None
            if pos_str and (a, pos_str) in self.position_stats and self.position_stats[(a, pos_str)].get("matchCount", 0) >= 100:
                ally_wrs.append(self.position_stats[(a, pos_str)]["winRate"])
            else:
                ally_wrs.append(self.hero_totals.get(a, {}).get("winRate", 50.0))

        enemy_wrs = [self.hero_totals.get(e, {}).get("winRate", 50.0) for e in enemies]
        avg_ally_wr = (sum(ally_wrs) / len(ally_wrs)) if ally_wrs else 50.0
        avg_enemy_wr = (sum(enemy_wrs) / len(enemy_wrs)) if enemy_wrs else 50.0
        meta_adv = avg_ally_wr - avg_enemy_wr

        # 4. Total Weighted Advantage with Adaptive Weights
        if allies and enemies:
            eff_wc = w_c
            eff_ws = w_s if (len(allies) >= 2 or len(enemies) >= 2) else 0.0
            eff_wm = w_m
            scale = 1.0 + 0.15 * (min(len(allies), len(enemies)) - 1)
        elif allies:
            eff_wc = 0.0
            eff_ws = w_s if len(allies) >= 2 else 0.0
            eff_wm = w_m
            scale = 1.0 + 0.1 * (len(allies) - 1)
        else:
            eff_wc = 0.0
            eff_ws = w_s if len(enemies) >= 2 else 0.0
            eff_wm = w_m
            scale = 1.0 + 0.1 * (len(enemies) - 1)

        tot_w = eff_wc + eff_ws + eff_wm
        if tot_w > 0:
            tot_adv = (eff_wc * avg_counter_adv + eff_ws * synergy_adv + eff_wm * meta_adv) / tot_w
        else:
            tot_adv = 0.0

        net_adv = tot_adv * scale
        allies_wr = max(15.0, min(85.0, 50.0 + net_adv))
        enemies_wr = 100.0 - allies_wr

        # 5. Descriptive Russian Insight
        if allies and enemies:
            diff = allies_wr - 50.0
            if allies_wr >= 53.0:
                if best_counters:
                    bc = best_counters[0]
                    insight = f"Отличный драфт! Преимущество нашей команды +{diff:.1f}%. Ключевой контрпик: {bc['allyName']} закрывает {bc['enemyName']} (+{bc['advantage']}%)."
                else:
                    insight = f"Отличный драфт! Преимущество нашей команды +{diff:.1f}% по оценке контрпиков и меты."
            elif allies_wr <= 47.0:
                if biggest_threats:
                    bt = biggest_threats[0]
                    insight = f"Предупреждение: у врага преимущество +{-diff:.1f}%. Главная угроза: {bt['enemyName']} против {bt['allyName']} (+{bt['advantage']}%). Возьмите сильные контрпики!"
                else:
                    insight = f"Предупреждение: вражеский драфт имеет преимущество (+{-diff:.1f}%). Выберите сильные контрпики из колонок!"
            else:
                if best_counters:
                    bc = best_counters[0]
                    insight = f"Баланс драфта равный (~{allies_wr:.1f}%). {bc['allyName']} закрывает {bc['enemyName']} (+{bc['advantage']}%). Следующие пики определят победителя."
                else:
                    insight = f"Баланс драфта равный (~{allies_wr:.1f}%). Подбирайте героев по рекомендованным позициям."
        elif allies:
            syn_txt = f", синергия пиков: +{avg_ally_syn:.1f}%" if len(allies) >= 2 and avg_ally_syn != 0 else ""
            insight = f"Драфт союзников: средний винрейт героев {avg_ally_wr:.1f}%{syn_txt}. Добавьте врагов для расчета контрпиков."
        else:
            insight = f"Драфт врагов: средний винрейт героев {avg_enemy_wr:.1f}%. Подберите контрпики из рекомендаций ниже."

        timeline = self.calculate_timeline_advantage(
            allies=allies,
            enemies=enemies,
            allies_roles=allies_roles,
            enemies_roles=enemies_roles,
            net_adv=net_adv,
            avg_counter_adv=avg_counter_adv,
            synergy_adv=synergy_adv
        )

        pick_scores = self.calculate_hero_pick_scores(
            allies=allies,
            enemies=enemies,
            allies_roles=allies_roles,
            enemies_roles=enemies_roles,
            bracket_key=bracket_key
        )

        return {
            "alliesWinRate": round(allies_wr, 1),
            "enemiesWinRate": round(enemies_wr, 1),
            "counterAdvantage": round(avg_counter_adv, 2),
            "synergyAdvantage": round(synergy_adv, 2),
            "alliesSynergy": round(avg_ally_syn, 2),
            "enemiesSynergy": round(avg_enemy_syn, 2),
            "metaAdvantage": round(meta_adv, 2),
            "bestCounters": best_counters[:3],
            "biggestThreats": biggest_threats[:3],
            "insight": insight,
            "timeline": timeline,
            "heroPickScores": pick_scores
        }
