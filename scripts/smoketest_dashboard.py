#!/usr/bin/env python
# Smoketest dashboard (tanpa jalanin bot)
import os, sys, traceback

# --- pastikan kita bisa import app.py di root repo
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# --- matikan bot saat test (set SEBELUM import app)
os.environ.setdefault("DISABLE_BOT_RUN", "1")

try:
    import app  # harus ada app.py di root
except Exception:
    print(f"FAIL: tidak bisa import 'app' dari {ROOT}")
    traceback.print_exc()
    sys.exit(1)

# --- buat app & client
try:
    a = app.create_app()
except Exception:
    print("FAIL: create_app() melempar error:")
    traceback.print_exc()
    sys.exit(1)

c = a.test_client()

tests = [
    ("/dashboard/login", "GET"),
    ("/dashboard/login", "POST"),
    ("/dashboard-static/css/login_theme.css", "GET"),
    ("/dashboard-static/js/login_apply_theme.js", "GET"),
    ("/dashboard-static/themes/gtake/theme.css", "GET"),
    ("/favicon.ico", "GET"),
    ("/uptime", "GET"),
    ("/api/ui-config", "GET"),
]

ok = True
for url, m in tests:
    try:
        r = c.open(url, method=m)
        print(url, m, r.status_code, r.headers.get("Location"))
        # minimal assertions
        if url == "/dashboard/login" and m == "POST":
            ok = ok and (r.status_code in (302, 303))
        elif url == "/dashboard/login" and m == "GET":
            ok = ok and (r.status_code == 200)
        else:
            ok = ok and (r.status_code == 200)
    except Exception:
        ok = False
        print(f"FAIL: request {m} {url}")
        traceback.print_exc()

sys.exit(0 if ok else 1)
