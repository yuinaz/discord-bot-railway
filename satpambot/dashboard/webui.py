
import os
from flask import Blueprint, render_template

def register_webui_builtin(app):
    bp = Blueprint(
        "dashboard",
        __name__,
        url_prefix="/dashboard",
        template_folder="templates",
        static_folder="static",
    )

    @bp.route("/")
    def home():
        return render_template("dashboard.html", title="Dashboard")

    @bp.route("/login")
    def login():
        return render_template("base_gtake.html", title="Login")

    @bp.route("/settings")
    def settings():
        from flask import jsonify
        return jsonify({"ok": True})

    @bp.route("/security")
    def security():
        from flask import jsonify
        return jsonify({"ok": True, "features": ["rate_limit","captcha","audit_log"]})

    app.register_blueprint(bp)
