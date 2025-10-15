# patch_app_theme.py
# Usage: run this script in the project root (same folder as app.py):
#   python patch_app_theme.py
#
# It will:
# 1) Insert theme helpers (_current_theme_name, etc.) BEFORE @app.context_processor
# 2) Fix background upload backslash ("path.replace('\\', '/')")
# 3) Create a timestamped backup app.py.bak-YYYYmmdd-HHMMSS

import os, re, time

HELPERS_BLOCK = r"""
# ==== THEME HOTFIX (auto-injected) ====
import json, sqlite3, time
from pathlib import Path as _Path
from flask import session, url_for

THEME_DIR = _Path("static/themes")
DEFAULT_THEME = os.getenv("DEFAULT_THEME", "neo.css")

def _available_themes():
    try:
        return sorted([p.name for p in THEME_DIR.glob("*.css")])
    except Exception:
        return ["neo.css", "neon.css"]

def _theme_exists(name: str) -> bool:
    if not name:
        return False
    fn = name if name.endswith(".css") else (name + ".css")
    return (THEME_DIR / fn).exists()

def _current_theme_name():
    name = session.get("theme")
    if not name:
        try:
            with sqlite3.connect(os.getenv("DB_PATH", "superadmin.db")) as conn:
                conn.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
                row = conn.execute("SELECT value FROM settings WHERE key='ui_theme'").fetchone()
                if row and row[0]:
                    name = row[0]
        except Exception:
            pass
    if not name:
        name = os.getenv("THEME") or DEFAULT_THEME
    if not name.endswith(".css"):
        name += ".css"
    if _theme_exists(name):
        return name
    avail = _available_themes()
    return avail[0] if avail else "neo.css"

def get_theme_path():
    fn = _current_theme_name()
    return url_for("static", filename=f"themes/{fn}")

def _load_background_url():
    # 1) config/theme.json
    try:
        cfg = json.load(open("config/theme.json","r",encoding="utf-8"))
        url = (cfg.get("background_image") or "").strip()
        if url:
            return url if url.startswith(("http://","https://","/")) else ("/" + url.lstrip())
    except Exception:
        pass
    # 2) SQLite assets -> /assets/background
    try:
        with sqlite3.connect(os.getenv("DB_PATH", "superadmin.db")) as conn:
            conn.execute("CREATE TABLE IF NOT EXISTS assets(key TEXT PRIMARY KEY, mime TEXT, data BLOB, updated_at TEXT)")
            row = conn.execute("SELECT 1 FROM assets WHERE key='background'").fetchone()
            if row: return "/assets/background"
    except Exception:
        pass
    return ""
# ==== /THEME HOTFIX ====
"""

def main():
    APP = "app.py"
    if not os.path.exists(APP):
        print("app.py not found in current directory.")
        return

    with open(APP, "r", encoding="utf-8", errors="ignore") as f:
        src = f.read()

    # Backup
    ts = time.strftime("%Y%m%d-%H%M%S")
    backup = f"app.py.bak-{ts}"
    with open(backup, "w", encoding="utf-8") as b:
        b.write(src)
    print(f"[patch] Backup -> {backup}")

    # Fix backslash issues in background upload
    src = src.replace('path.replace("\\\\","/")', 'path.replace("\\\\","/")')  # idempotent
    src = src.replace('path.replace("\\","/")', 'path.replace("\\\\","/")')
    src = src.replace('path.replace("\","/")', 'path.replace("\\\\","/")')

    # Insert helpers BEFORE @app.context_processor inject_globals
    m = re.search(r"@app\.context_processor\s*?\ndef\s+inject_globals\(\):", src)
    if m:
        idx = m.start()
        if "_current_theme_name(" not in src:
            src = src[:idx] + HELPERS_BLOCK + "\n" + src[idx:]
            print("[patch] Inserted theme helpers before @app.context_processor")
        else:
            print("[patch] Helpers already present; skipping insert")
    else:
        # If not found, insert after first 'app = Flask('
        m2 = re.search(r"app\s*=\s*Flask\(", src)
        if m2 and "_current_theme_name(" not in src:
            idx = m2.end()
            src = src[:idx] + "\n\n" + HELPERS_BLOCK + "\n" + src[idx:]
            print("[patch] Inserted theme helpers after app = Flask(...)")
        else:
            print("[patch] Could not find @app.context_processor; no insert made.")

    with open(APP, "w", encoding="utf-8") as f:
        f.write(src)

    print("[patch] Done. Try: python run_local.py --threading")

if __name__ == "__main__":
    main()
