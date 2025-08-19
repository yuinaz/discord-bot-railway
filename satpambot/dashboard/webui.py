import os, time, json, platform, socket
from glob import glob
from flask import Blueprint, render_template, jsonify, request, send_from_directory

BP_NAME = "webui_builtin"
bp = Blueprint(BP_NAME, __name__,
               template_folder="templates",
               static_folder="static",
               static_url_path="/dashboard-static")

_STARTED = time.time()
UI_PATH = os.getenv("UI_SETTINGS_JSON", "data/ui_settings.json")
UPLOAD_DIR = os.getenv("UI_UPLOADS_DIR", "data/ui_uploads")
MAX_UPLOAD_MB = float(os.getenv("UI_MAX_UPLOAD_MB", "16"))
ALLOWED_IMAGE = {"png","jpg","jpeg","webp","gif","svg"}
ALLOWED_VIDEO = {"mp4","webm","ogg"}
ALLOWED_EXTS = ALLOWED_IMAGE | ALLOWED_VIDEO

DEFAULT_UI = {
    "logo_url": "",
    "bg_url": "",
    "accent": "#2563eb",
    "theme": "dark",
    "apply_to_login": False,
    "bg_mode": "image",   # image | particles | video
    "video_url": "",
    "particles_preset": "default"
}

THEMES = {
    "dark":   {"bg":"#0b111b","text":"#e6edf3","panel":"#111827","line":"#1f2937","muted":"#9aa4b2"},
    "light":  {"bg":"#f3f4f6","text":"#111827","panel":"#ffffff","line":"#e5e7eb","muted":"#6b7280"},
    "nord":   {"bg":"#2e3440","text":"#eceff4","panel":"#3b4252","line":"#434c5e","muted":"#d8dee9"},
    "dracula":{"bg":"#282a36","text":"#f8f8f2","panel":"#1e1f29","line":"#44475a","muted":"#bd93f9"},
    "ocean":  {"bg":"#0f172a","text":"#e2e8f0","panel":"#111827","line":"#1f2937","muted":"#94a3b8"},
    "forest": {"bg":"#0b1310","text":"#e2f7e1","panel":"#0f1d18","line":"#1b2a24","muted":"#9fd4b5"}
}

def _load_external_themes():
    # Load additional theme JSONs from data/themes/*.json
    # schema: {"bg":"#..","text":"#..","panel":"#..","line":"#..","muted":"#.."}
    path = "data/themes"
    out = {}
    try:
        for fn in glob(os.path.join(path, "*.json")):
            try:
                name = os.path.splitext(os.path.basename(fn))[0]
                with open(fn, "r", encoding="utf-8") as f:
                    m = json.load(f)
                if isinstance(m, dict) and all(k in m for k in ("bg","text","panel","line","muted")):
                    out[name] = {k:str(m[k]) for k in ("bg","text","panel","line","muted")}
            except Exception:
                continue
    except Exception:
        pass
    return out

EXTERNAL_THEMES = _load_external_themes()
THEMES.update(EXTERNAL_THEMES)

def _load_ui():
    try:
        if os.path.exists(UI_PATH):
            with open(UI_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                out = DEFAULT_UI.copy()
                if isinstance(data, dict):
                    for k in DEFAULT_UI.keys():
                        if k in data: out[k] = data[k]
                return out
    except Exception:
        pass
    return DEFAULT_UI.copy()

def _save_ui(data: dict):
    try:
        os.makedirs(os.path.dirname(UI_PATH), exist_ok=True)
        with open(UI_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False

def _safe_monitor():
    out = {"uptime_s": max(0, int(time.time() - _STARTED)),
           "cpu_percent": None, "mem_mb": None, "hostname": socket.gethostname()}
    try:
        import psutil  # type: ignore
        out["cpu_percent"] = float(psutil.cpu_percent(interval=0.05))
        out["mem_mb"] = int(psutil.Process().memory_info().rss/1024/1024)
    except Exception:
        pass
    return out

def _safe_activity():
    path = os.getenv("APP_LOG_PATH", "logs/app.log")
    rows = []
    try:
        if os.path.exists(path):
            with open(path, "rb") as f:
                data = f.read().splitlines()[-20:]
            rows = [line.decode("utf-8", "ignore") for line in data]
    except Exception:
        rows = []
    return {"lines": rows}

def _http_check(url: str, timeout: float):
    import time
    t0 = time.perf_counter()
    code, ok = None, False
    try:
        try:
            import requests  # type: ignore
            r = requests.get(url, timeout=timeout)
            code = r.status_code
            ok = 200 <= r.status_code < 400
        except Exception:
            import urllib.request
            with urllib.request.urlopen(url, timeout=timeout) as resp:  # nosec
                code = getattr(resp, "status", 200)
                ok = 200 <= (code or 200) < 400
    except Exception:
        ok = False
    ms = int((time.perf_counter() - t0) * 1000)
    return ok, f"{ms}ms", code

def _tcp_check(host: str, port: int, timeout: float):
    import time, socket
    t0 = time.perf_counter()
    ok = False
    try:
        with socket.create_connection((host, int(port)), timeout=timeout):
            ok = True
    except Exception:
        ok = False
    ms = int((time.perf_counter() - t0) * 1000)
    return ok, f"{ms}ms", None

def _safe_servers():
    path = os.getenv("SERVERS_JSON", "data/servers.json")
    result = {"servers": []}
    try:
        data = json.load(open(path, "r", encoding="utf-8")) if os.path.exists(path) else {"servers":[]}
    except Exception:
        data = {"servers":[]}
    for item in data.get("servers", []):
        name = item.get("name") or "-"
        typ  = (item.get("type") or "http").lower()
        timeout = float(item.get("timeout") or 2.0)
        status, ping, code = False, "-", None
        if typ == "tcp":
            status, ping, code = _tcp_check(item.get("host",""), item.get("port",80), timeout)
        else:
            status, ping, code = _http_check(item.get("url",""), timeout)
        result["servers"].append({
            "name": name,
            "status": "UP" if status else "DOWN",
            "ping": ping,
            "code": code
        })
    return result

def _ext_ok(filename: str) -> bool:
    ext = (filename.rsplit(".",1)[-1] or "").lower()
    return ext in ALLOWED_EXTS

@bp.get("/dashboard")
def builtin_dashboard():
    return render_template("dashboard/monitor.html")

@bp.get("/dashboard/settings")
def dashboard_settings():
    return render_template("dashboard/settings.html", ui=_load_ui(), themes=sorted(THEMES.keys()))

@bp.get("/api/ui-themes")
def api_ui_themes():
    return jsonify({"themes": sorted(THEMES.keys())})

@bp.get("/api/ui-settings")
def api_get_ui():
    ui = _load_ui()
    ui["_themes"] = THEMES  # optional for bridge script
    return jsonify(ui)

@bp.post("/api/ui-settings")
def api_set_ui():
    try:
        data = request.get_json(force=True, silent=True) or {}
        ui = _load_ui()
        for k, v in data.items():
            if k in DEFAULT_UI:
                if k in ("apply_to_login",) and isinstance(v, bool):
                    ui[k] = v
                elif isinstance(v, str):
                    if k == "accent" and (not v.startswith("#") or len(v) not in (4,7)):
                        continue
                    if k == "theme" and v not in THEMES:
                        continue
                    if k == "bg_mode" and v not in ("image","particles","video"):
                        continue
                    ui[k] = v.strip()
        ok = _save_ui(ui)
        return jsonify({"ok": ok, "ui": ui}), (200 if ok else 500)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@bp.post("/api/ui-upload")
def api_upload():
    kind = (request.args.get("kind") or "").lower().strip()
    if kind not in ("logo","bg","video"): return jsonify({"ok": False, "error":"invalid kind"}), 400
    if "file" not in request.files: return jsonify({"ok": False, "error":"missing file"}), 400
    f = request.files["file"]
    if not f.filename or not _ext_ok(f.filename): return jsonify({"ok": False, "error":"invalid extension"}), 400
    # Size limit
    f.stream.seek(0, os.SEEK_END); size = f.stream.tell(); f.stream.seek(0)
    if size > MAX_UPLOAD_MB * 1024 * 1024:
        return jsonify({"ok": False, "error":"file too large"}), 400
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    import time
    base = f"{kind}-{int(time.time())}.{f.filename.rsplit('.',1)[-1].lower()}"
    path = os.path.join(UPLOAD_DIR, base)
    f.save(path)
    url = f"/dashboard/uploads/{base}"
    ui = _load_ui()
    if kind=="logo": ui["logo_url"]=url
    elif kind=="bg": ui["bg_url"]=url
    else: ui["video_url"]=url
    _save_ui(ui)
    return jsonify({"ok": True, "url": url, "ui": ui})

@bp.get("/dashboard/uploads/<path:fn>")
def serve_uploads(fn):
    return send_from_directory(UPLOAD_DIR, fn, as_attachment=False)

@bp.get("/api/monitor")
def api_monitor(): return jsonify(_safe_monitor())

@bp.get("/api/activity")
def api_activity(): return jsonify(_safe_activity())

@bp.get("/api/servers")
def api_servers(): return jsonify(_safe_servers())

def register_webui_builtin(app):
    if BP_NAME not in app.blueprints:
        app.register_blueprint(bp)
