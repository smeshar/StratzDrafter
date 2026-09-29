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

STRATZ_GRAPHQL_URL = "https://api.stratz.com/graphql"

# Available rank bracket configurations
BRACKET_CONFIGS = {
    "HERALD_GUARDIAN": ["HERALD_GUARDIAN"],
    "CRUSADER_ARCHON": ["CRUSADER_ARCHON"],
    "LOW_RANK": ["HERALD_GUARDIAN", "CRUSADER_ARCHON"],  # Default for low MMR
    "LEGEND_ANCIENT": ["LEGEND_ANCIENT"],
    "DIVINE_IMMORTAL": ["DIVINE_IMMORTAL"],
    "ALL": ["ALL"]
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

    def _save_disk_cache(self):
        """Saves current state to local JSON cache files."""
        try:
            with open(HEROES_CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(self.heroes, f, ensure_ascii=False, indent=2)

            pos_formatted = {f"{k[0]}:{k[1]}": v for k, v in self.position_stats.items()}
            with open(STATS_CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump({"totals": self.hero_totals, "positions": pos_formatted}, f, ensure_ascii=False, indent=2)

            matchups_serializable = {}
            for h_id, data in self.matchups.items():
                matchups_serializable[str(h_id)] = {
                    "vs": {str(k): v for k, v in data["vs"].items()},
                    "with": {str(k): v for k, v in data["with"].items()}
                }
            with open(MATCHUPS_CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(matchups_serializable, f, ensure_ascii=False)

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

    def preload_all_matchups_async(self, bracket_key: str = "LOW_RANK", custom_token: str = None, force_refresh: bool = False):
        """Background worker to download the entire Dota 2 matchup matrix in batches of 25 heroes."""
        if self.is_preloading:
            return

        def _worker():
            self.is_preloading = True
            if not self.heroes:
                self.fetch_heroes()
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

    def calculate_recommendations(
        self,
        allies: list[int],
        enemies: list[int],
        bans: list[int],
        weights: dict = None,
        role: str = "all",
        allow_off_meta: bool = True,
        bracket_key: str = "LOW_RANK"
    ) -> list[dict]:
        """
        Calculates draft recommendations based on custom weights:
        - counter_weight (default 70%)
        - synergy_weight (default 20%)
        - meta_weight (default 10%)
        """
        if weights is None:
            weights = {"counter": 70, "synergy": 20, "meta": 10}

        w_c = max(0.0, float(weights.get("counter", 70)))
        w_s = max(0.0, float(weights.get("synergy", 20)))
        w_m = max(0.0, float(weights.get("meta", 10)))

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

        candidates = []

        for h_id, hero in self.heroes.items():
            if h_id in taken_heroes:
                continue

            # Role filter check
            allowed, is_off_meta, role_share = self.is_hero_viable_for_position(h_id, role, allow_off_meta=allow_off_meta)
            if not allowed:
                continue

            # 1. Counter Score Calculation
            counter_advantages = []
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

                counter_advantages.append(h_advantage)
                counter_breakdown.append({
                    "enemyId": enemy_id,
                    "enemyName": self.heroes.get(enemy_id, {}).get("displayName", f"Hero {enemy_id}"),
                    "enemyShortName": self.heroes.get(enemy_id, {}).get("shortName", ""),
                    "advantage": round(h_advantage, 2),
                    "winRate": h_wr
                })

            counter_score = (sum(counter_advantages) / len(counter_advantages)) if counter_advantages else 0.0

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

            # 4. Final Weighted Score
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
                "synergyScore": round(synergy_score, 2),
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
        bracket_key: str = "LOW_RANK"
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
                bracket_key=bracket_key
            )
            matrix[role_key] = recs[:50]  # Return top 50 so client can search across all viable picks
        return matrix

    def calculate_draft_analysis(
        self,
        allies: list[int],
        enemies: list[int],
        weights: dict = None,
        bracket_key: str = "LOW_RANK",
        allies_roles: list[dict] = None
    ) -> dict:
        """
        Calculates realistic draft win rate prediction and analytical breakdown
        based on head-to-head counters, team synergies, and meta win rates.
        """
        if weights is None:
            weights = {"counter": 70, "synergy": 20, "meta": 10}

        w_c = max(0.0, float(weights.get("counter", 70)))
        w_s = max(0.0, float(weights.get("synergy", 20)))
        w_m = max(0.0, float(weights.get("meta", 10)))

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
                "insight": "Выберите героев врага или союзников для получения умных рекомендаций."
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
            "insight": insight
        }
