import os, time, json, platform, socket, datetime as dt
from flask import Blueprint, render_template, jsonify, request

BP_NAME = "webui_builtin"
bp = Blueprint(BP_NAME, __name__,
               template_folder="templates",
               static_folder="static",
               static_url_path="/dashboard-static")

_STARTED = time.time()
UI_PATH = os.getenv("UI_SETTINGS_JSON", "data/ui_settings.json")

DEFAULT_UI = {
    "logo_url": "",     # URL gambar logo (kosong = sembunyikan)
    "bg_url": "",       # URL gambar background (kosong = gunakan warna)
    "accent": "#2563eb",
    "theme": "dark"     # "dark" | "light"
}

def _load_ui():
    try:
        if os.path.exists(UI_PATH):
            with open(UI_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                # sanitize & merge defaults
                out = DEFAULT_UI.copy()
                if isinstance(data, dict):
                    out.update({k: v for k, v in data.items() if k in DEFAULT_UI})
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
           "cpu_percent": None, "mem_mb": None, "hostname": socket.gethostname(),
           "py": platform.python_version()}
    try:
        import psutil  # type: ignore
        try:
            out["cpu_percent"] = float(psutil.cpu_percent(interval=0.1))
        except Exception:
            out["cpu_percent"] = None
        try:
            out["mem_mb"] = int(psutil.Process().memory_info().rss/1024/1024)
        except Exception:
            out["mem_mb"] = None
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

def _safe_servers():
    path = os.getenv("SERVERS_JSON", "data/servers.json")
    try:
        if os.path.exists(path):
            return json.load(open(path, "r", encoding="utf-8"))
    except Exception:
        pass
    return {"servers": []}

@bp.get("/dashboard")
def builtin_dashboard():
    return render_template("dashboard/monitor.html")

@bp.get("/dashboard/settings")
def dashboard_settings():
    return render_template("dashboard/settings.html", ui=_load_ui())

@bp.get("/api/ui-settings")
def api_get_ui():
    return jsonify(_load_ui())

@bp.post("/api/ui-settings")
def api_set_ui():
    try:
        data = request.get_json(force=True, silent=True) or {}
        ui = _load_ui()
        for k in list(DEFAULT_UI.keys()):
            if k in data and isinstance(data[k], str):
                val = data[k].strip()
                # very basic validation for color
                if k == "accent":
                    if not val.startswith("#") or len(val) not in (4, 7):
                        continue
                if k == "theme" and val not in ("dark", "light"):
                    continue
                ui[k] = val
        ok = _save_ui(ui)
        return jsonify({"ok": ok, "ui": ui}), (200 if ok else 500)
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

@bp.get("/api/monitor")
def api_monitor(): return jsonify(_safe_monitor())

@bp.get("/api/activity")
def api_activity(): return jsonify(_safe_activity())

@bp.get("/api/servers")
def api_servers(): return jsonify(_safe_servers())

def register_webui_builtin(app):
    if BP_NAME not in app.blueprints:
        app.register_blueprint(bp)
