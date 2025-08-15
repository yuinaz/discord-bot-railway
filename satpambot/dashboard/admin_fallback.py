import os
from flask import Blueprint, request, session, redirect, url_for, render_template_string, jsonify

admin_fallback_bp = Blueprint("admin_fallback", __name__)

def _admin_creds():
    user = os.getenv("ADMIN_USERNAME") or os.getenv("SUPER_ADMIN_USER")
    pwd  = os.getenv("ADMIN_PASSWORD") or os.getenv("SUPER_ADMIN_PASS")
    return (user or "").strip(), (pwd or "").strip()

@admin_fallback_bp.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    USER, PASS = _admin_creds()
    err = None
    if not USER or not PASS:
        return render_template_string(
            "<h3>Admin login belum dikonfigurasi</h3>"
            "<p>Set <code>ADMIN_USERNAME/ADMIN_PASSWORD</code> "
            "atau <code>SUPER_ADMIN_USER/SUPER_ADMIN_PASS</code> di Render.</p>"
        )
    if request.method == "POST":
        u = (request.form.get("username") or "").strip()
        p = (request.form.get("password") or "").strip()
        if u == USER and p == PASS:
            session["is_admin"] = True
            session["admin_user"] = u
            return redirect(request.args.get("next") or "/")
        err = "Username / password salah"
    html = """
<!doctype html><meta name=viewport content="width=device-width, initial-scale=1">
<style>
body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Ubuntu,Helvetica,Arial,sans-serif;background:#0b0e14;color:#e6e6e6;display:grid;place-items:center;height:100vh;margin:0}
.card{background:#141923;border:1px solid #222b3b;border-radius:16px;padding:24px;min-width:320px;box-shadow:0 8px 32px rgba(0,0,0,.35)}
input,button{width:100%;padding:10px 12px;border-radius:10px}
input{border:1px solid #334;background:#0f1320;color:#e6e6e6;margin-top:8px}
button{margin-top:12px;border:none;background:#5865F2;color:#fff;font-weight:600;cursor:pointer}
.err{color:#ff6b6b;margin:8px 0 0 0;font-size:.9rem}
</style>
<div class=card>
  <h2>Login Admin</h2>
  {% if err %}<div class=err>{{err}}</div>{% endif %}
  <form method=POST>
    <label>Username</label><input name=username autocomplete=username>
    <label>Password</label><input name=password type=password autocomplete=current-password>
    <button type=submit>Masuk</button>
  </form>
  <p style="opacity:.7;margin-top:8px">Set <code>ADMIN_USERNAME/ADMIN_PASSWORD</code> atau <code>SUPER_ADMIN_USER/SUPER_ADMIN_PASS</code> di Render.</p>
</div>
"""
    return render_template_string(html, err=err)

@admin_fallback_bp.route("/logout")
def admin_logout():
    session.clear()
    return redirect("/")

@admin_fallback_bp.route("/api/me")
def api_me():
    return jsonify({"admin": bool(session.get("is_admin")), "user": session.get("admin_user")})
