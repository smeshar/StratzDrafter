import os
import json
import webbrowser
from threading import Timer
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

from stratz_client import StratzClient, BRACKET_CONFIGS, POSITION_LABELS
from aliases import matches_search, HERO_ALIASES

load_dotenv()

app = Flask(__name__, static_folder="static", template_folder="templates")
client = StratzClient()

# Initialize data on start
print("[Server] Initializing Stratz data...")
client.fetch_heroes()
client.fetch_stats(bracket_key="LOW_RANK")
# Trigger background preload
client.preload_all_matchups_async(bracket_key="LOW_RANK")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/heroes", methods=["GET"])
def get_heroes():
    """Returns list of all heroes with localized names and aliases for fast search."""
    search_q = request.args.get("q", "").strip()
    attr_filter = request.args.get("attr", "").strip().lower()

    heroes_list = []
    for h_id, h in client.heroes.items():
        if attr_filter and attr_filter != "all" and h.get("attribute", "").lower() != attr_filter:
            continue

        if search_q:
            if not matches_search(search_q, h["name"], h["displayName"], h["shortName"]):
                continue

        hero_copy = dict(h)
        hero_copy["russianAliases"] = HERO_ALIASES.get(h["displayName"], [])
        heroes_list.append(hero_copy)

    # Sort alphabetically by displayName
    heroes_list.sort(key=lambda x: x["displayName"])
    return jsonify({
        "success": True,
        "count": len(heroes_list),
        "heroes": heroes_list
    })


@app.route("/api/recommend", methods=["POST"])
def recommend():
    """Calculates recommendations for a specific role or all heroes."""
    data = request.get_json() or {}
    allies = [int(x) for x in data.get("allies", []) if x is not None]
    enemies = [int(x) for x in data.get("enemies", []) if x is not None]
    bans = [int(x) for x in data.get("bans", []) if x is not None]

    weights = data.get("weights", {"counter": 70, "synergy": 20, "meta": 10})
    role = data.get("role", "all")
    allow_off_meta = bool(data.get("allowOffMeta", True))
    bracket = data.get("bracket", "LOW_RANK")

    recs = client.calculate_recommendations(
        allies=allies,
        enemies=enemies,
        bans=bans,
        weights=weights,
        role=role,
        allow_off_meta=allow_off_meta,
        bracket_key=bracket
    )

    return jsonify({
        "success": True,
        "role": role,
        "roleLabel": POSITION_LABELS.get(role, "Все роли"),
        "totalCandidates": len(recs),
        "recommendations": recs[:50]  # Return top 50
    })


@app.route("/api/team_matrix", methods=["POST"])
def team_matrix():
    """Returns top recommendations for all 5 team positions at once."""
    data = request.get_json() or {}
    allies = [int(x) for x in data.get("allies", []) if x is not None]
    enemies = [int(x) for x in data.get("enemies", []) if x is not None]
    bans = [int(x) for x in data.get("bans", []) if x is not None]

    weights = data.get("weights", {"counter": 70, "synergy": 20, "meta": 10})
    allow_off_meta = bool(data.get("allowOffMeta", True))
    bracket = data.get("bracket", "LOW_RANK")

    matrix = client.get_team_recommendations_matrix(
        allies=allies,
        enemies=enemies,
        bans=bans,
        weights=weights,
        allow_off_meta=allow_off_meta,
        bracket_key=bracket
    )

    return jsonify({
        "success": True,
        "matrix": matrix
    })


@app.route("/api/status", methods=["GET"])
def status():
    """Returns status of preloader, cache, and token."""
    return jsonify({
        "hasToken": bool(client.api_token),
        "heroesCount": len(client.heroes),
        "cachedMatchupsCount": len(client.matchups),
        "isPreloading": client.is_preloading,
        "preloadProgress": client.preload_progress,
        "currentBracket": client.current_bracket,
        "availableBrackets": list(BRACKET_CONFIGS.keys())
    })


@app.route("/api/preload", methods=["POST"])
def trigger_preload():
    """Triggers background preloading of all matchups."""
    data = request.get_json() or {}
    bracket = data.get("bracket", "LOW_RANK")
    client.preload_all_matchups_async(bracket_key=bracket)
    return jsonify({"success": True, "message": "Preloading started in background."})


def open_browser():
    webbrowser.open_new("http://localhost:5000")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"\n=======================================================")
    print(f"  STRATZ DOTA 2 CUSTOM DRAFTER")
    print(f"  Running locally on http://localhost:{port}")
    print(f"=======================================================\n")
    # Uncomment to automatically open browser on launch
    # Timer(1.5, open_browser).start()
    app.run(host="127.0.0.1", port=port, debug=False)
