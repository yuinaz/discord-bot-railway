# webui.py (patched) — dashboard + settings (local uploads) + themes list
from __future__ import annotations
from flask import Blueprint, render_template, request, redirect, url_for, jsonify
from flask import current_app, send_from_directory
from pathlib import Path
import secrets, time, os
from .live_store import get_ui_config, set_ui_config

bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")

def _root_paths():
    here = Path(__file__).resolve().parent
    static_dir = here / "static"
    theme_dir = Path(here, "themes")
    upload_dir = static_dir / "uploads"
    upload_dir.mkdir(exist_ok=True, parents=True)
    return here, static_dir, theme_dir, upload_dir

def _list_themes() -> list[str]:
    _, _, theme_dir, _ = _root_paths()
    out = []
    for p in theme_dir.glob("*/theme.css"):
        out.append(p.parent.name)
    return sorted(out) or ["gtake"]

@bp.route("/")
def index():
    return render_template("dashboard.html")

@bp.route("/settings", methods=["GET","POST"])
def settings():
    cfg = get_ui_config() or {}
    here, static_dir, theme_dir, upload_dir = _root_paths()

    if request.method == "POST":
        # theme & accent
        theme = request.form.get("theme") or cfg.get("theme") or "gtake"
        accent = request.form.get("accent") or cfg.get("accent") or "teal"
        apply_login = bool(request.form.get("apply_login"))
        use_bg_image = bool(request.form.get("bg_mode_image"))
        # file uploads
        def save_file(field, prefix):
            f = request.files.get(field)
            if not f or not f.filename:
                return None
            ext = Path(f.filename).suffix.lower()
            if ext not in [".png",".jpg",".jpeg",".webp",".svg"]:
                return None
            name = f"{prefix}_{int(time.time())}_{secrets.token_hex(2)}{ext}"
            dst = upload_dir / name
            f.save(str(dst))
            return f"/dashboard-static/uploads/{name}"

        logo_url = save_file("logo_file","logo") or cfg.get("logo_url")
        bg_url = save_file("bg_file","bg") or cfg.get("bg_url")

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

    return render_template("settings.html", cfg=cfg, themes=_list_themes())

@bp.route("/theme/<name>/theme.css")
def theme_css(name:str):
    here, _, theme_dir, _ = _root_paths()
    css = theme_dir / name / "theme.css"
    if css.exists():
        return current_app.send_static_file(str(css))
    return ("/* theme not found */", 404, {"Content-Type":"text/css"})

# Aliases for compatibility
@bp.route("/theme/<name>/")
def theme_alias(name:str):
    return redirect(url_for(".theme_css", name=name))

# ===== API =====
@bp.route("/../api/ui-config")
def api_proxy_ui_config():
    # Using relative traversal to keep endpoint at /api/ui-config through blueprint mounting
    return jsonify(get_ui_config() or {"theme":"gtake","accent":"teal"})

@bp.route("/../api/ui-themes")
def api_proxy_ui_themes():
    return jsonify(_list_themes())
