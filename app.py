from satpambot.dashboard.phish_api import register_phish_routes

# app.py — robust entry for SatpamBot Dashboard
from __future__ import annotations
import os, logging
from flask import Flask, redirect, Response

log = logging.getLogger("entry.app")

def _try_register_webui(app: Flask) -> None:
    """Attempt to register an external dashboard blueprint if available."""
    tried = []
    for mod in ("satpambot.dashboard.webui", "dashboard.webui", "webui"):
        try:
            m = __import__(mod, fromlist=["register_webui_builtin"])
            m.register_webui_builtin(app)  # type: ignore
            log.info("Dashboard loaded via %s", mod)
            return
        except Exception as e:
            tried.append(f"{mod}: {e.__class__.__name__}")
    log.error("No dashboard blueprint registered. Tried: %s", ", ".join(tried))
    log.error("Dashboard failed to load - check import errors above.")

def _ensure_healthz(app: Flask) -> None:
    if any(r.rule == "/healthz" for r in app.url_map.iter_rules()):
        return
    @app.get("/healthz")
    def _healthz():
        return Response("OK", mimetype="text/plain")

def _register_aliases(app: Flask) -> None:
    def _alias(rule: str, target: str):
        if any(r.rule == rule for r in app.url_map.iter_rules()):
            return
        endpoint = f"_alias_{rule.replace('/', '_') or 'root'}"
        @app.get(rule, endpoint=endpoint)
        def _go():  # type: ignore
            return redirect(target, code=302)
        log.info("[alias] %s -> %s", rule, target)
    _alias("/", "/dashboard")
    _alias("/login", "/dashboard/login")
    _alias("/settings", "/dashboard/settings")
    _alias("/security", "/dashboard/security")



def _register_live_stats_api(app: Flask) -> None:
    """Expose /api/live/stats using the running Discord bot if available."""
    from flask import jsonify
    if any(r.rule == "/api/live/stats" for r in app.url_map.iter_rules()):
        return

    def _bot_try():
        # Try multiple locations
        try:
            from satpambot.bot.modules.discord_bot.discord_bot import bot as b
            if b: return b
        except Exception:
            pass
        try:
            from satpambot.bot.modules.discord_bot.shim_runner import bot as b  # type: ignore
            if b: return b
        except Exception:
            pass
        return None

    def _snapshot_sync(bot):
        try:
            guilds = list(getattr(bot, "guilds", []) or [])
        except Exception:
            guilds = []
        try:
            gcount = len(guilds)
        except Exception:
            gcount = 0
        # Channels and threads
        try:
            channels = sum(len(getattr(g, "channels", []) or []) for g in guilds)
        except Exception:
            channels = 0
        try:
            threads = sum(len(getattr(g, "threads", []) or []) for g in guilds)
        except Exception:
            threads = 0
        # Members & online (best-effort)
        total_members = 0
        total_online = 0
        for g in guilds:
            mc = getattr(g, "member_count", None)
            if isinstance(mc, int) and mc > 0:
                total_members += mc
            else:
                try:
                    total_members += len(getattr(g, "members", []) or [])
                except Exception:
                    pass
            try:
                total_online += sum(1 for m in (getattr(g, "members", []) or []) if str(getattr(getattr(m, "status", ""), "value", getattr(m,"status",""))).lower() not in ("offline","unknown","0","none"))
            except Exception:
                pass
        try:
            lat_ms = int(float(getattr(bot, "latency", 0.0) or 0.0) * 1000.0)
        except Exception:
            lat_ms = 0
        import time
        return {"guilds": gcount, "members": total_members, "online": total_online, "channels": channels, "threads": threads, "latency_ms": lat_ms, "updated": int(time.time())}

    @app.get("/api/live/stats")
    def _live_stats():
        bot = _bot_try()
        data = _snapshot_sync(bot) if bot else {"guilds":0,"members":0,"online":0,"channels":0,"threads":0,"latency_ms":0,"updated":0}
        data["ok"] = True
        return jsonify(data)


def _ensure_ui_api(app: Flask) -> None:
    def _has(rule: str) -> bool:
        return any(r.rule == rule for r in app.url_map.iter_rules())
    from flask import jsonify
    if not _has("/api/ui-config"):
        @app.get("/api/ui-config")
        def _ui_cfg():
            return jsonify({"ok": True, "theme": "gtake"})
    if not _has("/api/ui-themes"):
        @app.get("/api/ui-themes")
        def _ui_themes():
            return jsonify({"themes": ["gtake"]})

def _register_dashboard_blueprint_with_fallback(app: Flask) -> None:
    """If no /dashboard blueprint is present, install a very small fallback."""
    try:
        # If already present, do nothing
        if any(str(r.rule).startswith("/dashboard") for r in app.url_map.iter_rules()):
            return
    except Exception:
        pass
    from flask import Blueprint, render_template_string
    bp = Blueprint("dashboard_fallback", __name__, url_prefix="/dashboard")
    @bp.route("/", methods=["GET"])
    @bp.route("", methods=["GET"])
    def _home():
        return render_template_string("<!doctype html><title>Dashboard</title>Dashboard OK")
    app.register_blueprint(bp)

def _register_compat_assets(app: Flask) -> None:
    try:
        from satpambot.dashboard.compat_aliases import register_compat as __rc
        __rc(app)
    except Exception:
        # register minimal fallbacks
        @app.route("/dashboard-static/<path:fname>")
        def _compat_dashboard_static(fname):
            if fname.endswith(".js"):
                return ("console.log('compat ui bridge ok');", 200, {"Content-Type": "application/javascript"})
            if fname.endswith(".css"):
                return ("/* compat css ok */", 200, {"Content-Type": "text/css"})
            if fname.endswith(".svg"):
                return ("", 200, {"Content-Type": "image/svg+xml"})
            return ("", 200, {"Content-Type": "text/plain"})
        @app.route("/dashboard-theme/<theme>/theme.css")
        def _theme_css(theme):
            css = ":root{--bg:#0b1220;--text:#dbe1ff} body{background:var(--bg);color:var(--text);}"
            return (css, 200, {"Content-Type": "text/css"})
        @app.route("/favicon.ico")
        def _favicon():
            import base64
            data = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAukB9Xc2lZ0AAAAASUVORK5CYII=")
            return (data, 200, {"Content-Type": "image/png"})




def _register_phash_api(app: Flask) -> None:
    from flask import jsonify
    if any(r.rule == "/api/phish/phash" for r in app.url_map.iter_rules()):
        return
    def _load_phash_list():
        # Try data file if present, else return small sample
        import json, os
        p_candidates = ["data/phish/phash.json", "data/phash.json"]
        for p in p_candidates:
            if os.path.exists(p):
                try:
                    return json.load(open(p, "r", encoding="utf-8")) or []
                except Exception:
                    break
        # fallback demo data
        return ["a1b2c3d4", "e5f60789"]
    @app.get("/api/phish/phash")
    def _phash_array():
        return jsonify({"phash": _load_phash_list()})


def _register_uptime(app: Flask) -> None:
    import time
    if not getattr(app, "_start_time", None):
        app._start_time = time.time()
    @app.route("/uptime", methods=["HEAD"])
    def _uptime_head():
        return ("", 200, {"X-Uptime-Seconds": str(int(time.time() - app._start_time))})



def _register_logout_alias(app: Flask) -> None:
    from flask import Response, redirect
    @app.get("/logout")
    def _logout_page():
        # 200 page
        return Response("<!doctype html><title>Logged out</title>Logged out", mimetype="text/html")
    @app.get("/dashboard/logout")
    def _logout_redirect():
        return redirect("/dashboard/login", code=302)


def create_app() -> Flask:
    app = Flask("satpambot_dashboard")
    app.url_map.strict_slashes = False
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "satpambot-secret")

    _ensure_healthz(app)
    _try_register_webui(app)
    _register_dashboard_blueprint_with_fallback(app)
    _ensure_ui_api(app)
    _register_live_stats_api(app)
    _register_aliases(app)
    _register_compat_assets(app)
    _register_phash_api(app)
    _register_uptime(app)
    _register_logout_alias(app)
    return app





# Expose module-level app for environments importing `from app import app`
app = create_app()

# Back-compat placeholders (if other modules import these; set to None safely)
socketio = None
bootstrap = None

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    port = int(os.getenv("PORT", "10000"))
    app.run(host="0.0.0.0", port=port, debug=False)




# --- added by patch v13: simple health check route ---
@app.route('/healthz')
def healthz():
    return 'ok', 200

# auto-register v13
register_phish_routes(app)
