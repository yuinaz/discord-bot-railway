from __future__ import annotations
from flask import Blueprint, render_template

dashboard_bp = Blueprint(
    "dashboard",
    __name__,
    template_folder="templates",
    static_folder="static",
    url_prefix="/dashboard",
)

@dashboard_bp.get("/")
def page_dashboard(): return render_template("dashboard.html")

@dashboard_bp.get("/login")
def page_login(): return render_template("login.html")

@dashboard_bp.get("/settings")
def page_settings(): return render_template("settings.html")

@dashboard_bp.get("/security")
def page_security(): return render_template("security.html")

def register_webui_builtin(app):
    if "dashboard" not in app.blueprints:
        app.register_blueprint(dashboard_bp)
