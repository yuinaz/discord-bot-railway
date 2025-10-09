
import os, sys, compileall, importlib, traceback, json, re
from pathlib import Path

_HERE = Path(__file__).resolve()
_ROOT = _HERE.parent.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_ROOT / "scripts"))
os.environ.setdefault("SMOKE_MODE","1")

def _print_ok(msg): print(f"OK  : {msg}")
def _print_warn(msg): print(f"WARN: {msg}")
def _print_fail(msg): print(f"FAIL: {msg}")

# ---------------- syntax ----------------
print("== Smoke: syntax ==")
ok = compileall.compile_dir(str(_ROOT), maxlevels=10, quiet=1)
if not ok:
    _print_warn("compileall reported issues (continuing).")

# ---------------- imports ----------------
print("== Smoke: imports ==")
modules = [
    "satpambot.bot.modules.discord_bot.cogs.progress_embed_solo",
    "satpambot.bot.modules.discord_bot.cogs.phash_db_command_single",
    "satpambot.bot.modules.discord_bot.cogs.shadow_learn_observer",
    "satpambot.bot.modules.discord_bot.cogs.rl_shim_history",
    "satpambot.bot.modules.discord_bot.cogs.log_autodelete_bot",
    "satpambot.bot.utils.embed_scribe",
    "satpambot.bot.utils.dupe_guard",
    "satpambot.ml.neuro_lite_memory_fix",
    "satpambot.ml.shadow_metrics",
    "satpambot.ml.groq_helper",
    "satpambot.config.compat_conf",
    "satpambot.config.runtime_memory",
]
failed = []
for m in modules:
    try:
        importlib.import_module(m)
        print(f"[OK] import {m}")
    except Exception as e:
        failed.append((m, e))
        print(f"[FAIL] {m}: {e}")
        traceback.print_exc()

if failed:
    sys.exit(1)

# ---------------- dummy bot setup ----------------
print("== Smoke: dummy setup ==")
try:
    from scripts.smoke_utils import DummyBot, retrofit
    bot = retrofit(DummyBot())
    import asyncio
    async def _load():
        await (importlib.import_module("satpambot.bot.modules.discord_bot.cogs.progress_embed_solo").setup(bot))
        await (importlib.import_module("satpambot.bot.modules.discord_bot.cogs.phash_db_command_single").setup(bot))
        await (importlib.import_module("satpambot.bot.modules.discord_bot.cogs.shadow_learn_observer").setup(bot))
    asyncio.get_event_loop().run_until_complete(_load())
    print("[OK] cogs setup with DummyBot")
except Exception as e:
    print(f"[FAIL] dummy setup: {e}")
    sys.exit(1)

# ---------------- required files ----------------
print("\n== Smoke: required files ==")
required = [
    "satpambot/dashboard/webui.py",
    "satpambot/dashboard/templates/login.html",
    "satpambot/dashboard/templates/dashboard.html",
    "satpambot/dashboard/templates/security.html",
    "satpambot/dashboard/templates/settings.html",
    "satpambot/dashboard/static/css/login_exact.css",
    "satpambot/dashboard/static/css/neo_aurora_plus.css",
    "satpambot/dashboard/static/js/neo_dashboard_live.js",
    "satpambot/dashboard/static/logo.svg",
    "satpambot/dashboard/themes/gtake/templates/login.html",
    "satpambot/dashboard/themes/gtake/templates/dashboard.html",
    "satpambot/dashboard/themes/gtake/static/theme.css",
    "satpambot/dashboard/live_store.py",
    "satpambot/bot/modules/discord_bot/shim_runner.py",
    "satpambot/bot/modules/discord_bot/cogs/live_metrics_push.py",
]
for rel in required:
    p = _ROOT / rel
    if p.exists():
        _print_ok(f"file exists: {rel}")
    else:
        _print_warn(f"missing: {rel}")

# intents checks (best-effort)
shim = _ROOT / "satpambot/bot/modules/discord_bot/shim_runner.py"
if shim.exists():
    text = shim.read_text(encoding="utf-8", errors="ignore")
    msg = []
    if re.search(r"intents\s*\.\s*members\s*=\s*True", text): msg.append("intents.members=True (shim_runner.py)")
    else: msg.append("intents.members not True")
    if re.search(r"intents\s*\.\s*presences\s*=\s*True", text): msg.append("intents.presences=True (shim_runner.py)")
    else: msg.append("intents.presences not True")
    for m in msg:
        if "not" in m: _print_warn(m)
        else: print("OK   :", m)
else:
    _print_warn("shim_runner.py not found; skip intents check")

# ---------------- JSON validity ----------------
print("== Smoke: json ==")
json_candidates = [
    "satpambot_config.local.json",
    "config/satpambot_config.local.json",
    "data/config/satpambot_config.local.json",
    "satpambot.local.json",
    "data/neuro-lite/learn_progress_junior.json",
    "data/neuro-lite/learn_progress_senior.json",
    "data/neuro-lite/observe_metrics.json",
    "data/phash/SATPAMBOT_PHASH_DB_V1.json",
    "data/state/embed_scribe.json",
]
all_valid = True
for rel in json_candidates:
    p = _ROOT / rel
    if not p.exists():
        _print_warn(f"json missing: {rel}")
        all_valid = False
        continue
    try:
        json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        _print_fail(f"json invalid: {rel} :: {e}")
        all_valid = False
if all_valid:
    _print_ok("All JSON files valid/exist")

# ---------------- upsert call-sites ----------------
print("== Smoke: upsert call-sites ==")
bad = 0; good = 0
pat_upsert = re.compile(r"\.upsert\s*\(")
pat_channel_first = re.compile(r"""\(\s*[a-zA-Z_][a-zA-Z0-9_.]*\s*,\s*["'][^"']+["']\s*,\s*discord\.Embed""")
pat_legacy = re.compile(r"""\(\s*bot\s*,\s*[a-zA-Z_][a-zA-Z0-9_]*\s*, """)
for p in _ROOT.rglob("*.py"):
    try:
        text = p.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        continue
    for m in pat_upsert.finditer(text):
        window = text[m.start():m.start()+220]
        if pat_channel_first.search(window) or pat_legacy.search(window):
            good += 1
        else:
            bad += 1
if bad == 0:
    _print_ok("All upsert call-sites use channel-first or legacy bot,ch pattern")
else:
    _print_warn(f"{bad} upsert call-site(s) look unusual")

# ---------------- features (sitecustomize) ----------------
print("== Smoke: features ==")
sitecustom = _ROOT / "sitecustomize.py"
if not sitecustom.exists():
    _print_warn("sitecustomize.py: /healthz not exposed")
else:
    _print_ok("sitecustomize.py present")

# ---------------- HTTP endpoints via test_client ----------------
print("\n== Smoke: HTTP endpoints via test_client ==")
http_state = {"ok": True}
try:
    webui = importlib.import_module("satpambot.dashboard.webui")
except Exception as e:
    print("WARN: satpambot.dashboard.webui not importable, skipping HTTP smoke")
    webui = None

def _detect_app(webui):
    cand_names = ["app","application","api","fastapi","web","server","flask_app","fastapi_app"]
    for name in cand_names:
        obj = getattr(webui, name, None)
        if obj is None: continue
        mod = getattr(obj.__class__, "__module__", "").lower()
        if "flask" in mod or "fastapi" in mod or "starlette" in mod:
            return obj

    factories = ["create_app","build_app","make_app","init_app","factory","as_app"]
    for fn in factories:
        f = getattr(webui, fn, None)
        if callable(f):
            try:
                return f(testing=True)
            except TypeError:
                try: return f()
                except Exception: pass

    try:
        from flask import Flask, Blueprint
        for name, obj in vars(webui).items():
            if isinstance(obj, Blueprint):
                app = Flask(__name__)
                app.register_blueprint(obj)
                return app
    except Exception:
        pass
    return None

if webui is not None:
    app = _detect_app(webui)
    if app is None:
        print("WARN: No Flask/FastAPI app found in webui module. Skipping HTTP checks.")
    else:
        from scripts.http_smoke_utils import HttpSmokeClient
        client = HttpSmokeClient(app)

        def check(desc, fn):
            try:
                ok, info = fn()
                if ok:
                    print(f"OK  : {desc}")
                else:
                    print(f"WARN: {desc} :: {info}")
            except Exception as e:
                http_state["ok"] = False
                print(f"FAIL: {desc} :: {e}")

        # root
        check("/ -> redirect or 200", lambda: client.assert_status(client.get("/"), [200,302]))
        # login
        def _login():
            r = client.get("/dashboard/login")
            good, code = client.assert_status(r, [200])
            if not good: return False, code
            body = (r.text if hasattr(r,"text") else getattr(r,"data",b"").decode("utf-8","ignore"))
            return ("lg-card" in body or "login" in body.lower()), "layout missing"
        check("GET /dashboard/login :: 200 & layout", _login)
        # static
        for path in ["/dashboard-static/css/login_exact.css",
                     "/dashboard-static/css/neo_aurora_plus.css",
                     "/dashboard-static/js/neo_dashboard_live.js",
                     "/favicon.ico"]:
            check(f"GET {path} :: 200", lambda p=path: client.assert_status(client.get(p), [200]))
        # healthz/uptime
        check("HEAD /healthz :: 200", lambda: client.assert_status(client.head("/healthz"), [200]))
        check("HEAD /uptime :: 200", lambda: client.assert_status(client.head("/uptime"), [200]))
        # APIs
        check("GET /api/ui-config :: 200", lambda: client.assert_status(client.get("/api/ui-config"), [200]))
        def _themes():
            r = client.get("/api/ui-themes")
            ok, code = client.assert_status(r, [200])
            if not ok: return False, code
            data = client.json(r)
            present = False
            if isinstance(data, (list, dict)):
                s = str(data).lower()
                present = ("gtake" in s) or ("themes" in s)
            return present, "theme not listed"
        check("GET /api/ui-themes :: 200", _themes)
        check("GET /dashboard-theme/gtake/theme.css :: 200",
              lambda: client.assert_status(client.get("/dashboard-theme/gtake/theme.css"), [200]))
        def _live_stats():
            r = client.get("/api/live/stats")
            ok, code = client.assert_status(r, [200])
            if not ok: return False, code
            data = client.json(r) or {}
            has_keys = isinstance(data, dict) and any(k in data for k in ("uptime","cpu","memory","status","ok"))
            return has_keys, "live stats keys missing"
        check("GET /api/live/stats :: 200", _live_stats)
        # optional
        check("GET /api/phish/phash :: 200/404", lambda: client.assert_status(client.get("/api/phish/phash"), [200,404]))
        check("GET /logout :: 200/302", lambda: client.assert_status(client.get("/logout"), [200,302]))
        check("GET /dashboard/logout -> redirect :: 302/200",
              lambda: client.assert_status(client.get("/dashboard/logout"), [200,302]))

print("\n=== SUMMARY ===")
if failed:
    print("FAILED:")
    for m, e in failed:
        print(f"- import: {m} -> {e}")
    sys.exit(1)
try:
    if 'webui' in globals() and webui and http_state.get("ok") is False:
        print("FAILED: HTTP smoke")
        sys.exit(1)
except Exception:
    pass
