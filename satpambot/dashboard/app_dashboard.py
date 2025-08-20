from __future__ import annotations
import io, os, json, time
from pathlib import Path
from typing import Any, Dict, Iterable
from flask import (
    Flask, jsonify, request, render_template, redirect, url_for,
    send_from_directory, Response, Blueprint
)

# ========= Paths & config =========
DATA_DIR = Path("data"); DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR = DATA_DIR / "uploads"; UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
UI_CFG_PATH = DATA_DIR / "ui_config.json"
WHITELIST_PATH = DATA_DIR / "whitelist.txt"
PHISH_IMG_DB = Path(os.getenv("PHISH_IMG_DB", DATA_DIR / "phish_phash.json"))
PHISH_CFG = Path(os.getenv("PHISH_CONFIG_PATH", DATA_DIR / "phish_config.json"))

# ========= JSON helpers =========
def _load_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default

def _save_json(path: Path, obj: Any) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass

# ========= Health/Uptime =========
def _ensure_health_uptime(app: Flask):
    try:
        from .healthz_quiet import silence_healthz_logs, ensure_healthz_route, ensure_uptime_route
        silence_healthz_logs(); ensure_healthz_route(app); ensure_uptime_route(app)
    except Exception:
        start = time.time()
        @app.get("/healthz")
        def _healthz(): return jsonify(ok=True)
        @app.get("/uptime")
        def _uptime():  return jsonify(ok=True, uptime_sec=int(time.time()-start))

# ========= Discord bridge (fallback aman) =========
def _bridge_stats() -> Dict[str, Any]:
    try:
        from .discord_bridge import get_stats  # type: ignore
        return get_stats() or {}
    except Exception:
        return {
            "guilds": 0, "members": 0, "online": 0,
            "channels": 0, "threads": 0, "latency_ms": None,
        }

def _bridge_events() -> Iterable[Dict[str, Any]]:
    try:
        from .discord_bridge import iter_stats  # type: ignore
        for ev in iter_stats():
            yield ev
    except Exception:
        while True:
            yield _bridge_stats()
            time.sleep(3)

# ========= App factory =========
def create_app() -> Flask:
    app = Flask(
        "satpambot_dashboard",
        template_folder=str(Path(__file__).with_name("templates")),
        static_folder=None,
    )

    # Static dashboard assets → /dashboard-static/*
    static_bp = Blueprint(
        "dashboard_static", __name__,
        static_folder=str(Path(__file__).with_name("static")),
        static_url_path="/dashboard-static"
    )
    app.register_blueprint(static_bp)

    # (Opsional) NextJS static export di data/next_build
    try:
        NEXT_DIR = DATA_DIR / "next_build"
        if NEXT_DIR.exists():
            next_bp = Blueprint("next_export", __name__,
                                static_folder=str(NEXT_DIR),
                                static_url_path="/next")
            app.register_blueprint(next_bp)
    except Exception:
        pass

    # ===== Blueprint Presence (kalau ada modulnya) =====
    try:
        from .presence_api import bp as presence_bp  # type: ignore
        app.register_blueprint(presence_bp)
    except Exception:
        pass

    # ===== Pages =====
    @app.get("/")
    def root():
        return redirect("/login")

    @app.get("/login")
    def login_page():
        return render_template("login.html")

    @app.post("/login")
    def login_submit():
        # TODO: auth gate jika dibutuhkan
        return redirect("/dashboard")

    @app.get("/dashboard")
    def dashboard_page():
        return render_template("dashboard.html")

    @app.get("/dashboard/settings")
    def settings_page():
        return render_template("settings.html")

    @app.get("/settings")
    def settings_alias():
        return redirect("/dashboard/settings")

    @app.get("/dashboard/security")
    def security_page():
        return render_template("security.html")

    # ===== Static uploads =====
    @app.get("/uploads/<path:filename>")
    def uploads(filename: str):
        return send_from_directory(str(UPLOADS_DIR), filename, as_attachment=False)

    # ===== UI Config (kanonik + alias kunci agar frontend kompatibel) =====
    def _canonical_cfg():
        return {
            "theme": "dark",
            "accent_color": "#2563eb",
            "background_mode": "",
            "background_url": "",
            "apply_to_login": True,
            "logo_url": "",
        }

    @app.get("/api/ui-config")
    def ui_cfg_get():
        cfg = _load_json(UI_CFG_PATH, _canonical_cfg())
        # alias agar JS lama/baru kompatibel
        resp = {
            **cfg,
            "accent": cfg.get("accent_color"),
            "bg_mode": cfg.get("background_mode"),
            "bg_url": cfg.get("background_url"),
            "apply_login": cfg.get("apply_to_login"),
        }
        return jsonify(resp)

    @app.post("/api/ui-config")
    def ui_cfg_set():
        body = request.get_json(silent=True) or {}
        cfg = _load_json(UI_CFG_PATH, _canonical_cfg())

        # terima kedua versi kunci
        if "theme" in body: cfg["theme"] = body["theme"]
        if "accent" in body: cfg["accent_color"] = body["accent"]
        if "accent_color" in body: cfg["accent_color"] = body["accent_color"]
        if "bg_mode" in body: cfg["background_mode"] = body["bg_mode"]
        if "background_mode" in body: cfg["background_mode"] = body["background_mode"]
        if "bg_url" in body: cfg["background_url"] = body["bg_url"]
        if "background_url" in body: cfg["background_url"] = body["background_url"]
        if "apply_login" in body: cfg["apply_to_login"] = bool(body["apply_login"])
        if "apply_to_login" in body: cfg["apply_to_login"] = bool(body["apply_to_login"])
        if "logo_url" in body: cfg["logo_url"] = body["logo_url"]

        _save_json(UI_CFG_PATH, cfg)
        resp = {
            **cfg,
            "accent": cfg.get("accent_color"),
            "bg_mode": cfg.get("background_mode"),
            "bg_url": cfg.get("background_url"),
            "apply_login": cfg.get("apply_to_login"),
        }
        return jsonify({"ok": True, "config": resp})

    @app.post("/api/upload/background")
    def upload_background():
        f = request.files.get("file")
        if not f: return jsonify(ok=False, error="no file"), 400
        name = f.filename or f"bg_{int(time.time())}.bin"
        safe = name.replace("\\", "_").replace("/", "_")
        dst = UPLOADS_DIR / safe
        f.save(dst)
        url = f"/uploads/{safe}"
        # auto apply to config
        cfg = _load_json(UI_CFG_PATH, _canonical_cfg())
        cfg["background_mode"] = cfg.get("background_mode") or "image"
        cfg["background_url"] = url
        _save_json(UI_CFG_PATH, cfg)
        return jsonify(ok=True, url=url)

    # ===== Whitelist =====
    @app.get("/api/whitelist")
    def whitelist_get():
        if not WHITELIST_PATH.exists():
            return jsonify({"whitelist": []})
        lines = [x.strip() for x in WHITELIST_PATH.read_text(encoding="utf-8").splitlines() if x.strip()]
        return jsonify({"whitelist": lines})

    @app.post("/api/whitelist")
    def whitelist_set():
        body = request.get_json(silent=True) or {}
        items = body.get("whitelist") or body.get("items") or []
        if not isinstance(items, list): return jsonify(ok=False, error="invalid list"), 400
        WHITELIST_PATH.write_text("\n".join(str(x).strip() for x in items), encoding="utf-8")
        return jsonify(ok=True, count=len(items))

    # ===== Phishing =====
    @app.get("/api/phish/config")
    def phish_cfg_get():
        cfg = _load_json(PHISH_CFG, {"autoban": False, "threshold": 8, "urls": []})
        return jsonify(cfg)

    @app.post("/api/phish/config")
    def phish_cfg_set():
        body = request.get_json(silent=True) or {}
        cfg = _load_json(PHISH_CFG, {"autoban": False, "threshold": 8, "urls": []})
        for k in ("autoban","threshold","urls"):
            if k in body: cfg[k] = body[k]
        _save_json(PHISH_CFG, cfg)
        return jsonify(ok=True, cfg=cfg)

    @app.get("/api/phish/images")
    def phish_images_get():
        db = _load_json(PHISH_IMG_DB, {"phash": []})
        if isinstance(db, list):  # compat lama
            db = {"phash": db}
        return jsonify(db)

    @app.post("/api/phish/images")
    def phish_images_add():
        # dukung multipart upload file ATAU JSON {"phash":[...]}
        if request.files:
            from PIL import Image
            try:
                import imagehash  # optional
            except Exception:
                imagehash = None

            db = _load_json(PHISH_IMG_DB, {"phash": []})
            existing = set(str(x) for x in db.get("phash", []))
            added = []
            for key in request.files:
                try:
                    im = Image.open(request.files[key].stream).convert("RGB")
                    if imagehash:
                        h = str(imagehash.phash(im))
                    else:
                        # fallback hash sederhana (bukan phash asli)
                        px = list(im.resize((8,8)).getdata())
                        avg = sum(sum(p) for p in px) / (len(px)*3)
                        bits = "".join("1" if sum(p) >= avg*3 else "0" for p in px)
                        h = hex(int(bits, 2))[2:]
                    if h not in existing:
                        existing.add(h); added.append(h)
                except Exception:
                    continue
            db["phash"] = list(existing)
            _save_json(PHISH_IMG_DB, db)
            return jsonify(ok=True, added=added, total=len(existing))

        body = request.get_json(silent=True) or {}
        arr = body.get("phash") or []
        if not isinstance(arr, list): return jsonify(ok=False, error="invalid phash list"), 400
        db = _load_json(PHISH_IMG_DB, {"phash": []})
        existing = set(str(x) for x in db.get("phash", []))
        for h in arr:
            existing.add(str(h))
        db["phash"] = list(existing)
        _save_json(PHISH_IMG_DB, db)
        return jsonify(ok=True, total=len(existing))

    @app.get("/api/phish/urls")
    def phish_urls_get():
        cfg = _load_json(PHISH_CFG, {"urls": []})
        return jsonify({"urls": cfg.get("urls", [])})

    @app.post("/api/phish/urls")
    def phish_urls_add():
        body = request.get_json(silent=True) or {}
        urls = body.get("urls") or []
        if not isinstance(urls, list): return jsonify(ok=False, error="invalid urls"), 400
        cfg = _load_json(PHISH_CFG, {"urls": []})
        cur = set(cfg.get("urls", []))
        for u in urls: cur.add(str(u).strip())
        cfg["urls"] = sorted(cur)
        _save_json(PHISH_CFG, cfg)
        return jsonify(ok=True, total=len(cfg["urls"]))

    # ===== Metrics =====
    @app.get("/api/metrics")
    def metrics():
        out = {"ok": True, "ts": int(time.time())}
        try:
            import psutil
            p = psutil.Process()
            out["process"] = {
                "cpu_percent": psutil.cpu_percent(interval=0.05),
                "mem_rss": p.memory_info().rss,
                "threads": p.num_threads(),
            }
        except Exception:
            pass
        s = _bridge_stats()
        out["discord"] = {
            "guilds": s.get("guilds"), "members": s.get("members"),
            "online": s.get("online"), "channels": s.get("channels"),
            "threads": s.get("threads"), "latency_ms": s.get("latency_ms"),
        }
        return jsonify(out)

    # ===== Discord SSE =====
    @app.get("/api/discord/stats")
    def discord_stats_once():
        return jsonify(_bridge_stats())

    @app.get("/api/discord/stream")
    def discord_stats_stream():
        def gen():
            for item in _bridge_events():
                yield f"data: {json.dumps(item)}\n\n"
        return Response(gen(), mimetype="text/event-stream")

    # Health & Uptime
    _ensure_health_uptime(app)

    try:
        app.logger.info("Route map: %s", [str(r.rule) for r in app.url_map.iter_rules()])
    except Exception:
        pass

    return app

# WSGI export
app = create_app()
