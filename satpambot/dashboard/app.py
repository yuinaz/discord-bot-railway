import os, time, random
from flask import Flask, session, redirect, url_for, request, render_template, jsonify

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
def healthz(): return "ok", 200

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
