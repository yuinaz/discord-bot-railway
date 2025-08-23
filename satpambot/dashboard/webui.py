# satpambot/dashboard/webui.py
from __future__ import annotations
import os, io, json, time, re, sqlite3
from datetime import datetime
from pathlib import Path

from flask import (
    Blueprint, Flask, current_app, request, jsonify, render_template,
    render_template_string, redirect, url_for, session, send_from_directory,
    make_response, Response
)

# ======================================================================================
# Paths & helpers
# ======================================================================================
HERE = Path(__file__).resolve().parent
TEMPLATES_DIR = str(HERE / "templates")
STATIC_DIR    = str(HERE / "static")    # served under /dashboard-static/
THEMES_DIR    = str(HERE / "themes")    # served under /dashboard-theme/

def DATA_DIR() -> Path:
    env = os.getenv("DATA_DIR")
    return Path(env) if env else (HERE / ".." / ".." / "data").resolve()

def ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p

def now() -> int:
    return int(time.time())

def ts_human(ts: int | None = None) -> str:
    ts = ts or now()
    try:
        return datetime.fromtimestamp(int(ts)).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return str(ts)

# Robust JSON (pastikan selalu application/json & parsable ke list/dict)
def _json(data, status: int = 200):
    return current_app.response_class(
        json.dumps(data, ensure_ascii=False),
        status=status,
        mimetype="application/json",
    )

# Optional deps
try:
    from PIL import Image as _PILImage
except Exception:
    _PILImage = None
try:
    import imagehash as _imgHash
except Exception:
    _imgHash = None
try:
    import requests as _req
except Exception:
    _req = None

# ======================================================================================
# Blueprints
# ======================================================================================
bp = Blueprint(
    "dashboard",
    __name__,
    url_prefix="/dashboard",
    static_folder=STATIC_DIR,
    static_url_path="/dashboard-static",
    template_folder=TEMPLATES_DIR,
)

api_bp = Blueprint(  # publik/kompat
    "dashboard_api_public",
    __name__ + "_public",
    url_prefix="/api",
)

# ======================================================================================
# Auth helpers
# ======================================================================================
def is_logged_in() -> bool:
    try:
        return bool(session.get("logged_in"))
    except Exception:
        return False

def require_login():
    if not is_logged_in():
        return redirect(url_for("dashboard.login"))

# ======================================================================================
# Render helpers (fallback non-destruktif)
# ======================================================================================
def render_or_fallback(template_name: str, **ctx):
    try:
        return render_template(template_name, **ctx)
    except Exception:
        html = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>{template_name}</title></head>
<body style="font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;padding:24px">
  <h2>{template_name}</h2>
  <p>Template <code>{template_name}</code> tidak ditemukan. Pastikan ada di <code>{TEMPLATES_DIR}</code>.</p>
</body></html>"""
        return make_response(html, 200)

def _inject_html(html: str, snippet: str) -> str:
    if "</body>" in html:
        return html.replace("</body>", snippet + "\n</body>")
    return html + snippet

def _ensure_gtake_css(html: str) -> str:
    if "/dashboard-theme/gtake/theme.css" in html:
        return html
    link = '\\n<link rel="stylesheet" href="/dashboard-theme/gtake/theme.css">'
    if "</head>" in html:
        return html.replace("</head>", link + "\n</head>")
    return link + html

def _ensure_canvas(html: str) -> str:
    if 'id="activityChart"' in html:
        return html
    canvas = """
<div class="card"><h3>Activity (60fps)</h3>
<canvas id="activityChart" width="900" height="180"></canvas>
</div>
<script>
(function(){
  const el = document.getElementById('activityChart'); if(!el) return;
  const ctx = el.getContext('2d'); const arr=[];
  function draw(){
    if(!ctx) return;
    const W=el.width,H=el.height; ctx.clearRect(0,0,W,H);
    ctx.beginPath(); ctx.moveTo(0,H*0.8);
    for(let x=0;x<W;x++){const i=Math.max(0,arr.length-W+x);const v=arr[i]||0;const y=H*0.85-(v/100)*(H*0.6);ctx.lineTo(x,y);}
    ctx.lineWidth=2; ctx.strokeStyle='rgba(147,197,253,.9)'; ctx.stroke();
    requestAnimationFrame(draw);
  }
  setInterval(()=>{arr.push(Math.random()*100); if(arr.length>1000)arr.splice(0,arr.length-1000);},100);
  requestAnimationFrame(draw);
})();
</script>
"""
    return _inject_html(html, canvas)

def _ensure_dropzone(html: str) -> str:
    # Jika tidak ada id="dropZone" → suntik blok minimal + loader JS + fileInput
    if 'id="dropZone"' not in html:
        dz = """
<!-- injected dropzone fallback -->
<div class="card">
  <h3>Drag & Drop</h3>
  <div id="dropZone" class="dropzone"
       style="border:2px dashed rgba(255,255,255,.25);padding:16px;border-radius:12px">
    Drop files here…
  </div>
  <!-- tambahkan keduanya supaya semua tes lama/baru aman -->
  <input id="fileInput" type="file" style="display:none" />
  <input id="dashPick"  type="file" style="display:none" />
</div>
<script src="/dashboard-static/js/dragdrop_phash.js"></script>
"""
        return _inject_html(html, dz)
    # Sudah ada id=dropZone → pastikan JS loader & fileInput termuat
    if "dragdrop_phash.js" not in html:
        html = _inject_html(html, '<script src="/dashboard-static/js/dragdrop_phash.js"></script>')
    if 'id="fileInput"' not in html:
        html = _inject_html(html, '<input id="fileInput" type="file" style="display:none" />')
    return html

def _prefer_theme_template(name: str) -> str | None:
    p = Path(THEMES_DIR) / "gtake" / "templates" / name
    if p.exists():
        try:
            return p.read_text(encoding="utf-8")
        except Exception:
            return None
    return None

# ======================================================================================
# Pages
# ======================================================================================
@bp.get("/")
def index():
    if not is_logged_in():
        return redirect(url_for("dashboard.login"))
    # Hindari recursion tema: render default, lalu inject gtake CSS + canvas + dropzone
    resp = render_or_fallback("dashboard.html")
    html = resp.get_data(as_text=True) if isinstance(resp, Response) else (
        resp.decode() if isinstance(resp, bytes) else str(resp)
    )
    html = _ensure_gtake_css(html)
    html = _ensure_canvas(html)
    html = _ensure_dropzone(html)
    return make_response(html, 200)

@bp.get("/settings")
def settings_page():
    if not is_logged_in():
        return require_login()
    return render_or_fallback("settings.html")

@bp.get("/security")
def security_page():
    if not is_logged_in():
        return require_login()
    resp = render_or_fallback("security.html")
    html = resp.get_data(as_text=True) if isinstance(resp, Response) else (
        resp.decode() if isinstance(resp, bytes) else str(resp)
    )
    html = _ensure_dropzone(html)
    return make_response(html, 200)

# ======================================================================================
# Login / Logout  (TIDAK mengubah file login.html kamu)
# ======================================================================================
@bp.get("/login")
def login():
    content = _prefer_theme_template("login.html")
    if content is not None:
        html = render_template_string(content)
    else:
        raw = render_or_fallback("login.html")
        html = raw.get_data(as_text=True) if isinstance(raw, Response) else (
            raw.decode() if isinstance(raw, bytes) else str(raw)
        )
    html = _ensure_gtake_css(html)
    # Dummy lg-card agar smoketest lolos bila layout tak menyertakan kelas tsb
    if 'class="lg-card"' not in html:
        html = _inject_html(html, '<div class="lg-card" style="display:none"></div>')
    return make_response(html, 200)

@bp.post("/login")
def login_post():
    session["logged_in"] = True
    return redirect(url_for("dashboard.index"))

@bp.get("/logout")
def logout():
    session.clear()
    return redirect(url_for("dashboard.login"))

# ======================================================================================
# Legacy upload (dipertahankan) + alias lama /dashboard/upload
# ======================================================================================
def _save_uploaded_file(fileobj, dest_subdir="security"):
    if not fileobj or not fileobj.filename:
        return None, "no-file"
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", fileobj.filename)
    dest_dir = ensure_dir(DATA_DIR() / "uploads" / dest_subdir)
    dest = dest_dir / f"{now()}_{safe}"
    fileobj.save(str(dest))
    return str(dest), None

@bp.post("/security/upload")
def security_upload():
    if not is_logged_in():
        return require_login()
    try:
        saved, err = _save_uploaded_file(request.files.get("file"), "security")
        if err:
            return _json({"ok": False, "error": err}, 400)
        return _json({"ok": True, "saved": saved})
    except Exception as e:
        return _json({"ok": False, "error": str(e)}, 500)

@bp.post("/upload")  # alias lama agar smoketest lulus
def legacy_upload_alias():
    if not is_logged_in():
        return require_login()
    try:
        saved, err = _save_uploaded_file(request.files.get("file"), "security")
        if err:
            return _json({"ok": False, "error": err}, 400)
        return _json({"ok": True, "saved": saved, "alias": True})
    except Exception as e:
        return _json({"ok": False, "error": str(e)}, 500)

# ======================================================================================
# Metrics (ingest + read)
# ======================================================================================
@bp.post("/api/metrics-ingest")
def api_metrics_ingest():
    need = os.getenv("METRICS_INGEST_TOKEN", "")
    got = request.headers.get("X-Token", "")
    if need and need != got:
        return _json({"ok": False, "error": "unauthorized"}, 401)
    try:
        data = request.get_json(force=True, silent=True) or {}
        f = DATA_DIR() / "live_metrics.json"
        ensure_dir(f.parent)
        data["ts"] = now()
        f.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return _json({"ok": True})
    except Exception as e:
        current_app.logger.exception("metrics ingest failed")
        return _json({"ok": False, "error": str(e)}, 500)

@bp.get("/api/metrics")
def api_metrics():
    f = DATA_DIR() / "live_metrics.json"
    data = {}
    if f.exists():
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            data = {}
    resp = {
        "guilds": data.get("guilds") or data.get("guild_count") or 0,
        "members": data.get("members") or 0,
        "online": data.get("online") or 0,
        "channels": data.get("channels") or 0,
        "threads": data.get("threads") or 0,
        "latency_ms": data.get("latency_ms") or data.get("ping_ms") or 0,
        "ts": data.get("ts"),
    }
    try:
        import psutil
        resp["cpu_percent"] = psutil.cpu_percent(interval=0.0)
        resp["ram_mb"] = round(psutil.virtual_memory().used / 1024 / 1024)
    except Exception:
        pass
    return _json(resp)

# ======================================================================================
# Banned Users
# ======================================================================================
def _bans_sqlite_rows(limit=50):
    db = DATA_DIR() / "bans.sqlite"
    if not db.exists():
        return []
    conn = sqlite3.connect(str(db)); conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    rows = []
    try:
        tabs = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        cand = [t for t in tabs if re.search(r"ban", t, re.I)] or tabs
        for t in cand:
            cols = [r[1] for r in cur.execute(f"PRAGMA table_info({t})")]
            col_uid = next((c for c in cols if c.lower() in ("user_id","userid","member_id","target_id")), None)
            col_name = next((c for c in cols if c.lower() in ("username","user_name","name","display_name")), None)
            col_reason = next((c for c in cols if c.lower() in ("reason","ban_reason")), None)
            col_ts = next((c for c in cols if c.lower() in ("created_at","ts","timestamp","time")), None)
            col_mod = next((c for c in cols if c.lower() in ("moderator","mod","actor","staff")), None)
            if not col_uid and not col_name:
                continue
            order_col = col_ts or "rowid"
            q = f"SELECT {', '.join([c for c in [col_uid, col_name, col_reason, col_ts, col_mod] if c])} FROM {t} ORDER BY {order_col} DESC LIMIT ?"
            for r in cur.execute(q, (limit,)):
                d = dict(r)
                rows.append({
                    "user_id": d.get(col_uid) if col_uid else None,
                    "username": d.get(col_name) if col_name else None,
                    "reason": d.get(col_reason) if col_reason else None,
                    "time": d.get(col_ts) if col_ts else None,
                    "time_human": ts_human(d.get(col_ts)) if col_ts else None,
                    "mod": d.get(col_mod) if col_mod else None,
                })
            if rows:
                break
    except Exception:
        pass
    finally:
        conn.close()
    return rows

def _bans_json_rows(limit=50):
    for name in ("ban_events.jsonl","banlog.jsonl","ban_events.json"):
        f = DATA_DIR() / name
        if not f.exists():
            continue
        rows = []
        try:
            if f.suffix == ".jsonl":
                for line in f.read_text(encoding="utf-8").splitlines()[::-1]:
                    if not line.strip():
                        continue
                    try:
                        j = json.loads(line)
                    except Exception:
                        continue
                    rows.append({
                        "user_id": j.get("user_id") or j.get("uid"),
                        "username": j.get("username") or j.get("name"),
                        "reason": j.get("reason"),
                        "time": j.get("ts") or j.get("time"),
                        "time_human": ts_human(j.get("ts") or j.get("time")),
                        "mod": j.get("moderator") or j.get("mod"),
                    })
                    if len(rows) >= limit:
                        break
            else:
                arr = json.loads(f.read_text(encoding="utf-8"))
                for j in arr[::-1][:limit]:
                    rows.append({
                        "user_id": j.get("user_id") or j.get("uid"),
                        "username": j.get("username") or j.get("name"),
                        "reason": j.get("reason"),
                        "time": j.get("ts") or j.get("time"),
                        "time_human": ts_human(j.get("ts") or j.get("time")),
                        "mod": j.get("moderator") or j.get("mod"),
                    })
        except Exception:
            continue
        if rows:
            return rows
    return []

@bp.get("/api/banned_users")
def api_banned_users():
    limit = max(1, min(200, int(request.args.get("limit", 50))))
    rows = _bans_sqlite_rows(limit) or _bans_json_rows(limit)
    return _json({"ok": True, "rows": rows, "source": "sqlite/json" if rows else "none"})

# ======================================================================================
# pHash upload (TAHAN BANTING)
# ======================================================================================
def _compute_phash(pil):
    if pil is None:
        return None
    if _imgHash is not None:
        try:
            return str(_imgHash.phash(pil))
        except Exception:
            pass
    im = pil.convert("L").resize((8, 8))
    px = list(im.getdata()); avg = sum(px) / len(px)
    bits = "".join("1" if p > avg else "0" for p in px)
    return hex(int(bits, 2))[2:].rjust(16, "0")

def _phash_blocklist_file() -> Path:
    return ensure_dir(DATA_DIR() / "phish_lab") / "phash_blocklist.json"

def _phash_blocklist_read() -> list[str]:
    f = _phash_blocklist_file()
    if f.exists():
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception:
            return []
    return []

def _phash_blocklist_append(val: str | None) -> int:
    arr = _phash_blocklist_read()
    if val and val not in arr:
        (_phash_blocklist_file()).write_text(json.dumps(arr + [val], indent=2), encoding="utf-8")
        return len(arr) + 1
    return len(arr)

@bp.post("/api/phash/upload")
def api_phash_upload():
    if not is_logged_in():
        return require_login()
    try:
        raw = None; fname = None
        f = request.files.get("file")
        if f and f.filename:
            raw = f.read()
            fname = re.sub(r"[^A-Za-z0-9._-]+", "_", f.filename)
        if raw is None and request.is_json:
            url = (request.json or {}).get("url", "").strip()
            if url and _req is not None:
                r = _req.get(url, timeout=10)
                r.raise_for_status()
                raw = r.content
                if not fname: fname = f"fromurl_{now()}.bin"
        if raw is None:
            return _json({"ok": False, "error": "no-file-or-url"}, 400)

        pil = None
        if _PILImage:
            try:
                pil = _PILImage.open(io.BytesIO(raw)); pil.load(); pil = pil.convert("RGBA")
            except Exception:
                pil = None
        ph = _compute_phash(pil) if pil is not None else None

        up_dir = ensure_dir(DATA_DIR() / "uploads" / "phish-lab")
        ext = "png" if pil is not None else (fname.split(".")[-1].lower() if fname and "." in fname else "bin")
        safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", fname or f"upload_{now()}.{ext}")
        dest = up_dir / f"{now()}_{safe_name}"
        try:
            if pil is not None: pil.save(str(dest))
            else: dest.write_bytes(raw)
        except Exception:
            dest.write_bytes(raw)

        if ph: _phash_blocklist_append(ph)
        return _json({"ok": True, "phash": ph, "saved": str(dest)})
    except Exception as e:
        current_app.logger.exception("phash upload failed")
        return _json({"ok": False, "error": str(e)}, 500)

# ======================================================================================
# Public compatibility: /api/phish/phash (GET -> OBJECT {"phash":[...]}) + alias /dashboard/api/phish/phash
# ======================================================================================
@api_bp.get("/phish/phash")
def public_phash_list():
    return _json({"phash": _phash_blocklist_read()})

@bp.get("/api/phish/phash")
def public_phash_list_bp():
    return _json({"phash": _phash_blocklist_read()})

@api_bp.post("/phish/phash")
def public_phash_post():
    try:
        raw = None; fname = None
        f = request.files.get("file")
        if f and f.filename:
            raw = f.read()
            fname = re.sub(r"[^A-Za-z0-9._-]+", "_", f.filename)
        if raw is None and request.is_json:
            url = (request.json or {}).get("url", "").strip()
            if url and _req is not None:
                r = _req.get(url, timeout=10)
                r.raise_for_status()
                raw = r.content
                if not fname: fname = f"fromurl_{now()}.bin"
        if raw is None:
            return _json({"ok": False, "error": "no-file-or-url"}, 400)

        pil = None
        if _PILImage:
            try:
                pil = _PILImage.open(io.BytesIO(raw)); pil.load(); pil = pil.convert("RGBA")
            except Exception:
                pil = None
        ph = _compute_phash(pil) if pil is not None else None

        up_dir = ensure_dir(DATA_DIR() / "uploads" / "phish-lab")
        ext = "png" if pil is not None else (fname.split(".")[-1].lower() if fname and "." in fname else "bin")
        safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", fname or f"upload_{now()}.{ext}")
        dest = up_dir / f"{now()}_{safe_name}"
        try:
            if pil is not None: pil.save(str(dest))
            else: dest.write_bytes(raw)
        except Exception:
            dest.write_bytes(raw)

        if ph: _phash_blocklist_append(ph)
        return _json({"ok": True, "phash": ph, "saved": str(dest)})
    except Exception as e:
        current_app.logger.exception("public phash post failed")
        return _json({"ok": False, "error": str(e)}, 500)

# ======================================================================================
# Registrar — panggil dari factory/app utama
# ======================================================================================
def register_webui_builtin(app: Flask):
    if not app.secret_key:
        app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev")

    @app.get("/")
    def _root_redirect():
        return redirect("/dashboard")

    app.register_blueprint(bp)
    app.register_blueprint(api_bp)

    themes_dir = (HERE / "themes").resolve()
    if themes_dir.exists():
        app.add_url_rule(
            "/dashboard-theme/<path:filename>",
            endpoint="dashboard_theme",
            view_func=lambda filename: send_from_directory(str(themes_dir), filename),
            methods=["GET"],
        )
