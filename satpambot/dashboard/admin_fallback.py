import os
from flask import Blueprint, request, session, redirect, render_template, jsonify

admin_fallback_bp = Blueprint("admin_fallback", __name__)

# integrate theme helpers without modifying app.py
@admin_fallback_bp.record_once
def _init_theme(setup_state):
    try:
        from satpambot.app_theme_context_patch import attach_theme_context, register_theme_routes
        app = setup_state.app
        attach_theme_context(app)
        register_theme_routes(app)
    except Exception:
        pass

def _creds():
    u = os.getenv("ADMIN_USERNAME") or os.getenv("SUPER_ADMIN_USER")
    p = os.getenv("ADMIN_PASSWORD") or os.getenv("SUPER_ADMIN_PASS")
    return (u or "").strip(), (p or "").strip()

@admin_fallback_bp.route("/admin/login", methods=["GET","POST"])
def admin_login():
    USER, PASS = _creds()
    if not USER or not PASS:
        return render_template("login.html", err="Set ADMIN_USERNAME/ADMIN_PASSWORD atau SUPER_ADMIN_USER/SUPER_ADMIN_PASS di Render.")
    err=None
    if request.method == "POST":
        u = (request.form.get("username") or "").strip()
        p = (request.form.get("password") or "").strip()
        if u == USER and p == PASS:
            session["is_admin"] = True
            session["admin_user"] = u
            return redirect("/")
        err = "Username / password salah"
    return render_template("login.html", err=err)

@admin_fallback_bp.route("/logout")
def admin_logout():
    session.clear(); return redirect("/")

@admin_fallback_bp.route("/api/me")
def me():
    return jsonify({"admin": bool(session.get("is_admin")), "user": session.get("admin_user")})
