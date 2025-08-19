from flask import Blueprint, render_template
bp = Blueprint("webui", __name__, template_folder="templates")
@bp.get("/")
def home(): return render_template("dashboard/index.html")
@bp.get("/dashboard")
def dashboard(): return render_template("dashboard/index.html")
def register_webui(app):
    if "webui" not in app.blueprints:
        app.register_blueprint(bp)
