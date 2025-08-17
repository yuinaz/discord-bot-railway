from werkzeug.utils import secure_filename
import os, time, random
from flask import Flask, jsonify, redirect, render_template, request, session, url_for

# Explicit folders but relative to project root if run with PYTHONPATH=.
app = Flask("main", template_folder="templates", static_folder="static")

from functools import wraps
def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not (session.get("admin") or session.get("oauth") or session.get("discord_user")):
            return redirect(url_for("login", next=request.url))
        return fn(*args, **kwargs)
    return wrapper

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-please-change')
app.jinja_env.globals['cache_bust'] = os.getenv('CACHE_BUST', '1')

@app.get("/ping")
def ping(): return "pong", 200

@app.get("/healthz")
def healthz():
    return ("", 204)

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        user = request.form.get("user","")
        pw = request.form.get("pass","")
        user_env = os.getenv("ADMIN_USERNAME", os.getenv("SUPER_ADMIN_USER","admin"))
        pass_env = (os.getenv("ADMIN_PASSWORD") or os.getenv("SUPER_ADMIN_PASS") or os.getenv("SUPER_ADMIN_PASSWORD") or "admin")
        if user == user_env and pw == pass_env:
            session["admin"] = user
            nxt = request.args.get("next")
            return redirect(nxt or url_for("__root_dashboard"))
        return render_template("login.html", error="Kredensial salah.")
    return render_template("login.html", error=None)

@app.route("/admin/login", methods=["GET","POST"])
def admin_login():
    if request.method == "POST":
        return login()
    return redirect(url_for("login"))

@app.get("/logout")
def logout():
    session.pop("admin", None)
    return redirect(url_for("login"))

@app.before_request
def __root_conditional_dashboard():
    try:
        if request.path == "/" or request.path == "":
            if session.get("admin") or session.get("oauth") or session.get("discord_user"):
                return render_template("dashboard.html")
    except Exception:
        pass
    return None

@app.get("/__dashboard")
def __root_dashboard():
    return render_template("dashboard.html")

# --- API stubs for dashboard ---
@app.get("/api/stats")
def api_stats():
    return jsonify({
        "online": random.randint(5, 60),
        "messages_today": random.randint(100, 900),
        "warnings": random.randint(0, 5),
        "uptime": time.strftime("%H:%M:%S", time.gmtime(time.time()%86400)),
    })

@app.get("/api/traffic")
def api_traffic():
    labels = [f"{h:02d}:00" for h in range(24)]
    values = [random.randint(0, 50) for _ in labels]
    return jsonify({"labels": labels, "values": values})

@app.get("/api/top_guilds")
def api_top():
    return jsonify([{"name": f"Guild {i}", "count": random.randint(1, 99)} for i in range(1,7)])

@app.get("/api/mini-monitor")
def api_mm():
    return jsonify({"uptime": "3d 12h", "cpu": round(random.uniform(4, 27),1), "ram": random.randint(350, 1200)})


@app.get("/settings")
@login_required
def settings_page():
    # render template from package templates; ChoiceLoader already set
    return render_template("settings.html")


@app.get("/servers")
@login_required
def servers_page():
    # render template from package templates
    return render_template("servers.html")


@app.get("/api/live")
def __api_live_fallback():
    from flask import jsonify
    return jsonify(ok=True, live=True, bot=os.getenv("RUN_BOT","0") not in ("0","false","False"))
# === PATCH START: dashboard templates/routing ===
import os
from jinja2 import ChoiceLoader, FileSystemLoader
from functools import wraps

# Dual template loader (package + root)
try:
    pkg_templates = os.path.join(os.path.dirname(__file__), "templates")
    root_templates = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "templates"))
    loaders = []
    if os.path.isdir(pkg_templates):
        loaders.append(FileSystemLoader(pkg_templates))
    if os.path.isdir(root_templates):
        loaders.append(FileSystemLoader(root_templates))
    if loaders:
        app.jinja_loader = ChoiceLoader(loaders)
except Exception:
    pass

# login_required (ringan) bila belum ada
try:
    login_required
except NameError:
    def login_required(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not (session.get("admin") or session.get("oauth") or session.get("discord_user")):
                return redirect(url_for("login", next=request.url))
            return fn(*args, **kwargs)
        return wrapper

# Hindari loop redirect pada /login
@app.before_request
def __login_loop_guard():
    p = request.path or "/"
    if p in ("/login", "/admin/login"):
        return None

# Alias /dashboard
@app.get("/dashboard")
@login_required
def dashboard_alias():
    return render_template("dashboard.html")

# Halaman settings & servers
@app.get("/__debug/templates")
def __debug_templates():
    from flask import jsonify
    paths = []
    try:
        loader = app.jinja_loader
        loaders = getattr(loader, "loaders", [loader])
        for L in loaders:
            sp = getattr(L, "searchpath", None)
            if isinstance(sp, (list,tuple)):
                paths.extend(list(sp))
            elif isinstance(sp, str):
                paths.append(sp)
    except Exception:
        pass
    names = ["base.html","login.html","dashboard.html","settings.html","servers.html"]
    found = {}
    for base in paths:
        for n in names:
            fp = os.path.join(base, n)
            found[fp] = os.path.exists(fp)
    return jsonify(paths=paths, found=found)
# === PATCH END ===

@app.get("/theme/list")
@login_required
def theme_list():
    from flask import jsonify
    base = os.path.join(os.path.dirname(__file__), "static", "themes")
    themes = []
    try:
        if os.path.isdir(base):
            for n in os.listdir(base):
                if n.endswith(".css"):
                    themes.append(os.path.splitext(n)[0])
    except Exception:
        pass
    if not themes:
        themes = ["default","dark","light"]
    return jsonify(ok=True, themes=themes)

@app.get("/api/guilds")
@login_required
def api_guilds():
    from flask import jsonify
    return jsonify(ok=True, guilds=[])

@app.get("/assets-manager")
@login_required
def assets_manager():
    return render_template("assets_manager.html")

@app.get("/favicon.ico")
def favicon():
    from flask import send_from_directory
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    return send_from_directory(static_dir, "favicon.ico", mimetype="image/x-icon")

@app.get("/theme")
def theme_css():
    from flask import send_from_directory, session
    theme = (session.get("theme") or "default").strip()
    base = os.path.join(os.path.dirname(__file__), "static", "themes")
    css = f"{theme}.css"
    if not os.path.isfile(os.path.join(base, css)):
        css = "default.css"
    return send_from_directory(base, css, mimetype="text/css")

@app.get("/theme/apply")
@login_required
def theme_apply():
    from flask import jsonify, request, session
    theme = (request.args.get("set") or "default").strip()
    session["theme"] = theme
    return jsonify(ok=True, theme=theme)

# --- dev quick login context ---
@app.context_processor
def _inject_dev_login():
    flag = str(os.getenv("DEBUG_DEV_LOGIN","0")).lower() in ("1","true","yes","on")
    user = os.getenv("DEV_FAKE_USER","satpamleina")
    return {"dev_fake_login": flag, "dev_fake_user": user}

# --- dev quick login-as ---
@app.get("/dev/login-as/<username>")
def dev_login_as(username):
    # hanya aktif jika DEBUG_DEV_LOGIN=1
    flag = str(os.getenv("DEBUG_DEV_LOGIN","0")).lower() in ("1","true","yes","on")
    if not flag:
        from flask import abort
        return abort(404)
    session["admin"] = True
    session["username"] = username
    session["display_name"] = username
    # arahkan ke dashboard (alias)
    return redirect(url_for("dashboard_alias"))


# --- uptime endpoint (UptimeRobot) ---
@app.get("/uptime")
def uptime():
    return "OK", 200, {"Content-Type": "text/plain; charset=utf-8"}


# --- stub: /discord/login (redirect ke /login) ---
@app.get("/discord/login")
def discord_login_stub():
    return redirect(url_for("login"))


# --- upload background ke static/uploads ---
@app.post("/upload/background")
def upload_background():
    file = request.files.get("file")
    if not file:
        return jsonify(ok=False, error="no file"), 400
    save_dir = os.path.join(os.path.dirname(__file__), "static", "uploads")
    os.makedirs(save_dir, exist_ok=True)
    from datetime import datetime
    raw = file.filename or "background.bin"
    name, ext = os.path.splitext(raw)
    fname = f"bg_{{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}}{{ext or '.bin'}}"
    path = os.path.join(save_dir, fname)
    file.save(path)
    rel = f"uploads/{{fname}}"
    return jsonify(ok=True, path=f"/static/{{rel}}")


# === Phish signature API (pHash) ===
from PIL import Image
import imagehash, io, json
from pathlib import Path

PHASH_FILE = Path(os.getenv("PHISH_PHASH_FILE") or "data/phish_phash.json")
def _phash_load():
    if PHASH_FILE.exists():
        try:
            return json.loads(PHASH_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"phash":[]}

def _phash_save(obj):
    PHASH_FILE.parent.mkdir(parents=True, exist_ok=True)
    PHASH_FILE.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

@app.post("/api/phish-signature")
@login_required
def api_phish_signature():
    f = request.files.get("file")
    if not f:
        return jsonify(ok=False, error="no file"), 400
    try:
        img = Image.open(io.BytesIO(f.read())).convert("RGB")
        h = imagehash.phash(img)
        hstr = str(h)
        db = _phash_load()
        if hstr not in db["phash"]:
            db["phash"].append(hstr)
            _phash_save(db)
        return jsonify(ok=True, phash=hstr, count=len(db["phash"]))
    except Exception as e:
        return jsonify(ok=False, error=str(e)), 500

@app.get("/phish-lab")
@login_required
def phish_lab():
    db = _phash_load()
    return render_template("phish_lab.html", hashes=db.get("phash", []))


# === Phish config (no ENV) ===
import json
PHISH_CONFIG_PATH = os.path.join("data", "phish_config.json")

def _cfg_load():
    try:
        with open(PHISH_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"autoban": False, "threshold": 8, "log_thread_name": "Ban Log"}

def _cfg_save(obj):
    os.makedirs(os.path.dirname(PHISH_CONFIG_PATH), exist_ok=True)
    with open(PHISH_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)

@app.get("/api/phish-config")
@login_required
def api_phish_cfg_get():
    return jsonify(_cfg_load())

@app.post("/api/phish-config")
@login_required
def api_phish_cfg_post():
    data = request.get_json(silent=True) or {}
    cfg = _cfg_load()
    if "autoban" in data:
        cfg["autoban"] = bool(data["autoban"])
    if "threshold" in data:
        try:
            v = int(data["threshold"]); v = max(1, min(16, v))
            cfg["threshold"] = v
        except Exception:
            pass
    if "log_thread_name" in data:
        name = str(data["log_thread_name"]).strip() or "Ban Log"
        cfg["log_thread_name"] = name
    _cfg_save(cfg)
    return jsonify({"ok": True, **cfg})


# === Recent bans API (read from data/recent_bans.json) ===
import json, time
RECENT_BANS_PATH = os.path.join("data","recent_bans.json")
def _recent_bans_load():
    try:
        with open(RECENT_BANS_PATH,"r",encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"items":[]}

@app.get("/api/recent-bans")
def api_recent_bans():
    data = _recent_bans_load()
    # keep only latest 50 on read (optional cleanup)
    items = sorted(data.get("items", []), key=lambda x: x.get("ts", 0), reverse=True)[:50]
    return {"items": items, "ts": int(time.time())}


# === Whitelist API (realtime) ===
import json
WL_PATH = os.path.join("data","whitelist_domains.json")

def _wl_load():
    try:
        return json.load(open(WL_PATH,"r",encoding="utf-8"))
    except Exception:
        return []

def _wl_save(domains):
    os.makedirs(os.path.dirname(WL_PATH), exist_ok=True)
    # normalize: lowercase, strip, unique, sort
    norm = sorted({(d or "").strip().lower() for d in domains if (d or "").strip()})
    json.dump(norm, open(WL_PATH,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
    return norm

@app.get("/api/whitelist")
@login_required
def api_whitelist_get():
    return {"domains": _wl_load()}

@app.post("/api/whitelist")
@login_required
def api_whitelist_post():
    data = request.get_json(silent=True) or {}
    # support "text" (multiline) or "domains" list
    if "text" in data and isinstance(data["text"], str):
        items = [ln.strip() for ln in data["text"].splitlines()]
        saved = _wl_save(items)
        return {"ok": True, "domains": saved}
    if "domains" in data and isinstance(data["domains"], list):
        saved = _wl_save(data["domains"])
        return {"ok": True, "domains": saved}
    return {"ok": False, "error": "invalid payload"}, 400


# --- Theme injection (default to dark.css) ---
@app.context_processor
def inject_theme_path():
    try:
        theme = session.get("theme_css")
    except Exception:
        theme = None
    if not theme:
        theme = "/static/themes/dark.css"
    return {"theme_path": theme}


# --- UI Config for login (logo/background) ---
import json, os
UI_CFG_PATH = os.path.join("data","ui_config.json")

def _ui_cfg_load():
    try:
        return json.load(open(UI_CFG_PATH,"r",encoding="utf-8"))
    except Exception:
        return {}

@app.context_processor
def inject_login_ui():
    cfg = _ui_cfg_load()
    # default values
    logo = cfg.get("login_logo") or "/static/img/login-user.svg"
    bg   = cfg.get("login_bg") or "linear-gradient(120deg,#f093fb 0%,#f5576c 100%)"
    particles = bool(cfg.get("login_particles", True))
    return {"login_logo": logo, "login_bg": bg, "login_particles": particles}


@app.get("/api/ui-config")
@login_required
def api_ui_cfg_get():
    return _ui_cfg_load()

@app.post("/api/ui-config")
@login_required
def api_ui_cfg_post():
    data = request.get_json(silent=True) or {}
    cfg = _ui_cfg_load()
    if "login_logo" in data: cfg["login_logo"] = str(data["login_logo"]).strip()
    if "login_bg" in data: cfg["login_bg"] = str(data["login_bg"]).strip()
    if "login_particles" in data: cfg["login_particles"] = bool(data["login_particles"])
    _ui_cfg_save(cfg)
    return {"ok": True, **cfg}
