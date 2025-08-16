set -euo pipefail
ROOT="satpambot/dashboard"
APP="$ROOT/app.py"

mkdir -p "$ROOT/static/css" "$ROOT/static/js" "$ROOT/static/themes" "$ROOT/templates/partials" "$ROOT/templates"

# --- CSS yang diminta halaman ---
[ -f "$ROOT/static/css/auth.css" ] || cat > "$ROOT/static/css/auth.css" <<'CSS'
:root { color-scheme: dark; }
body{margin:0;font-family:system-ui,Segoe UI,Roboto,Arial,sans-serif;background:#0b0d12;color:#e5e7eb}
.container{max-width:1100px;margin:24px auto;padding:0 16px}
.card{background:#121621;border:1px solid #1f2430;border-radius:12px;padding:16px}
.btn{display:inline-block;padding:8px 12px;border-radius:10px;border:1px solid #303544;cursor:pointer}
.kpi{font-size:28px;font-weight:700}
CSS

# beberapa template lama minta /static/dashboard.css → sediakan placeholder
[ -f "$ROOT/static/dashboard.css" ] || cat > "$ROOT/static/dashboard.css" <<'CSS'
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px}
.label{opacity:.7;font-size:.9rem;margin-top:4px}
CSS

# --- themes minimal agar /theme/list ada isinya ---
for t in default dark light; do
  [ -f "$ROOT/static/themes/$t.css" ] || echo "/* theme $t */" > "$ROOT/static/themes/$t.css"
done

# --- favicon kecil (base64) agar /favicon.ico 200 ---
if [ ! -f "$ROOT/static/favicon.ico" ]; then
  base64 -d > "$ROOT/static/favicon.ico" <<'ICO'
AAABAAEAEBAAAAEAIABoBAAAFgAAACgAAAAQAAAAIAAAAAEAGAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAABmZmYAZmZmAGZmZgBmZmYAZmZmAGZm
ZgBmZmYAZmZmAGZmZgBmZmYAZmZmAGZmZgBmZmYAZmZmAGZmZgBmZmYAZmZmAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA
AAAA
ICO
fi

# --- halaman assets manager sederhana ---
[ -f "$ROOT/templates/assets_manager.html" ] || cat > "$ROOT/templates/assets_manager.html" <<'HTML'
{% extends 'base.html' %}
{% block title %}Assets Manager - SatpamBot{% endblock %}
{% block content %}
{% include 'partials/logout_nav.html' %}
<div class="container">
  <h2>Assets Manager</h2>
  <div class="card"><p>Placeholder halaman manajemen aset.</p></div>
</div>
{% endblock %}
HTML

# --- sisipkan routes bila belum ada ---
add_route() {
  sig="$1"; code="$2"
  grep -q "$sig" "$APP" || printf "\n%s\n" "$code" >> "$APP"
}

add_route '@app.get("/theme/list")' "$(cat <<'PY'
@app.get("/theme/list")
@login_required
def theme_list():
    from flask import jsonify
    base = os.path.join(os.path.dirname(__file__), "static", "themes")
    themes = []
    try:
        if os.path.isdir(base):
            for n in os.listdir(base):
                if n.endswith(".css"):
                    themes.append(os.path.splitext(n)[0])
    except Exception:
        pass
    if not themes:
        themes = ["default","dark","light"]
    return jsonify(ok=True, themes=themes)
PY
)"

add_route '@app.get("/api/guilds")' "$(cat <<'PY'
@app.get("/api/guilds")
@login_required
def api_guilds():
    from flask import jsonify
    return jsonify(ok=True, guilds=[])
PY
)"

add_route '@app.get("/assets-manager")' "$(cat <<'PY'
@app.get("/assets-manager")
@login_required
def assets_manager():
    return render_template("assets_manager.html")
PY
)"

add_route '@app.get("/favicon.ico")' "$(cat <<'PY'
@app.get("/favicon.ico")
def favicon():
    from flask import send_from_directory
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    return send_from_directory(static_dir, "favicon.ico", mimetype="image/x-icon")
PY
)"

git add "$APP" "$ROOT/static" "$ROOT/templates/assets_manager.html"
git commit -m "fix(ui): resolve 404s (/theme/list, /static/dashboard.css, /api/guilds, /assets-manager, /favicon.ico)"
