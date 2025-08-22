#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Robust smoketest (auto path detect) – no env tweaks required.

import os, sys, json

HERE = os.path.abspath(os.path.dirname(__file__))
def find_root():
    cands = [
        os.path.abspath(os.path.join(HERE, "..")),
        os.path.abspath(os.getcwd()),
    ]
    cur = os.path.abspath(os.getcwd())
    for _ in range(4):
        cands.append(cur)
        cur = os.path.abspath(os.path.join(cur, ".."))
    for r in cands:
        if any(os.path.exists(os.path.join(r, f)) for f in ("app.py","app_dashboard.py"))            or os.path.isdir(os.path.join(r, "satpambot")):
            return r
    return None

def ensure_pkgs(root):
    pkgs = ["satpambot","satpambot/dashboard"]
    for p in pkgs:
        d = os.path.join(root, p.replace("/", os.sep))
        if os.path.isdir(d):
            f = os.path.join(d, "__init__.py")
            if not os.path.exists(f):
                try:
                    open(f, "w", encoding="utf-8").write("# pkg marker\n")
                except: pass

def import_create_app():
    try:
        import app
        if hasattr(app, "create_app"): return app.create_app, "app.create_app"
    except Exception as e:
        print("[info] import app gagal:", e)
    try:
        import app_dashboard
        if hasattr(app_dashboard, "create_app"): return app_dashboard.create_app, "app_dashboard.create_app"
    except Exception as e:
        print("[info] import app_dashboard gagal:", e)
    try:
        from satpambot.dashboard.app_fallback import create_app
        return create_app, "satpambot.dashboard.app_fallback.create_app"
    except Exception as e:
        raise RuntimeError("Tidak bisa mendapatkan create_app(): %r" % e)

def want(c, method, url, code):
    r = c.open(url, method=method)
    if r.status_code != code:
        raise SystemExit(f"FAIL {method} {url} :: {r.status_code}")
    return r

def main():
    root = find_root()
    if not root: raise SystemExit("Repo root tidak ditemukan")
    if root not in sys.path: sys.path.insert(0, root)
    ensure_pkgs(root)
    create_app, src = import_create_app()
    print("[ok] create_app:", src)
    app = create_app()
    c = app.test_client()
    r = want(c, "GET", "/", 302); print("OK / ->", r.headers.get("Location"))
    want(c, "GET", "/dashboard/login", 200); print("OK /dashboard/login 200")
    want(c, "GET", "/dashboard", 200); print("OK /dashboard 200")
    want(c, "HEAD", "/healthz", 200); want(c, "HEAD", "/uptime", 200); print("OK healthz/uptime 200")
    r = want(c, "GET", "/api/ui-config", 200)
    r = want(c, "GET", "/api/ui-themes", 200); print("OK ui-config/themes 200 (optional)")
    print("All smoketests PASSED")

if __name__ == "__main__":
    main()
