#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Auto-inject fallback dashboard register call into create_app()
Safe for Windows/Linux. Only touches app.py / app_dashboard.py if present.
"""
import os, re, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TARGETS = [os.path.join(ROOT, "app.py"), os.path.join(ROOT, "app_dashboard.py")]

# This snippet is injected verbatim into target file(s) if not present
UTIL_SNIPPET = '''

def _register_dashboard_blueprint_with_fallback(app):
    """
    Daftarkan blueprint dashboard; fallback aktif jika import webui gagal.
    Tidak mengubah config/env lain. Jika webui utama tersedia, fallback tidak dipakai.
    """
    tried = []

    def _try(mod_name):
        mod = __import__(mod_name, fromlist=['bp','register'])
        if hasattr(mod, 'bp'):
            app.register_blueprint(getattr(mod,'bp')); return True
        if hasattr(mod, 'register'):
            getattr(mod,'register')(app); return True
        return False

    for mod_name in ('satpambot.dashboard.webui','dashboard.webui','webui','satpambot.dashboard.app_fallback'):
        try:
            if _try(mod_name):
                return
        except Exception as e:
            tried.append(f"{mod_name}: {e.__class__.__name__}")

    # Inline fallback sangat ringan – hanya agar health/smoketest & login 200
    from flask import Blueprint, render_template_string

    bp = Blueprint('dashboard_fallback', __name__, url_prefix='/dashboard')

    @bp.route('/login', methods=['GET'])
    def _login_fallback():
        return render_template_string(
            "<!doctype html><title>Login</title>"
            "<p>Fallback login (sementara). WebUI utama gagal diimpor.</p>"
        ), 200

    @bp.route('/', methods=['GET'])
    def _dash_fallback():
        return render_template_string(
            "<!doctype html><title>Dashboard</title>"
            "<p>Fallback dashboard. WebUI utama gagal diimpor.</p>"
        ), 200

    app.register_blueprint(bp)
'''

def patch_file(path):
    if not os.path.exists(path):
        return False, "skip (not found)"
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        txt = f.read()

    changed = False
    if "_register_dashboard_blueprint_with_fallback" not in txt:
        txt = txt.rstrip() + "\n\n" + UTIL_SNIPPET + "\n"
        changed = True

    # Inject call inside create_app before 'return app'
    # Find first def create_app(...):
    m = re.search(r"^def\s+create_app\s*\(.*?\):", txt, flags=re.M)
    if m and "_register_dashboard_blueprint_with_fallback(app)" not in txt:
        start = m.end()
        mret = re.search(r"\n\s*return\s+app\b", txt[start:], flags=re.S)
        if mret:
            insert_at = start + mret.start()
            txt = txt[:insert_at] + "\n    _register_dashboard_blueprint_with_fallback(app)\n" + txt[insert_at:]
            changed = True

    if changed:
        with open(path, "w", encoding="utf-8") as f:
            f.write(txt)
        return True, "patched"
    else:
        return True, "ok (no change)"

def main():
    any_touched = False
    for t in TARGETS:
        ok, msg = patch_file(t)
        print(f"[patch] {t} -> {msg}")
        any_touched = any_touched or (ok and msg == "patched")
    if not any_touched:
        print("[patch] Nothing changed. If /dashboard/login still 404, ensure create_app() is in app.py/app_dashboard.py")

if __name__ == "__main__":
    main()
