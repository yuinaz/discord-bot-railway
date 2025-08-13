
# assets_manager.py — Blueprint untuk manajemen Background & Logo (dengan pagination)
import os, sqlite3, json
from flask import Blueprint, request, jsonify, render_template, send_file, abort, redirect, url_for, current_app
from io import BytesIO
from datetime import datetime

assets_bp = Blueprint("assets_bp", __name__)

DB_PATH = os.getenv("DB_PATH", "superadmin.db")

def _get_conn():
    return sqlite3.connect(DB_PATH)

def _ensure_tables():
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS asset_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,        -- 'background' | 'logo'
                filename TEXT,
                mime TEXT,
                url TEXT,                      -- optional: URL dari webhook/remote
                data BLOB,                     -- optional: binary
                is_active INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_asset_history_cat_created ON asset_history(category, created_at DESC)
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS assets (
                key TEXT PRIMARY KEY,          -- 'background' | 'logo'
                mime TEXT,
                data BLOB,
                updated_at TEXT
            )
        """)
        conn.commit()

def _row_to_dict(r):
    return {
        "id": r[0],
        "category": r[1],
        "filename": r[2],
        "mime": r[3],
        "url": r[4],
        "has_data": bool(r[5]),
        "is_active": bool(r[6]),
        "created_at": r[7],
    }

def _active_url_for(category, row):
    # Jika ada URL remote gunakan itu; selainnya pakai /assets/<category>
    # background -> /assets/background ; logo -> /assets/logo (harap app.py sudah punya route tsb)
    if row and row.get("url"):
        return row["url"]
    if category == "background":
        return "/assets/background"
    if category == "logo":
        return "/assets/logo"
    return ""

@assets_bp.route("/assets-manager")
def page_assets_manager():
    _ensure_tables()
    return render_template("settings_assets.html")

@assets_bp.get("/api/assets")
def api_assets_list():
    _ensure_tables()
    category = request.args.get("category", "background")
    page = max(int(request.args.get("page", 1)), 1)
    per = min(max(int(request.args.get("per", 12)), 1), 60)
    offset = (page - 1) * per
    with _get_conn() as conn:
        cur = conn.execute("SELECT COUNT(*) FROM asset_history WHERE category=?", (category,))
        total = cur.fetchone()[0] or 0
        rows = conn.execute(
            "SELECT id,category,filename,mime,url,data,is_active,created_at FROM asset_history WHERE category=? ORDER BY datetime(created_at) DESC LIMIT ? OFFSET ?",
            (category, per, offset),
        ).fetchall()
    items = [_row_to_dict(r) for r in rows]
    # Buat URL untuk preview tiap item
    for it in items:
        it["preview_url"] = it["url"] if it["url"] else f"/assets/item/{it['id']}"
    return jsonify({"ok": True, "page": page, "per": per, "total": total, "items": items})

@assets_bp.get("/assets/item/<int:item_id>")
def api_assets_get_item(item_id: int):
    _ensure_tables()
    with _get_conn() as conn:
        r = conn.execute("SELECT id,category,filename,mime,url,data,is_active,created_at FROM asset_history WHERE id=?", (item_id,)).fetchone()
    if not r:
        abort(404)
    d = _row_to_dict(r)
    if d["url"]:
        return redirect(d["url"], code=302)
    if not d["has_data"]:
        abort(404)
    return send_file(BytesIO(r[5]), mimetype=d["mime"] or "application/octet-stream", download_name=d["filename"] or f"{d['category']}.bin")

@assets_bp.post("/api/assets/activate")
def api_assets_activate():
    _ensure_tables()
    body = request.get_json(silent=True) or {}
    item_id = int(body.get("id", 0))
    if not item_id:
        return jsonify({"ok": False, "error": "missing id"}), 400
    with _get_conn() as conn:
        r = conn.execute("SELECT id,category,filename,mime,url,data,is_active,created_at FROM asset_history WHERE id=?", (item_id,)).fetchone()
        if not r:
            return jsonify({"ok": False, "error": "not found"}), 404
        d = _row_to_dict(r)
        category = d["category"]
        # Set aktif pada history
        conn.execute("UPDATE asset_history SET is_active=0 WHERE category=?", (category,))
        conn.execute("UPDATE asset_history SET is_active=1 WHERE id=?", (item_id,))
        # Update table assets (aktif)
        if category in ("background", "logo"):
            if d["url"]:
                # jika remote URL, kosongkan BLOB dan biarkan app pakai URL remote untuk UI (background via config/theme.json)
                conn.execute("REPLACE INTO assets(key,mime,data,updated_at) VALUES (?,?,?,?)",
                             (category, d["mime"], None, datetime.utcnow().isoformat()))
                # Update config untuk background agar UI mengikuti URL
                if category == "background":
                    try:
                        os.makedirs("config", exist_ok=True)
                        path = os.path.join("config","theme.json")
                        cfg = {}
                        if os.path.exists(path):
                            import json
                            cfg = json.load(open(path,"r",encoding="utf-8"))
                        cfg["background_image"] = d["url"]
                        json.dump(cfg, open(path,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
                    except Exception:
                        pass
            else:
                # simpan blob aktif
                conn.execute("REPLACE INTO assets(key,mime,data,updated_at) VALUES (?,?,?,?)",
                             (category, d["mime"], r[5], datetime.utcnow().isoformat()))
        conn.commit()

    # Emit Socket.IO event (jika ada)
    try:
        socketio = current_app.extensions.get("socketio")
        if socketio:
            socketio.emit("asset_updated", {"category": d["category"], "url": _active_url_for(d["category"], d)}, broadcast=True)
    except Exception:
        pass

    return jsonify({"ok": True})

@assets_bp.delete("/api/assets/<int:item_id>")
def api_assets_delete(item_id: int):
    _ensure_tables()
    with _get_conn() as conn:
        r = conn.execute("SELECT id,category,is_active FROM asset_history WHERE id=?", (item_id,)).fetchone()
        if not r:
            return jsonify({"ok": False, "error": "not found"}), 404
        if r[2]:  # is_active
            return jsonify({"ok": False, "error": "cannot delete active item"}), 409
        conn.execute("DELETE FROM asset_history WHERE id=?", (item_id,))
        conn.commit()
    return jsonify({"ok": True})
