# -*- coding: utf-8 -*-
"""
WebUI utama SatpamBot (dashboard).
Blueprint '/dashboard' + static '/dashboard-static' + theme CSS '/dashboard-theme/<name>/theme.css'.
Tidak mengubah konfigurasi lain.
"""

from __future__ import annotations
import os, time, secrets
from pathlib import Path
from flask import (
    Blueprint, render_template, request, redirect, url_for,
    abort, current_app, send_from_directory, make_response
)
from .live_store import get_ui_config, set_ui_config

# -----------------------------------------------------------------------------
# Lokasi folder relatif ke file ini
# -----------------------------------------------------------------------------
HERE = Path(__file__).resolve().parent
TEMPLATES_DIR = HERE / "templates"
STATIC_DIR    = HERE / "static"
THEMES_DIR    = HERE / "themes"
UPLOADS_DIR   = STATIC_DIR / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

# -----------------------------------------------------------------------------
# Blueprint: /dashboard + /dashboard-static
# -----------------------------------------------------------------------------
bp = Blueprint(
    "dashboard",
    __name__,
    template_folder=str(TEMPLATES_DIR),
    static_folder=str(STATIC_DIR),
    static_url_path="/dashboard-static",
    url_prefix="/dashboard"
)

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------
def _safe_theme(name: str) -> str:
    name = (name or "").strip()
    name = "".join(ch for ch in name if ch.isalnum() or ch in ("-", "_"))
    return name or "gtake"

def _list_themes() -> list[str]:
    # Struktur: themes/<theme>/static/theme.css
    out = []
    for p in THEMES_DIR.glob("*/static/theme.css"):
        out.append(p.parent.parent.name)  # folder themes/<theme>/static/theme.css
    return sorted(out) or ["gtake"]

def _render_or_fallback(tpl: str, fallback_html: str):
    path = TEMPLATES_DIR / tpl
    if path.exists():
        return render_template(tpl)
    return fallback_html, 200

def _save_upload(field: str, prefix: str) -> str | None:
    f = request.files.get(field)
    if not f or not f.filename:
        return None
    ext = Path(f.filename).suffix.lower()
    if ext not in {".png", ".jpg", ".jpeg", ".webp", ".svg"}:
        return None
    name = f"{prefix}_{int(time.time())}_{secrets.token_hex(2)}{ext}"
    dst = UPLOADS_DIR / name
    f.save(str(dst))
    return f"/dashboard-static/uploads/{name}"

# -----------------------------------------------------------------------------
# Halaman utama
# -----------------------------------------------------------------------------
@bp.route("/", methods=["GET"])
def dashboard_home():
    return _render_or_fallback(
        "dashboard.html",
        "<!doctype html><title>Dashboard</title>"
        "<link rel='stylesheet' href='/dashboard-static/css/neo_aurora_plus.css'>"
        "<div class='container'><div class='card'>"
        "<h1>Dashboard</h1><p>Template dashboard.html belum ditemukan.</p>"
        "</div></div>"
    )

# -----------------------------------------------------------------------------
# Login
# -----------------------------------------------------------------------------
@bp.route("/login", methods=["GET"])
def login_get():
    # Menggunakan template login milikmu apa adanya (tidak diubah layout)
    return _render_or_fallback(
        "login.html",
        "<!doctype html><title>Login</title><p>Template login.html belum ditemukan.</p>"
    )

@bp.route("/login", methods=["POST"])
def login_post():
    # Autentikasi sesuai sistemmu; di sini redirect agar alur tetap 303 -> /dashboard
    resp = make_response(redirect(url_for("dashboard.dashboard_home"), code=303))
    # Optional: simpan pilihan theme dari form kalau ada
    t = request.form.get("theme")
    if t:
        resp.set_cookie("theme", _safe_theme(t), max_age=30*24*3600, samesite="Lax")
    return resp

# -----------------------------------------------------------------------------
# Settings (mendukung upload file lokal)
# -----------------------------------------------------------------------------
@bp.route("/settings", methods=["GET", "POST"])
def settings():
    cfg = get_ui_config() or {}

    if request.method == "POST":
        theme = _safe_theme(request.form.get("theme") or cfg.get("theme") or "gtake")
        accent = (request.form.get("accent") or cfg.get("accent") or "teal").strip()
        apply_login = bool(request.form.get("apply_login"))
        use_bg_image = bool(request.form.get("bg_mode_image"))

        logo_url = _save_upload("logo_file", "logo") or cfg.get("logo_url")
        bg_url   = _save_upload("bg_file", "bg") or cfg.get("bg_url")

        cfg.update({
            "theme": theme,
            "accent": accent,
            "logo_url": logo_url,
            "bg_mode": "image" if use_bg_image else "gradient",
            "bg_url": bg_url if use_bg_image else None,
            "apply_login": apply_login,
        })
        set_ui_config(cfg)
        return redirect(url_for(".settings"))

    return _render_or_fallback("settings.html",
        "<!doctype html><title>Settings</title><p>Template settings.html belum ditemukan.</p>"
    )

# -----------------------------------------------------------------------------
# Security (drag & drop)
# -----------------------------------------------------------------------------
@bp.route("/security", methods=["GET"])
def security():
    return _render_or_fallback("security.html",
        "<!doctype html><title>Security</title><p>Template security.html belum ditemukan.</p>"
    )

# -----------------------------------------------------------------------------
# Theme CSS (kompatibel dengan endpoint lama: /dashboard-theme/<name>/theme.css)
# Didaftarkan lewat blueprint ini, sehingga URL global tetap sama.
# -----------------------------------------------------------------------------
@bp.route("/../dashboard-theme/<name>/theme.css", methods=["GET"])
def theme_css(name: str):
    name = _safe_theme(name)
    css_path = THEMES_DIR / name / "static" / "theme.css"
    if not css_path.exists():
        abort(404)
    return send_from_directory(css_path.parent, css_path.name, mimetype="text/css")
