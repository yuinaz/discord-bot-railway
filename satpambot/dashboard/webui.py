
import os
from flask import Blueprint, render_template, request, redirect, url_for, jsonify

def register_webui_builtin(app):
    bp = Blueprint(
        "dashboard",
        __name__,
        url_prefix="/dashboard",
        template_folder="templates",
        static_folder="static",
    )

    @bp.route("/", methods=["GET"])
    def home():
        # Render theme-based dashboard if present; fallback to default
        try:
            return render_template("dashboard.html", title="Dashboard")
        except Exception:
            return "<!doctype html><title>Dashboard</title>Dashboard OK"

    @bp.route("/login", methods=["GET","POST"])
    def login():
        # Do NOT change original design; just render the existing login template
        cfg = {"theme":"gtake","apply_to_login": False, "logo_url": ""}
        if request.method == "POST":
            return redirect(url_for("dashboard.home"))
        return render_template("login.html", title="Login", cfg=cfg)

    @bp.route("/settings", methods=["GET","POST"])
    def settings():
        # Render tidy settings page (template exists)
        try:
            return render_template("settings_gtake.html", title="Settings")
        except Exception:
            return render_template("settings.html", title="Settings")

    @bp.route("/security", methods=["GET"])
    def security():
        return render_template("security.html", title="Security")

    @bp.route("/upload", methods=["POST"])
    def upload():
        if "file" not in request.files:
            return jsonify({"ok": False, "error": "no file"}), 400
        f = request.files["file"]
        return jsonify({"ok": True, "name": getattr(f, "filename", "upload")})

    @bp.route("/security/upload", methods=["POST"])
    def security_upload():
        if "file" not in request.files:
            return jsonify({"ok": False, "error": "no file"}), 400
        f = request.files["file"]
        return jsonify({"ok": True, "name": getattr(f, "filename", "upload")})

    app.register_blueprint(bp)
