
from functools import wraps
from flask import Flask, session, redirect, url_for, request, render_template, flash, jsonify
from flask_socketio import SocketIO
from werkzeug.security import check_password_hash, generate_password_hash
import sqlite3
import threading
import os
import json
import datetime
import psutil
import time

# ===== INIT APP & SOCKET =====
app = Flask(__name__, template_folder='templates', static_folder='static')
app.secret_key = os.getenv('SECRET_KEY') or os.getenv('FLASK_SECRET', 'supersecretkey')
app.permanent_session_lifetime = datetime.timedelta(hours=12)

# Security & uploads hardening
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=True,  # Render uses HTTPS
    MAX_CONTENT_LENGTH=int(os.getenv("MAX_UPLOAD_MB", "8")) * 1024 * 1024,
)
ALLOWED_IMAGE_EXTS = {".gif", ".png", ".jpg", ".jpeg", ".webp"}
ALLOWED_MIMES = {"image/gif", "image/png", "image/jpeg", "image/webp"}

# --- Login guard decorator ---
def login_required(view):
    from functools import wraps
    from flask import session, redirect, url_for, request
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped

# === Metrics sampler & /stats.json ===
try:
    from modules.discord_bot.helpers.metrics_agg import start_sampler, snapshot
    start_sampler(interval_sec=60)
    @app.route("/stats.json")
    def stats_json_public():
        return jsonify(snapshot())
except Exception as _stats_err:
    # keep app running even if metrics module missing
    pass

socketio = SocketIO(app)

# Waktu mulai untuk uptime
start_time = time.time()

# ===== UTIL =====
def _now():
    return datetime.datetime.now()

# === TEMA / PROFILE ===
def _load_background_url():
    try:
        with open('config/background.json','r',encoding='utf-8') as f:
            return json.load(f).get('background_url')
    except Exception:
        return None
def _load_live_flag():
    try:
        with open('config/background.json','r',encoding='utf-8') as f:
            return bool(json.load(f).get('live_enabled'))
    except Exception:
        return False

def _load_background_opacity():
    try:
        with open('config/background.json','r',encoding='utf-8') as f:
            v = (json.load(f).get('opacity') or 1)
            try:
                return float(v)
            except Exception:
                return 1
    except Exception:
        return 1

def _save_background(url=None, live_enabled=None, opacity=None):
    os.makedirs('config', exist_ok=True)
    try:
        cur = json.load(open('config/background.json','r',encoding='utf-8'))
    except Exception:
        cur = {}
    if url is not None: cur['background_url'] = url
    if live_enabled is not None: cur['live_enabled'] = bool(live_enabled)
    if opacity is not None:
        try: cur['opacity'] = float(opacity)
        except Exception: pass
    json.dump(cur, open('config/background.json','w',encoding='utf-8'), ensure_ascii=False, indent=2)

def _load_profile():
    try:
        with open('config/profile.json','r',encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return {}
def _save_profile(data:dict):
    os.makedirs('config', exist_ok=True)
    with open('config/profile.json','w',encoding='utf-8') as f:
        json.dump(data, f)

@app.context_processor
def inject_theme():
    try:
        with open("config/theme.json", "r", encoding="utf-8") as f:
            theme_file = json.load(f).get("theme", "default.css")
            if not theme_file.endswith(".css"):
                theme_file += ".css"
    except Exception:
        theme_file = "default.css"
    session['live_bg_enabled']=_load_live_flag()
    _p=_load_profile()
    # cache_bust to beat CDN/browser caching for theme/background assets
    return {
        "theme_path": f"/static/themes/{theme_file}",
        "background_url": _load_background_url(),
        "profile_avatar_url": _p.get('avatar_url'),
        "login_background_url": _p.get('login_background_url'),
        "cache_bust": int(time.time()),
        "invite_url": _invite_url(),
        "background_opacity": _load_background_opacity()
    }

# ===== DATABASE SETUP =====
DB_PATH = "superadmin.db"
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS superadmin (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS banned_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                username TEXT,
                guild_id TEXT,
                reason TEXT,
                banned_at TEXT,
                active INTEGER DEFAULT 1,
                unbanned_at TEXT
            )
        """)
        if cur.fetchone():
            conn.execute("UPDATE superadmin SET password=? WHERE username=?",
                         (generate_password_hash(env_pass), env_user))
        else:
            conn.execute("INSERT INTO superadmin (username, password) VALUES (?, ?)",
                         (env_user, generate_password_hash(env_pass)))

# ===== SAFE LOG =====
def safe_log(msg, level="info"):
    now = datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")
    tag = {"info": "ℹ️", "error": "❌", "success": "✅"}.get(level, "")
    print(f"{now} {tag} {msg}")

# ===== IMPORT MODULES =====
from modules.discord_bot import run_bot as run_discord_bot
APP_BOT_THREAD_STARTED = False
from modules.database import (
    init_stats_db,
    get_last_7_days,
    get_stats_last_7_days,
    get_stats_all_guilds,
    get_hourly_join_leave
)

# ===== START DISCORD BOT THREAD =====
if not os.getenv('DISABLE_APP_AUTOBOT') and not APP_BOT_THREAD_STARTED:
    bot_thread = threading.Thread(target=run_discord_bot, daemon=True)
    bot_thread.start()
    APP_BOT_THREAD_STARTED = True

# ===== HEALTHCHECK & PING =====
@app.route('/healthz')
def healthz():
    return 'ok', 200

@app.route('/uptime')
def uptime():
    return 'alive', 200

@app.route('/ping')
def ping():
    return 'pong', 200

# ===== ROUTES =====
@app.route("/")
def home():
    return redirect("/dashboard") if session.get("logged_in") else redirect("/login")

@app.route("/login", methods=["GET", "POST"])
def login():
    # Sudah login? ke dashboard
    if session.get("logged_in"):
        return redirect(url_for("dashboard"))

    # Pastikan admin ENV tersinkron ke DB
    try:
        ensure_admin_seed()
    except Exception as e:
        safe_log(f"ensure_admin_seed error: {e}", level="error")

    if request.method == "POST":
        username = (request.form.get("username") or "").strip() or "admin"
        password = request.form.get("password") or ""

        # 1) Coba autentik via DB dulu
        try:
            with sqlite3.connect(DB_PATH) as conn:
                row = conn.execute(
                    "SELECT username, password FROM superadmin WHERE username=?",
                    (username,)
                ).fetchone()
                if row and check_password_hash(row[1], password):
                    session.permanent = True if request.form.get("remember") else False
                    session["logged_in"] = True
                    session["username"] = row[0]
                    flash("Login sukses", "success")
                    return redirect(request.args.get("next") or url_for("dashboard"))
        except Exception as e:
            safe_log(f"DB auth error: {e}", level="error")

        # 2) Fallback ke ENV
        env_user = os.getenv("SUPER_ADMIN_USER") or "admin"
        env_pass = os.getenv("SUPER_ADMIN_PASS") or os.getenv("ADMIN_PASSWORD") or ""
        if env_pass and username == env_user and password == env_pass:
            # Sinkron ke DB agar change-password bekerja
            try:
                with sqlite3.connect(DB_PATH) as conn:
                    cur = conn.execute("SELECT id FROM superadmin WHERE username=?", (env_user,))
                    if cur.fetchone():
                        conn.execute("UPDATE superadmin SET password=? WHERE username=?",
                                     (generate_password_hash(env_pass), env_user))
                    else:
                        conn.execute("INSERT INTO superadmin (username, password) VALUES (?, ?)",
                                     (env_user, generate_password_hash(env_pass)))
            except Exception as e:
                safe_log(f"DB sync from ENV failed: {e}", level="error")

            session.permanent = True if request.form.get("remember") else False
            session["logged_in"] = True
            session["username"] = env_user
            flash("Login sukses", "success")
            return redirect(request.args.get("next") or url_for("dashboard"))

        flash("Username / password salah", "danger")
        return render_template("login.html")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return render_template("logout.html")

@app.route("/dashboard")
@login_required
def dashboard():
    if not session.get("logged_in"):
        return redirect("/login")
    return render_template("dashboard.html")

@app.route("/settings", methods=["GET", "POST"])
def settings():
    if not session.get("logged_in"):
        return redirect("/login")
    if request.method == "POST":
        print("Disimpan:", request.form)
        return redirect("/settings")
    return render_template("settings.html", available_themes=list_themes(), current_theme=(json.load(open("config/theme.json","r",encoding="utf-8")).get("theme") if os.path.exists("config/theme.json") else None))

@app.route("/grafik")
def grafik():
    if not session.get("logged_in"):
        return redirect("/login")
    return render_template("grafik.html")

@app.route("/profil")
def profil():
    if not session.get("logged_in"):
        return redirect("/login")
    return render_template("profil.html")

@app.route("/change-password", methods=["GET", "POST"])
def change_password():
    if not session.get("logged_in"):
        return redirect("/login")
    if request.method == "POST":
        old_pw = request.form.get("old_password") or ""
        new_pw = request.form.get("new_password") or ""
        if len(new_pw) < 6:
            flash("Password baru minimal 6 karakter.", "danger")
            return redirect(url_for("change_password"))
        with sqlite3.connect(DB_PATH) as conn:
            user = conn.execute("SELECT username, password FROM superadmin WHERE username=?", (session["username"],)).fetchone()
            if user and check_password_hash(user[1], old_pw):
                conn.execute("UPDATE superadmin SET password=? WHERE username=?",
                             (generate_password_hash(new_pw), session["username"]))
                flash("Password berhasil diubah.", "success")
            else:
                flash("Password lama salah.", "danger")
        return redirect("/change-password")
    return render_template("change-password.html")

@app.route("/api/user-stats")
def user_stats():
    if not session.get("logged_in"):
        return redirect("/login")
    data = get_last_7_days()
    labels = [d[0] for d in data]
    values = [d[1] for d in data]
    return jsonify({"labels": labels, "values": values})

@app.route("/api/server-stats/<guild_id>")
def server_stats(guild_id):
    if not session.get("logged_in"):
        return redirect("/login")
    data = get_stats_last_7_days(guild_id)
    labels = [d[0] for d in data]
    values = [d[1] for d in data]
    return jsonify({"labels": labels, "values": values})

@app.route("/api/join-leave/<guild_id>")
@login_required
def api_join_leave(guild_id):
    rows = get_hourly_join_leave(guild_id)
    hours, joins, leaves = [], [], []
    for hour, j, l in rows:
        hours.append(f"{hour}:00")
        joins.append(j)
        leaves.append(l)
    return jsonify({"hours": hours, "joins": joins, "leaves": leaves})

# ===== API REAL-TIME: Semua Server Stats =====
@app.route("/api/servers/summary")
def api_servers_summary():
    if not session.get("logged_in"):
        return redirect("/login")
    try:
        stats = get_stats_all_guilds()
        return jsonify(stats)
    except Exception as e:
        safe_log(f"❌ Gagal ambil summary stats: {e}", level="error")
        return jsonify([])

# ===== API: Live System Stats =====
@app.route("/api/live_stats")
def live_stats():
    if not session.get("logged_in"):
        return jsonify({"error": "Unauthorized"}), 401

    uptime_seconds = time.time() - start_time
    uptime_str = str(datetime.timedelta(seconds=int(uptime_seconds)))

    ram_usage = round(psutil.virtual_memory().used / (1024 * 1024), 2)
    cpu_usage = psutil.cpu_percent(interval=0.5)

    return jsonify({
        "uptime": uptime_str,
        "ram": ram_usage,
        "cpu": cpu_usage
    })

# ===== GANTI TEMA (Form Manual + Dropdown Otomatis) =====
@app.route("/themes", methods=["GET", "POST"])
def themes():
    if not session.get("logged_in"):
        return redirect("/login")

    theme_folder = "static/themes"
    os.makedirs(theme_folder, exist_ok=True)

    available_themes = [
        f for f in os.listdir(theme_folder)
        if f.endswith(".css") and not f.startswith("_")
    ]

    if request.method == "POST":
        theme = request.form.get("theme", "")
        if theme in available_themes:
            os.makedirs("config", exist_ok=True)
            with open("config/theme.json", "w", encoding="utf-8") as f:
                json.dump({"theme": theme}, f)
            safe_log(f"🎨 Tema diubah via form: {theme}")
        return redirect("/dashboard")

    return render_template(
        "themes.html",
        username=session.get("username", "Admin"),
        themes=available_themes
    )

# ===== GANTI TEMA (AJAX) =====
@app.route("/theme", methods=["POST"])
def change_theme():
    try:
        if request.method == "POST":
            data = request.get_json(silent=True) or {}
            theme_name = (data.get("theme") or "").strip()
            bg = (data.get("background_image") or "").strip()
        else:
            theme_name = (request.args.get("set") or request.args.get("theme") or "").strip()
            bg = (request.args.get("background_image") or "").strip()

        if theme_name and not theme_name.endswith(".css"):
            theme_name += ".css"
        themes_dir = os.path.join("static","themes")
        available = {f for f in os.listdir(themes_dir) if f.endswith(".css")}

        if theme_name and theme_name not in available:
            return jsonify({"status":"error","message":"File tema tidak ditemukan"}), 400

        os.makedirs("config", exist_ok=True)
        conf_path = os.path.join("config","theme.json")
        try:
            conf = json.load(open(conf_path,"r",encoding="utf-8"))
        except Exception:
            conf = {}
        if theme_name: conf["theme"] = theme_name
        if bg: conf["background_image"] = bg
        json.dump(conf, open(conf_path,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
        return jsonify({"status":"success","config":conf})
    except Exception as e:
        safe_log(f"❌ Gagal ubah tema: {e}", level="error")
        return jsonify({"status":"error","message":str(e)}), 500

# ===== SOCKETIO EVENTS =====

@socketio.on('connect')
def handle_connect():
    print("📡 Client terhubung ke SocketIO")

@socketio.on('disconnect')
def handle_disconnect():
    print("📴 Client terputus")

def broadcast_stat_update():
    data = get_stats_all_guilds()
    socketio.emit("update_stats", {"data": data})

# Auto broadcast tiap 60 detik
def start_broadcast_loop():
    def loop():
        while True:
            socketio.sleep(60)
            broadcast_stat_update()
    thread = threading.Thread(target=loop)
    thread.daemon = True
    thread.start()

# === Upload helpers ===
def _validate_upload(file):
    if not file:
        return False, "no-file"
    # MIME check (best-effort)
    if file.mimetype and file.mimetype.lower() not in ALLOWED_MIMES:
        return False, "bad-mime"
    # Extension check
    _, ext = os.path.splitext(file.filename or "")
    if (ext or "").lower() not in ALLOWED_IMAGE_EXTS:
        return False, "bad-ext"
    return True, "ok"

# === Dashboard background upload ===
@app.route("/upload-background", methods=["POST"])
def upload_background():
    if not session.get("logged_in"): return redirect(url_for("login"))
    file = request.files.get("background")
    ok, reason = _validate_upload(file)
    if not ok: 
        flash("Format gambar tidak didukung.", "danger")
        return redirect(url_for("settings"))
    os.makedirs("static/uploads", exist_ok=True)
    save_path = os.path.join("static","uploads","dashboard_bg.jpg")
    file.save(save_path)
    public = "/static/uploads/dashboard_bg.jpg"
    os.makedirs("config", exist_ok=True)
    with open("config/background.json","w",encoding="utf-8") as f:
        json.dump({"background_url": public, "live_enabled": _load_live_flag()}, f)
    flash("Background dashboard diperbarui.", "success")
    return redirect(url_for("settings"))

# === Live background toggle ===
@app.route("/background-live", methods=["POST"])
def set_background_live():
    try:
        enabled = bool((request.get_json(silent=True) or {}).get("enabled"))
        os.makedirs("config", exist_ok=True)
        data = {}
        try:
            with open("config/background.json","r",encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}
        data["live_enabled"] = enabled
        with open("config/background.json","w",encoding="utf-8") as f:
            json.dump(data, f)
        session["live_bg_enabled"] = enabled
        return jsonify({"ok": True, "enabled": enabled})
    except Exception as e:
        return jsonify({"ok": False, "message": str(e)}), 400

# === Profile avatar upload ===
@app.route("/upload-avatar", methods=["POST"])
def upload_avatar():
    if not session.get("logged_in"): return redirect(url_for("login"))
    file = request.files.get("avatar")
    ok, reason = _validate_upload(file)
    if not ok:
        flash("Format gambar tidak didukung.", "danger")
        return redirect(url_for("settings"))
    os.makedirs("static/uploads", exist_ok=True)
    import os as _os
    ext = (_os.path.splitext(file.filename)[1] or "").lower()
    save = "avatar" + (ext if ext in [".gif",".png",".jpg",".jpeg",".webp"] else ".png")
    path = _os.path.join("static","uploads", save)
    file.save(path)
    public = "/static/uploads/" + save
    p = _load_profile()
    p["avatar_url"] = public
    _save_profile(p)
    flash("Avatar diperbarui.", "success")
    return redirect(url_for("settings"))

# === Login background upload ===
@app.route("/upload-login-background", methods=["POST"])
def upload_login_background():
    if not session.get("logged_in"): return redirect(url_for("login"))
    file = request.files.get("background")
    ok, reason = _validate_upload(file)
    if not ok:
        flash("Format gambar tidak didukung.", "danger")
        return redirect(url_for("settings"))
    os.makedirs("static/uploads", exist_ok=True)
    path = os.path.join("static","uploads","login_bg.jpg")
    file.save(path)
    public = "/static/uploads/login_bg.jpg"
    p = _load_profile()
    p["login_background_url"] = public
    _save_profile(p)
    flash("Background login diperbarui.", "success")
    return redirect(url_for("settings"))

# === Blacklist Image Editor ===
@app.route("/blacklist-image", methods=["GET","POST"])
def blacklist_image():
    if not session.get("logged_in"): return redirect(url_for("login"))
    if request.method == "POST":
        file = request.files.get("image"); note = request.form.get("note") or ""
        ok, reason = _validate_upload(file)
        if not ok:
            flash("Format gambar tidak didukung.", "danger")
            return redirect(url_for("blacklist_image"))
        from modules.discord_bot.helpers.image_check import add_to_blacklist
        add_to_blacklist(file.read(), note=note, added_by=session.get("username","admin"))
        flash("Gambar ditambahkan ke blacklist.", "success")
        return redirect(url_for("blacklist_image"))
    try:
        import os as _os, json as _json
        path = os.getenv("BLACKLIST_IMAGE_HASHES","data/blacklist_image_hashes.json")
        if _os.path.exists(path): items = _json.load(open(path,"r",encoding="utf-8"))
        else: items = []
    except Exception: items = []
    return render_template("admin_blacklist.html", items=items)

# === Security dashboard ===
@app.route("/security", methods=["GET","POST"])
def security_page():
    if not session.get("logged_in"): return redirect(url_for("login"))
    from modules.discord_bot.helpers.config_manager import load_config, save_config
    wl_path = os.getenv("WHITELIST_DOMAINS_FILE", "data/whitelist_domains.json")
    bl_path = os.getenv("BLACKLIST_DOMAINS_FILE", "data/blacklist_domains.json")

    if request.method == "POST":
        action = request.form.get("action")
        if action == "save_lists":
            wl_text = request.form.get("whitelist","")
            bl_text = request.form.get("blacklist","")
            wl = [d.strip() for d in wl_text.splitlines() if d.strip()]
            bl = [d.strip() for d in bl_text.splitlines() if d.strip()]
            os.makedirs(os.path.dirname(wl_path), exist_ok=True)
            with open(wl_path,"w",encoding="utf-8") as f: json.dump(wl, f, ensure_ascii=False, indent=2)
            os.makedirs(os.path.dirname(bl_path), exist_ok=True)
            with open(bl_path,"w",encoding="utf-8") as f: json.dump(bl, f, ensure_ascii=False, indent=2)
        elif action == "save_ocr":
            ocr_text = request.form.get('ocr_words','')
            lst = [w.strip() for w in ocr_text.split(',') if w.strip()]
            os.makedirs('config', exist_ok=True)
            with open('config/ocr.json','w',encoding='utf-8') as f:
                json.dump({'blockwords': lst}, f, ensure_ascii=False, indent=2)
        elif action == "save_lists_roles":
            roles = [x.strip() for x in (request.form.get('roles','')).split(',') if x.strip()]
            chans = [x.strip().lstrip('#') for x in (request.form.get('channels','')).split(',') if x.strip()]
            from modules.discord_bot.helpers.config_manager import load_config, save_config
            cfg = load_config(); cfg['EXEMPT_ROLES']=roles; cfg['WHITELIST_CHANNELS']=chans; save_config(cfg)
        elif action == "save_flags":
            cfg = load_config()
            for key in ["OCR_ENABLED","NSFW_INVITE_AUTOBAN","URL_RESOLVE_ENABLED","URL_AUTOBAN_CRITICAL","VIRUSTOTAL_ENABLED"]:
                cfg[key] = bool(request.form.get(key))
            cfg["URL_CRITICAL_ACTION"] = request.form.get("URL_CRITICAL_ACTION") or "ban"
            cfg["VIRUSTOTAL_TIMEOUT"] = request.form.get("VIRUSTOTAL_TIMEOUT") or "5"
            save_config(cfg)
        return redirect(url_for("security_page"))

    try:
        with open(wl_path,"r",encoding="utf-8") as f: wl = json.load(f)
    except Exception: wl = []
    try:
        with open(bl_path,"r",encoding="utf-8") as f: bl = json.load(f)
    except Exception: bl = []

    cfg = {}
    try:
        from modules.discord_bot.helpers.config_manager import load_config as _lc
        cfg = _lc()
    except Exception:
        cfg = {}

    return render_template("security.html", wl=wl, bl=bl, cfg=cfg)

# === Security live stats ===
@app.route("/security-stats")
def security_stats():
    from modules.discord_bot.helpers.stats import summarize
    s = summarize(3600)  # last hour
    return jsonify({"ok": True, "data": s})

# === Image Classifier Admin ===
@app.route("/image-classifier", methods=["GET","POST"])
def image_classifier_page():
    if not session.get("logged_in"): return redirect(url_for("login"))
    from modules.discord_bot.helpers.image_classifier import add_exemplar, _load_db
    msg = None
    if request.method == "POST":
        label = request.form.get("label") or "scam"
        file = request.files.get("image")
        ok, reason = _validate_upload(file)
        if file and ok:
            add_exemplar(file.read(), label=label)
            msg = f"Exemplar {label} ditambahkan."
        else:
            msg = "Format gambar tidak didukung."
    db = _load_db()
    return render_template("image_classifier.html", db=db, msg=msg)

@app.route("/healthcheck")
def healthcheck():
    return "ok", 200

# === Discord OAuth Login ===
from urllib.parse import urlencode
import requests

def oauth_enabled():
    return bool(os.getenv("DISCORD_CLIENT_ID") and os.getenv("DISCORD_CLIENT_SECRET"))

@app.route("/login/oauth/discord")
def login_oauth_discord():
    if not oauth_enabled():
        return redirect(url_for("login"))
    params = {
        "client_id": os.getenv("DISCORD_CLIENT_ID"),
        "redirect_uri": os.getenv("DISCORD_REDIRECT_URI", request.url_root.rstrip("/") + "/oauth/callback/discord"),
        "response_type": "code",
        "scope": "identify"
    }
    return redirect("https://discord.com/api/oauth2/authorize?" + urlencode(params))

@app.route("/oauth/callback/discord")
def oauth_callback_discord():
    if not oauth_enabled():
        return redirect(url_for("login"))
    code = request.args.get("code")
    if not code:
        return redirect(url_for("login"))
    data = {
        "client_id": os.getenv("DISCORD_CLIENT_ID"),
        "client_secret": os.getenv("DISCORD_CLIENT_SECRET"),
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": os.getenv("DISCORD_REDIRECT_URI", request.url_root.rstrip("/") + "/oauth/callback/discord"),
        "scope": "identify"
    }
    r = requests.post("https://discord.com/api/oauth2/token", data=data, headers={"Content-Type":"application/x-www-form-urlencoded"})
    if r.status_code != 200:
        return redirect(url_for("login"))
    tok = r.json().get("access_token")
    u = requests.get("https://discord.com/api/users/@me", headers={"Authorization": f"Bearer {tok}"})
    if u.status_code == 200:
        user = u.json()
        session["logged_in"] = True
        session["username"] = user.get("username")
        session["user_id"] = user.get("id")
        session["avatar"] = f"https://cdn.discordapp.com/avatars/{user.get('id')}/{user.get('avatar')}.png" if user.get("avatar") else None
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

# === Logs viewer ===
@app.route("/logs")
def logs_view():
    if not session.get("logged_in"): return redirect(url_for("login"))
    from modules.discord_bot.helpers.db import SessionLocal, ActionLog, init_db as _init_db_logs
    _init_db_logs()
    q = request.args.get("q","").strip().lower()
    with SessionLocal() as s:
        qry = s.query(ActionLog).order_by(ActionLog.ts.desc()).limit(500)
        rows = list(qry)
        if q:
            rows = [r for r in rows if q in (r.action or '').lower() or q in (r.user_id or '').lower() or q in (r.guild_id or '').lower() or q in (r.reason or '').lower()]
    return render_template("logs.html", rows=rows)

# === Provision UI ===
@app.route("/provision")
def provision_page():
    if not session.get("logged_in"): return redirect(url_for("login"))
    return render_template("provision.html")

@app.route("/provision/role", methods=["POST"])
def provision_role():
    if not session.get("logged_in"): return redirect(url_for("login"))
    name = (request.form.get("name") or "").strip()
    color = (request.form.get("color") or "").strip()
    if not name: return redirect(url_for("provision_page"))
    # send command to bot via a lightweight file signal (simplest cross-process)
    os.makedirs("data", exist_ok=True)
    with open("data/provision_queue.json","w",encoding="utf-8") as f:
        json.dump({"type":"role","name":name,"color":color}, f)
    return redirect(url_for("provision_page"))

@app.route("/provision/channel", methods=["POST"])
def provision_channel():
    if not session.get("logged_in"): return redirect(url_for("login"))
    name = (request.form.get("name") or "").strip()
    if not name: return redirect(url_for("provision_page"))
    os.makedirs("data", exist_ok=True)
    with open("data/provision_queue.json","w",encoding="utf-8") as f:
        json.dump({"type":"channel","name":name}, f)
    return redirect(url_for("provision_page"))

@app.route("/plugin")
def plugin_page():
    if not session.get("logged_in"): return redirect(url_for("login"))
    return render_template("plugin.html")

@app.route("/resource")
def resource_page():
    if not session.get("logged_in"): return redirect(url_for("login"))
    return render_template("resource.html")

@app.route("/user-locator")
def user_locator_page():
    if not session.get("logged_in"): return redirect(url_for("login"))
    return render_template("user_locator.html")

@app.route("/heartbeat")
def heartbeat():
    try:
        import json, os, time as _t
        path = "data/heartbeat.json"
        if os.path.exists(path):
            data = json.load(open(path,"r",encoding="utf-8"))
        else:
            data = {"ts": int(_t.time()), "status": "no-heartbeat-yet"}
        return jsonify({"ok": True, "data": data})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@app.route("/env-check")
def env_check():
    import os
    required = {"DISCORD_BOT_TOKEN": bool(os.getenv("DISCORD_BOT_TOKEN") or os.getenv("DISCORD_TOKEN"))}
    optional = {
        "VIRUSTOTAL_API_KEY": bool(os.getenv("VIRUSTOTAL_API_KEY")),
        "HF_API_TOKEN": bool(os.getenv("HF_API_TOKEN")),
        "DATABASE_URL": bool(os.getenv("DATABASE_URL")),
        "DISCORD_CLIENT_ID": bool(os.getenv("DISCORD_CLIENT_ID")),
        "DISCORD_CLIENT_SECRET": bool(os.getenv("DISCORD_CLIENT_SECRET")),
        "DISCORD_REDIRECT_URI": bool(os.getenv("DISCORD_REDIRECT_URI")),
    }
    ok = all(required.values())
    return jsonify({"ok": ok, "required": required, "optional": optional, "profile": os.environ.get("ENV_PROFILE_ACTIVE","none")})

@app.route("/widget")
def widget_page():
    return render_template("widget.html")

@app.route("/widget.js")
def widget_js():
    from flask import Response
    js = open("static/widget/widget.js","r",encoding="utf-8").read()
    return Response(js, mimetype="application/javascript")

@app.route("/widget.css")
def widget_css():
    from flask import Response
    css = open("static/widget/widget.css","r",encoding="utf-8").read()
    return Response(css, mimetype="text/css")

@app.route("/desktop-status")
def desktop_status():
    # Optional HMAC auth
    secret = os.getenv("DESKTOP_STATUS_SECRET")
    if secret:
        ts = request.headers.get("X-Widget-Timestamp")
        sig = request.headers.get("X-Widget-Signature")
        try:
            ts_i = int(ts)
            import time as _t, hmac, hashlib
            if abs(int(_t.time()) - ts_i) > 60:
                return jsonify({"ok": False, "error": "stale timestamp"}), 401
            calc = hmac.new(secret.encode(), str(ts_i).encode(), hashlib.sha256).hexdigest()
            if calc != sig:
                return jsonify({"ok": False, "error": "bad signature"}), 401
        except Exception:
            return jsonify({"ok": False, "error": "invalid auth"}), 401
    import time as _t, os as _os, json as _json, requests as _req
    base = request.url_root.rstrip("/")
    try: hb = _req.get(base + "/heartbeat", timeout=5).json()
    except Exception: hb = {"ok": False}
    try: health = (_req.get(base + "/healthcheck", timeout=5).text.strip() == "ok")
    except Exception: health = False
    # UptimeRobot (optional)
    ur_ok = None; ur_msg = "no-key"
    if os.getenv("UPTIMEROBOT_API_KEY"):
        try:
            r = _req.post("https://api.uptimerobot.com/v2/getMonitors",
                              data={"api_key": os.getenv("UPTIMEROBOT_API_KEY"), "format": "json", "logs": "0"}, timeout=7)
            data = r.json(); mons = data.get("monitors", []) if data.get("stat")=="ok" else []
            down = [m for m in mons if int(m.get("status",0)) in (0,8,9)]
            ur_ok = (len(down)==0); ur_msg = f"{len(mons)} monitors, down={len(down)}"
        except Exception: ur_ok = False; ur_msg = "err"
    return jsonify({
        "ok": True, "env": os.environ.get("ENV_PROFILE_ACTIVE","none"),
        "bot": hb, "render": {"ok": bool(health)},
        "uptimerobot": {"ok": ur_ok, "note": ur_msg}, "ts": int(_t.time())
    })

@app.route("/restart", methods=["POST"])
def restart_service():
    import os
    token = request.headers.get("X-Widget-Token") or request.args.get("token")
    expected = os.getenv("DESKTOP_RESTART_TOKEN")
    if not expected or token != expected:
        return jsonify({"ok": False, "error": "unauthorized"}), 401
    try:
        os._exit(1)  # Render akan restart proses
    except Exception:
        pass
    return jsonify({"ok": True})

def bootstrap():
    # Inisialisasi DB dashboards & bot stats
    ensure_admin_seed()
    init_db()
    init_stats_db()

    # Pastikan theme config valid
    os.makedirs("config", exist_ok=True)
    theme_file = "config/theme.json"
    if not os.path.exists(theme_file):
        with open(theme_file, "w", encoding="utf-8") as f:
            json.dump({"theme": "default.css"}, f)
    else:
        try:
            with open(theme_file, "r", encoding="utf-8") as f:
                current = json.load(f).get("theme", "")
            if not current.endswith(".css"):
                raise ValueError("Invalid theme format")
        except Exception:
            with open(theme_file, "w", encoding="utf-8") as f:
                json.dump({"theme": "default.css"}, f)

    # Mulai loop broadcast realtime 60 detik sekali
    start_broadcast_loop()

# ===== API: Member Monitor (dummy minimal agar UI tidak error) =====
@app.route("/api/member_monitor")
def api_member_monitor():
    if not session.get("logged_in"):
        return jsonify({"error":"Unauthorized"}), 401
    return jsonify({
        "labels": [f"{h:02d}:00" for h in range(24)],
        "active": [0]*24
    })


def _invite_url():
    cid = os.getenv("DISCORD_CLIENT_ID") or os.getenv("BOT_CLIENT_ID")
    perms = os.getenv("DISCORD_INVITE_PERMS", "8")
    scope = "bot%20applications.commands"
    if not cid: 
        return None
    return f"https://discord.com/api/oauth2/authorize?client_id={cid}&permissions={perms}&scope={scope}"

# ===== BANNED USERS: SQLite helpers =====
def db_list_bans():
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM banned_users ORDER BY active DESC, banned_at DESC, id DESC").fetchall()
        return [dict(r) for r in rows]

def db_add_ban(user_id, username=None, guild_id=None, reason=None):
    now = datetime.datetime.utcnow().isoformat() + "Z"
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO banned_users (user_id, username, guild_id, reason, banned_at, active) VALUES (?,?,?,?,?,1)",
            (str(user_id), username, str(guild_id) if guild_id else None, reason, now)
        )
        conn.commit()

def db_unban(user_id):
    now = datetime.datetime.utcnow().isoformat() + "Z"
    with sqlite3.connect(DB_PATH) as conn:
        cur = conn.execute("UPDATE banned_users SET active=0, unbanned_at=? WHERE user_id=? AND active=1", (now, str(user_id)))
        conn.commit()
        return cur.rowcount > 0

@app.route("/api/bans")
@login_required
def api_bans():
    return jsonify(db_list_bans())

@app.route("/api/unban/<user_id>", methods=["POST"])
@login_required
def api_unban(user_id):
    ok = db_unban(user_id)
    if ok:
        return jsonify({"status":"success","user_id":user_id})
    return jsonify({"status":"not_found"}), 404

# ==== Ingest dari Bot (ban/unban) ====
INGEST_TOKEN = os.getenv("BAN_INGEST_TOKEN", "change-me")

@app.route("/ingest/ban", methods=["POST"])
def ingest_ban():
    tok = request.headers.get("X-INGEST-TOKEN")
    if tok != INGEST_TOKEN:
        return jsonify({"status":"forbidden"}), 403
    data = request.get_json(silent=True) or {}
    action = (data.get("action") or "").lower()
    user_id = data.get("user_id")
    if not user_id:
        return jsonify({"status":"error","message":"user_id required"}), 400
    if action == "ban":
        db_add_ban(user_id, data.get("username"), data.get("guild_id"), data.get("reason"))
    elif action == "unban":
        db_unban(user_id)
    else:
        return jsonify({"status":"error","message":"invalid action"}), 400
    return jsonify({"status":"ok"})

@app.route("/bans")
@login_required
def bans_page():
    return render_template("bans.html")

def list_themes():
    themes_dir = os.path.join("static","themes")
    try:
        return sorted([f for f in os.listdir(themes_dir) if f.endswith(".css")])
    except Exception:
        return []

@app.route("/settings/theme", methods=["GET","POST"])
@login_required
def settings_theme():
    if request.method == "POST":
        theme = (request.form.get("theme") or "").strip()
        if theme and not theme.endswith(".css"):
            theme += ".css"
        available = set(list_themes())
        if theme in available:
            os.makedirs("config", exist_ok=True)
            path = os.path.join("config","theme.json")
            try:
                conf = json.load(open(path,"r",encoding="utf-8"))
            except Exception:
                conf = {}
            conf["theme"] = theme
            json.dump(conf, open(path,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
            flash("Tema disimpan.", "success")
        else:
            flash("Tema tidak ditemukan.", "danger")
        return redirect("/settings/theme")
    # current
    try:
        cur = json.load(open("config/theme.json","r",encoding="utf-8")).get("theme")
    except Exception:
        cur = None
    return render_template("settings_theme.html", available_themes=list_themes(), current_theme=cur)

@app.route("/save-background", methods=["POST"])
def save_background():
    if not session.get("logged_in"): return redirect(url_for("login"))
    url = request.form.get("background_url") or request.json.get("background_url") if request.is_json else None
    opacity = request.form.get("opacity") or request.json.get("opacity") if request.is_json else None
    live_enabled = (request.form.get("live_enabled") or request.json.get("live_enabled") if request.is_json else None)
    _save_background(url=url, live_enabled=live_enabled, opacity=opacity)
    flash("Background disimpan.", "success")
    return redirect(url_for("settings"))

from werkzeug.utils import secure_filename
from PIL import Image, ImageOps

ALLOWED_IMAGE_EXT = {".png",".jpg",".jpeg",".webp",".gif"}

def allowed_image(filename: str) -> bool:
    try:
        ext = "." + filename.rsplit(".",1)[1].lower()
    except Exception:
        return False
    return ext in ALLOWED_IMAGE_EXT

@app.route("/upload/background", methods=["POST"])
@login_required
def upload_background():
    # Limit a bit (e.g., 15MB)
    max_len = 15 * 1024 * 1024
    if request.content_length and request.content_length > max_len:
        return jsonify({"status":"error","message":"File terlalu besar (>15MB)"}), 413

    f = request.files.get("file")
    if not f or not f.filename:
        return jsonify({"status":"error","message":"Tidak ada file"}), 400
    if not allowed_image(f.filename):
        return jsonify({"status":"error","message":"Ekstensi tidak diizinkan"}), 400

    ts = int(time.time())
    base = secure_filename(f.filename)
    name = f"{ts}_{base}"
    updir = os.path.join("static","uploads")
    os.makedirs(updir, exist_ok=True)
    path = os.path.join(updir, name)
    f.save(path)

    # Build URL and persist to theme.json as background_image
    url = f"/static/uploads/{name}"
    try:
        conf_path = os.path.join("config","theme.json")
        os.makedirs("config", exist_ok=True)
        try:
            conf = json.load(open(conf_path,"r",encoding="utf-8"))
        except Exception:
            conf = {}
        conf["background_image"] = url
        json.dump(conf, open(conf_path,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
    except Exception as e:
        pass

    return jsonify({"status":"success","url": url})

@app.route("/api/guilds")
@login_required
def api_guilds():
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM bot_guilds ORDER BY LOWER(name)").fetchall()
        return jsonify([dict(r) for r in rows])

@app.route("/servers")
@login_required
def servers_page():
    return render_template("servers.html")
