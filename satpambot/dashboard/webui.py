"""Dashboard WebUI registration shim.

Provides `register_webui_builtin(app, ...)` expected by tests without altering
existing config formats. It mounts:
- /dashboard            (pages: /, /login, /security, /settings)
- /dashboard-static/*   -> satpambot/dashboard/static/*
- /dashboard-theme/<theme>/* -> satpambot/dashboard/themes/<theme>/static/*
- /favicon.ico          (fallback to logo.svg if favicon.ico is absent)
"""
from __future__ import annotations

import os

from flask import Blueprint, redirect, render_template, send_from_directory, url_for

_HERE = os.path.dirname(__file__)

def _file_exists(*parts: str) -> bool:
    return os.path.exists(os.path.join(_HERE, *parts))

def register_webui_builtin(
    app,
    url_prefix: str = "/dashboard",
    static_prefix: str = "/dashboard-static",
    theme_prefix: str = "/dashboard-theme",
):
    """Register built-in dashboard views & static mounts onto a Flask app.

    This function **does not** change any config; it only wires routes so the
    smoke tests can fetch /dashboard/login and /dashboard-static assets.
    """
    bp = Blueprint(
        "dashboard_builtin",
        __name__,
        template_folder=os.path.join(_HERE, "templates"),
        static_folder=os.path.join(_HERE, "static"),
    )

    # --- Views ---
    @bp.route("/")
    def _dash_root():
        # Redirect to the dashboard landing page
        return redirect(url_for("dashboard_builtin.dashboard"))

    @bp.route("/dashboard")
    def dashboard():
        # Keep existing template name; do not alter template content
        return render_template("dashboard.html"), 200

    @bp.route("/login")
    def login():
        return render_template("login.html"), 200

    @bp.route("/security")
    def security():
        return render_template("security.html"), 200

    @bp.route("/settings")
    def settings():
        return render_template("settings.html"), 200

    # Register blueprint under /dashboard
    app.register_blueprint(bp, url_prefix=url_prefix)

    # --- Static mounts ---
    def _static(filename: str):
        # Map /dashboard-static/* to satpambot/dashboard/static/*
        return send_from_directory(os.path.join(_HERE, "static"), filename)

    app.add_url_rule(
        f"{static_prefix}/<path:filename>",
        endpoint="dashboard_builtin_static",
        view_func=_static,
    )

    # Theme static: /dashboard-theme/<theme>/<path>
    def _theme_static(theme: str, filename: str):
        base = os.path.join(_HERE, "themes", theme, "static")
        return send_from_directory(base, filename)

    app.add_url_rule(
        f"{theme_prefix}/<theme>/<path:filename>",
        endpoint="dashboard_theme_static",
        view_func=_theme_static,
    )

    # Favicon fallback to avoid 404 in tests
    @app.route("/favicon.ico")
    def _favicon():
        ico_dir = os.path.join(_HERE, "static")
        # Use favicon.ico if present; otherwise fall back to logo.svg
        if os.path.exists(os.path.join(ico_dir, "favicon.ico")):
            return send_from_directory(ico_dir, "favicon.ico")
        return send_from_directory(ico_dir, "logo.svg")

    return bp

__all__ = ["register_webui_builtin"]
