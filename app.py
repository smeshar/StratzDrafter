import os
import json
import webbrowser
import requests
from threading import Timer
from flask import Flask, render_template, request, jsonify, session
from dotenv import load_dotenv

from stratz_client import StratzClient, BRACKET_CONFIGS, POSITION_LABELS
from aliases import matches_search, HERO_ALIASES
from users_db import (
    register_user,
    authenticate_user,
    get_user_by_id,
    update_user_stratz_token,
    get_raw_stratz_token_for_user
)

load_dotenv()

app = Flask(__name__, static_folder="static", template_folder="templates")
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.secret_key = os.getenv("SECRET_KEY", "stratz-drafter-secret-key-12345")

client = StratzClient()

# Initialize data on start
print("[Server] Initializing Stratz data...")
client.fetch_heroes()
client.fetch_stats(bracket_key="LOW_RANK")


def get_current_user():
    """Retrieves safe profile for currently logged in session user."""
    user_id = session.get("user_id")
    if not user_id:
        return None
    return get_user_by_id(user_id)


def get_active_stratz_token():
    """Returns user's custom STRATZ token if logged in and configured, else None."""
    user_id = session.get("user_id")
    if not user_id:
        return None
    return get_raw_stratz_token_for_user(user_id)


# ==============================================================================
# PAGES & CORE ROUTES
# ==============================================================================

@app.route("/")
def index():
    return render_template("index.html")


# ==============================================================================
# AUTHENTICATION & USER PROFILE API
# ==============================================================================

@app.route("/api/auth/me", methods=["GET"])
def auth_me():
    """Returns current authentication state and user profile."""
    user = get_current_user()
    return jsonify({
        "authenticated": bool(user),
        "user": user
    })


@app.route("/api/auth/register", methods=["POST"])
def auth_register():
    """Registers standard account with email, password, and optional name."""
    data = request.get_json() or {}
    email = data.get("email", "").strip()
    password = data.get("password", "")
    name = data.get("name", "").strip()

    try:
        user = register_user(email=email, password=password, name=name)
        session["user_id"] = user["id"]
        return jsonify({
            "success": True,
            "user": user,
            "message": "Регистрация прошла успешно!"
        })
    except ValueError as ve:
        return jsonify({"success": False, "message": str(ve)}), 400
    except Exception as e:
        return jsonify({"success": False, "message": f"Ошибка регистрации: {e}"}), 500


@app.route("/api/auth/login", methods=["POST"])
def auth_login():
    """Authenticates standard user via email/username and password."""
    data = request.get_json() or {}
    login_id = data.get("email", "").strip()
    password = data.get("password", "")

    user = authenticate_user(login_or_email=login_id, password=password)
    if not user:
        return jsonify({"success": False, "message": "Неверный логин или пароль"}), 401

    session["user_id"] = user["id"]
    safe_user = get_user_by_id(user["id"])
    return jsonify({
        "success": True,
        "user": safe_user,
        "message": f"С возвращением, {safe_user['name']}!"
    })


@app.route("/api/auth/logout", methods=["POST"])
def auth_logout():
    """Logs out user and clears session."""
    session.pop("user_id", None)
    return jsonify({"success": True, "message": "Вы вышли из системы"})


@app.route("/api/auth/token", methods=["POST"])
def auth_save_token():
    """Saves and validates personalized STRATZ API Bearer token for logged in user."""
    user = get_current_user()
    if not user:
        return jsonify({"success": False, "message": "Для сохранения токена необходимо войти в аккаунт"}), 401

    data = request.get_json() or {}
    token = data.get("token", "").strip()

    if not token:
        return jsonify({"success": False, "message": "Токен не может быть пустым"}), 400

    # Validate token live against Stratz GraphQL
    is_valid = client.validate_token(token)
    if not is_valid:
        return jsonify({
            "success": False,
            "message": "Токен не прошел проверку в Stratz API! Убедитесь, что скопировали Bearer токен полностью."
        }), 400

    update_user_stratz_token(user["id"], token)
    updated_user = get_user_by_id(user["id"])
    return jsonify({
        "success": True,
        "message": "Токен успешно проверен и сохранен! Теперь живые запросы выполняются через ваш аккаунт Stratz.",
        "user": updated_user
    })


@app.route("/api/auth/token", methods=["DELETE"])
def auth_delete_token():
    """Removes personalized STRATZ API token, returning account to offline cache mode."""
    user = get_current_user()
    if not user:
        return jsonify({"success": False, "message": "Необходима авторизация"}), 401

    update_user_stratz_token(user["id"], None)
    updated_user = get_user_by_id(user["id"])
    return jsonify({
        "success": True,
        "message": "Токен удален. Режим переключен на оффлайн-кэш.",
        "user": updated_user
    })


@app.route("/api/auth/validate_token", methods=["POST"])
def auth_validate_token():
    """Test validates a token string against Stratz GraphQL without saving it."""
    data = request.get_json() or {}
    token = data.get("token", "").strip()
    is_valid = client.validate_token(token)
    return jsonify({
        "success": is_valid,
        "isValid": is_valid,
        "message": "Токен валиден!" if is_valid else "Токен недействителен."
    })


# ==============================================================================
# DRAFT RECOMMENDATIONS & HEROES API
# ==============================================================================

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

    # If user has personalized token, ensure any missing matchups can be fetched
    user_token = get_active_stratz_token()
    if user_token:
        client.ensure_matchups(allies + enemies, bracket_key=bracket, custom_token=user_token)

    recommendations = client.calculate_recommendations(
        allies=allies,
        enemies=enemies,
        bans=bans,
        weights=weights,
        role=role,
        allow_off_meta=allow_off_meta,
        bracket_key=bracket
    )

    analysis = client.calculate_draft_analysis(
        allies=allies,
        enemies=enemies,
        weights=weights,
        bracket_key=bracket,
        allies_roles=data.get("alliesRoles")
    )

    return jsonify({
        "success": True,
        "count": len(recommendations),
        "role": role,
        "recommendations": recommendations,
        "analysis": analysis
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

    user_token = get_active_stratz_token()
    if user_token:
        client.ensure_matchups(allies + enemies, bracket_key=bracket, custom_token=user_token)

    matrix = client.get_team_recommendations_matrix(
        allies=allies,
        enemies=enemies,
        bans=bans,
        weights=weights,
        allow_off_meta=allow_off_meta,
        bracket_key=bracket
    )

    analysis = client.calculate_draft_analysis(
        allies=allies,
        enemies=enemies,
        weights=weights,
        bracket_key=bracket,
        allies_roles=data.get("alliesRoles")
    )

    return jsonify({
        "success": True,
        "matrix": matrix,
        "analysis": analysis
    })


@app.route("/api/draft_analysis", methods=["POST"])
def draft_analysis():
    """Direct fast endpoint for computing draft win rate and analytical insights."""
    data = request.get_json() or {}
    allies = [int(x) for x in data.get("allies", []) if x is not None]
    enemies = [int(x) for x in data.get("enemies", []) if x is not None]
    weights = data.get("weights", {"counter": 70, "synergy": 20, "meta": 10})
    bracket = data.get("bracket", "LOW_RANK")

    analysis = client.calculate_draft_analysis(
        allies=allies,
        enemies=enemies,
        weights=weights,
        bracket_key=bracket,
        allies_roles=data.get("alliesRoles")
    )

    return jsonify({
        "success": True,
        "analysis": analysis
    })


@app.route("/api/status", methods=["GET"])
def status():
    """Returns status of preloader, cache, authentication, and token mode."""
    user = get_current_user()
    user_token = get_active_stratz_token()
    env_token = os.getenv("STRATZ_API", "").strip() or client.api_token
    has_user_token = bool(user_token)
    has_env_token = bool(env_token)
    has_token = has_user_token or has_env_token

    if has_user_token:
        auth_mode = "personal_token"
    elif has_env_token:
        auth_mode = "server_token"
    elif user:
        auth_mode = "authenticated_no_token"
    else:
        auth_mode = "anonymous"

    return jsonify({
        "status": "ready" if client.heroes and client.matchups else "initializing",
        "isAuthenticated": bool(user),
        "authMode": auth_mode,
        "user": user,
        "hasUserToken": has_user_token,
        "hasServerToken": has_env_token,
        "hasToken": has_token,
        "isAnonymous": not bool(user),
        "mode": "live_user_token" if has_user_token else ("live_server_token" if has_env_token else "offline_cache"),
        "heroesCount": len(client.heroes),
        "cachedMatchupsCount": len(client.matchups),
        "isPreloading": client.is_preloading,
        "preloadProgress": client.preload_progress,
        "currentBracket": client.current_bracket,
        "availableBrackets": list(BRACKET_CONFIGS.keys())
    })


@app.route("/api/preload", methods=["POST"])
def trigger_preload():
    """
    Triggers background preloading of matchups.
    Anonymous mode restricts live requests to prevent quota burning.
    Authenticated users with custom token or server .env token use their own API key.
    """
    try:
        user_token = get_active_stratz_token()
        env_token = os.getenv("STRATZ_API", "").strip() or client.api_token
        is_test = bool(os.environ.get("PYTEST_CURRENT_TEST"))
        token_to_use = user_token or env_token or (client.api_token if is_test else None)

        if not token_to_use and not is_test:
            return jsonify({
                "success": False,
                "isAnonymous": True,
                "message": "В анонимном режиме используются только кэшированные данные. Войдите в личный кабинет и укажите свой STRATZ API токен для обновления базы."
            }), 400

        data = request.get_json(silent=True) or {}
        bracket = data.get("bracket", "LOW_RANK")
        force_refresh = data.get("force", True)

        client.preload_all_matchups_async(bracket_key=bracket, custom_token=token_to_use, force_refresh=force_refresh)
        return jsonify({
            "success": True,
            "message": "Синхронизация запущена с использованием вашего STRATZ API токена."
        })
    except Exception as e:
        print(f"Error starting preload: {e}")
        return jsonify({
            "success": False,
            "message": f"Ошибка запуска синхронизации: {e}"
        }), 500


def open_browser():
    webbrowser.open_new("http://localhost:5000")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    host = os.environ.get("HOST", "127.0.0.1")
    print(f"\n=======================================================")
    print(f"  STRATZ DOTA 2 CUSTOM DRAFTER")
    print(f"  Running on http://{host}:{port}")
    print(f"=======================================================\n")
    app.run(host=host, port=port, debug=False)
