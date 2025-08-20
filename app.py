# app.py — WSGI entry untuk Render (FINAL)
from __future__ import annotations
import os

# Selalu gunakan aplikasi dashboard utama
try:
    # Import factory dari dashboard kamu
    from satpambot.dashboard.app_dashboard import create_app as _create_dashboard_app
    app = _create_dashboard_app()
except Exception as e:
    # Fallback super-minimal kalau import dashboard gagal
    from flask import Flask
    app = Flask("satpambot_fallback")

    @app.get("/")
    def _fb():
        # Biarkan jelas kalau yang tampil ini fallback, agar mudah dilog/di-debug
        return "SatpamBot dashboard fallback (import failed)", 500

# (Opsional) Root → /login agar akses domain langsung mengarah ke halaman login.
# Aman karena hanya dibuat kalau route "/" belum ada di app dashboard.
try:
    from flask import redirect
    existing_rules = {r.rule for r in app.url_map.iter_rules()}
    if "/" not in existing_rules:
        @app.get("/")
        def _root_redirect():
            return redirect("/login", code=302)
except Exception:
    # Jangan sampai gagal hanya karena inspeksi url_map/redirect
    pass


# Menjalankan lokal/dev; di Render Procfile/Start Command cukup: `python main.py`
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "10000")), debug=False)
