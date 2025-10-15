
import os, importlib, json
from urllib.parse import urlparse
os.environ.setdefault("DISABLE_BOT_RUN", "1")  # if respected by user's app
try:
    import app
    create_app = app.create_app
    print("[ok] create_app sumber: app.create_app")
except Exception as e:
    print("[warn] gagal import app.create_app:", e)
    from satpambot.dashboard.webui import register_webui_builtin
    from flask import Flask
    def create_app():
        app = Flask("satpambot_dashboard")
        register_webui_builtin(app)
        return app
    print("[ok] pakai fallback Flask minimal")

a = create_app()
try:
    # ensure our dashboard registered
    from satpambot.dashboard.webui import register_webui_builtin
    register_webui_builtin(a)
except Exception:
    pass
c = a.test_client()

def assert_status(method, path, code):
    r = c.open(path, method=method)
    if r.status_code != code:
        raise AssertionError(f"FAIL {method} {path} :: {r.status_code}")
    print("OK", method, path, "::", code)
    return r

# Basic routes
r = assert_status("GET", "/", 302)
assert r.headers.get("Location") == "/dashboard"
assert_status("GET", "/dashboard/login", 200)
r = c.post("/dashboard/login", data={"username":"admin","password":"admin"}, follow_redirects=False)
# either 303 or 302 depending on stack
assert r.status_code in (302,303)
assert "/dashboard" in (r.headers.get("Location") or "")

# Access dashboard
with c.session_transaction() as s: s["logged_in"]=True
assert_status("GET", "/dashboard", 200)
assert_status("GET", "/dashboard/settings", 200)
assert_status("GET", "/dashboard/security", 200)
assert_status("GET", "/api/ui-config", 200)
assert_status("GET", "/api/ui-themes", 200)
assert_status("GET", "/dashboard-theme/gtake/theme.css", 200)

# Static
assert_status("GET", "/dashboard-static/css/login_exact.css", 200)
assert_status("GET", "/dashboard-static/js/neo_dashboard_live.js", 200)
assert_status("GET", "/favicon.ico", 200)

print("All smoketests PASSED")
