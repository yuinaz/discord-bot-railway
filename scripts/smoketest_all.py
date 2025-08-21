# scripts/smoketest_all.py
from __future__ import annotations
import os, sys, io, re, json, time, py_compile
from pathlib import Path

# ====== Konfigurasi ======
EXCLUDE_DIRS = {".git", ".venv", "venv", "__pycache__", "build", "dist"}
DASH_REQUIRED = [
    "satpambot/dashboard/webui.py",
    "satpambot/dashboard/templates/login.html",
    "satpambot/dashboard/templates/dashboard.html",
    "satpambot/dashboard/templates/security.html",
    "satpambot/dashboard/templates/settings.html",
    "satpambot/dashboard/static/css/login_exact.css",
    "satpambot/dashboard/static/css/neo_aurora_plus.css",
    "satpambot/dashboard/static/js/neo_dashboard_live.js",
    "satpambot/dashboard/static/logo.svg",
    # favicon opsional: kalau tidak ada, route harus fallback 200
    "satpambot/dashboard/themes/gtake/templates/login.html",
    "satpambot/dashboard/themes/gtake/templates/dashboard.html",
    "satpambot/dashboard/themes/gtake/static/theme.css",
    "satpambot/dashboard/live_store.py",
]
BOT_REQUIRED = [
    "satpambot/bot/modules/discord_bot/shim_runner.py",
    "satpambot/bot/modules/discord_bot/cogs/live_metrics_push.py",
]

# ====== Helpers ======
fails: list[str] = []
warns: list[str] = []

def must(cond: bool, label: str, extra: str = ""):
    ok = bool(cond)
    print(f"{'OK  ' if ok else 'FAIL'}: {label}{(' :: ' + extra) if extra else ''}")
    if not ok:
        fails.append(f"{label} {extra}")

def warn(cond: bool, label: str, extra: str = ""):
    if cond:
        print(f"WARN: {label}{(' :: ' + extra) if extra else ''}")
        warns.append(f"{label} {extra}")

def py_syntax_scan(root: Path):
    total = 0
    for p in root.rglob("*.py"):
        if any(part in EXCLUDE_DIRS for part in p.parts):
            continue
        try:
            py_compile.compile(str(p), doraise=True)
            total += 1
        except Exception as e:
            print(f"FAIL: Syntax {p} :: {e}")
            fails.append(f"syntax {p}")
    print(f"OK  : Python syntax check ({total} files)")

def check_files_exist(paths: list[str]):
    for rel in paths:
        p = Path(rel)
        must(p.exists(), f"file exists: {rel}")

def check_intents_flags(shim_path: str):
    p = Path(shim_path)
    if not p.exists():
        fails.append(f"missing {shim_path}")
        return
    t = p.read_text(encoding="utf-8", errors="ignore")
    has_members   = re.search(r"intents\.members\s*=\s*True", t) is not None
    has_presences = re.search(r"intents\.presences\s*=\s*True", t) is not None
    must(has_members,  "intents.members=True (shim_runner.py)")
    must(has_presences,"intents.presences=True (shim_runner.py)")
    if not has_presences:
        warns.append("Presence Intent belum ON di code; aktifkan juga di Developer Portal")

# ====== Mulai ======
if __name__ == "__main__":
    root = Path(".").resolve()
    print("== Smoke: syntax ==")
    py_syntax_scan(root)

    print("\n== Smoke: required files ==")
    check_files_exist(DASH_REQUIRED)
    check_files_exist(BOT_REQUIRED)
    check_intents_flags("satpambot/bot/modules/discord_bot/shim_runner.py")

    # ==== Test HTTP via Flask test_client (tanpa jalankan bot) ====
    print("\n== Smoke: HTTP endpoints via test_client ==")
    os.environ["DISABLE_BOT_RUN"] = "1"  # hindari start bot waktu test web

    try:
        import app as appmod
        a = appmod.create_app()
        c = a.test_client()
    except Exception as e:
        print("FAIL: create_app() ::", e)
        fails.append(f"create_app {e}")
        a = None
        c = None

    def expect_get(url: str, code=200, label=None):
        r = c.get(url); must(r.status_code == code, label or f"GET {url}", str(r.status_code))
        return r

    def expect_head(url: str, code=200, label=None):
        r = c.open(url, method="HEAD"); must(r.status_code == code, label or f"HEAD {url}", str(r.status_code))
        return r

    def expect_post(url: str, data=None, code=(302,303,200), label=None, follow=False):
        r = c.post(url, data=(data or {}), follow_redirects=follow)
        must(r.status_code in (code if isinstance(code,(list,tuple,set)) else (code,)), label or f"POST {url}", f"{r.status_code} -> {r.headers.get('Location')}")
        return r

    if c:
        # root redirect
        r = c.get("/")
        must(r.status_code in (301,302,307,308), "/ -> redirect", f"{r.status_code} -> {r.headers.get('Location')}")

        # login GET/POST
        r = expect_get("/dashboard/login", 200, "GET /dashboard/login")
        must(("class=\"lg-card\"" in r.data.decode()), "login layout present (lg-card)")
        expect_post("/dashboard/login", data={"username":"u","password":"p"}, code=(302,303), label="POST /dashboard/login -> redirect")

        # static essentials
        expect_get("/dashboard-static/css/login_exact.css", 200)
        expect_get("/dashboard-static/css/neo_aurora_plus.css", 200)
        expect_get("/dashboard-static/js/neo_dashboard_live.js", 200)
        # favicon (route fallback must 200)
        r = c.get("/favicon.ico")
        must(r.status_code == 200, "GET /favicon.ico", str(r.status_code))

        # health + uptime (HEAD, anti spam log)
        expect_head("/healthz", 200)
        expect_head("/uptime", 200)

        # ui-config & themes
        r = c.get("/api/ui-config"); must(r.status_code==200, "GET /api/ui-config", str(r.status_code))
        cfg = r.get_json() or {}
        r = c.get("/api/ui-themes"); must(r.status_code==200, "GET /api/ui-themes", str(r.status_code))
        themes = r.get_json() or {}
        must(("gtake" in (themes.get("themes") or [])), "theme 'gtake' available")

        # switch theme to gtake (temporary)
        prev_theme = cfg.get("theme")
        if prev_theme != "gtake":
            r = c.post("/api/ui-config", json={**cfg, "theme":"gtake"})
            must(r.status_code == 200, "switch theme -> gtake", str(r.status_code))

        # themed assets + dashboard contents
        expect_get("/dashboard-theme/gtake/theme.css", 200)
        r = expect_get("/dashboard", 200, "GET /dashboard (gtake)")
        html = r.data.decode("utf-8","ignore")
        must(("G.TAKE" in html), "dashboard layout = gtake")
        must(("id=\"activityChart\"" in html), "dashboard has 60fps canvas")
        must(("id=\"dashDrop\"" in html and "id=\"dashPick\"" in html), "dashboard has dropzone")

        # settings + security
        expect_get("/dashboard/settings", 200)
        r = expect_get("/dashboard/security", 200)
        sec_html = r.data.decode("utf-8","ignore")
        must(("id=\"dropZone\"" in sec_html and "id=\"fileInput\"" in sec_html), "security page has drag&drop")

        # live stats & phash
        r = c.get("/api/live/stats"); must(r.status_code==200, "GET /api/live/stats", str(r.status_code))
        live = r.get_json() or {}
        keys_ok = all(k in live for k in ["guilds","members","online","channels","threads","latency_ms","updated"])
        must(keys_ok, "live stats keys present")
        if keys_ok and all((live.get(k,0)==0) for k in ["guilds","members","online"]):
            warn(True, "live stats are zero (bot belum siap / intents belum aktif)")

        r = c.get("/api/phish/phash"); must(r.status_code==200, "GET /api/phish/phash", str(r.status_code))
        phash = r.get_json() or {}
        must(("phash" in phash and isinstance(phash["phash"], list)), "phash array present")

        # upload endpoints
        data = {"file": (io.BytesIO(b"dummy"), "test_dash.png")}
        r = c.post("/dashboard/upload", data=data, content_type="multipart/form-data")
        must(r.status_code==200 and r.is_json and r.get_json().get("ok") is True, "POST /dashboard/upload")

        data2 = {"file": (io.BytesIO(b"dummy2"), "test_sec.png")}
        r = c.post("/dashboard/security/upload", data=data2, content_type="multipart/form-data")
        must(r.status_code==200 and r.is_json and r.get_json().get("ok") is True, "POST /dashboard/security/upload")

        # logout + alias
        r = c.get("/logout"); must(r.status_code==200, "GET /logout", str(r.status_code))
        r = c.get("/dashboard/logout"); must(r.status_code in (301,302,303), "GET /dashboard/logout -> redirect", f"{r.status_code} -> {r.headers.get('Location')}")

        # restore theme
        if prev_theme and prev_theme != "gtake":
            r = c.post("/api/ui-config", json={**cfg, "theme": prev_theme})
            must(r.status_code == 200, "restore previous theme", str(r.status_code))

    # ===== Summary =====
    print("\n=== SUMMARY ===")
    if fails:
        print("FAILED:")
        for f in fails: print("-", f)
        if warns:
            print("\nWARNINGS:")
            for w in warns: print("-", w)
        sys.exit(1)
    else:
        if warns:
            print("WARNINGS (non-fatal):")
            for w in warns: print("-", w)
        print("All smoketests PASSED")
        sys.exit(0)
