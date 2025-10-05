from pathlib import Path
import os

ROOT = Path(".")
STATIC = ROOT / "satpambot/dashboard/static"
TEMPLATES = ROOT / "satpambot/dashboard/templates"
APP_PY = ROOT / "satpambot/dashboard/app.py"

STATIC.mkdir(parents=True, exist_ok=True)
(STATIC/"img").mkdir(parents=True, exist_ok=True)
(STATIC/"uploads").mkdir(parents=True, exist_ok=True)
(STATIC/"css").mkdir(parents=True, exist_ok=True)

# ---------- CSS ----------
css = (STATIC/"dashboard.css")
css_alt = (STATIC/"css"/"dashboard.css")
css_text = """
:root{--card-bg:rgba(17,24,39,.65);--card-radius:14px;--input-h:44px}
.login-card{background:var(--card-bg);border-radius:var(--card-radius);padding:1.25rem 1.5rem;box-shadow:0 10px 24px rgba(0,0,0,.35);max-width:980px;margin:0 auto}
.login-card h1,.login-card h2{text-align:center;margin:.25rem 0 1rem}
.form-row{max-width:900px;margin:0 auto 12px}
.form-row label{display:block;margin:.35rem 0 .25rem;opacity:.85}
.login-form input[type=text],.login-form input[type=password],
form[action="/login"] input[type=text],form[action="/login"] input[type=password],
form#login input[type=text],form#login input[type=password]{
 display:block;width:100%;height:var(--input-h);box-sizing:border-box;padding:.6rem .8rem;
 border-radius:12px;border:1px solid rgba(255,255,255,.08);background:rgba(0,0,0,.35);color:#fff;outline:none}
.login-form input:focus{border-color:rgba(59,130,246,.6);box-shadow:0 0 0 3px rgba(59,130,246,.25)}
.btn-primary,.login-btn{display:block;width:100%;height:var(--input-h);border-radius:12px;border:0;cursor:pointer;background:#1a56db;color:#fff;font-weight:600}
.brand{display:flex;align-items:center;gap:.6rem}.brand img.logo{height:28px;opacity:.9}.brand .title{font-weight:700;letter-spacing:.2px}
.particles-bg,#tsparticles,#particles-js{position:fixed;inset:0;z-index:-1;pointer-events:none;opacity:.35}
.particles-js-canvas-el{opacity:.35!important}
""".lstrip()
for p in (css, css_alt):
    p.write_text(css_text, encoding="utf-8")

# ---------- Logo ----------
logo = STATIC/"img/logo.svg"
if not logo.exists():
    logo.write_text("""<svg xmlns="http://www.w3.org/2000/svg" width="160" height="40" viewBox="0 0 160 40">
<defs><linearGradient id="g" x1="0" x2="1"><stop stop-color="#7c3aed"/><stop offset="1" stop-color="#2563eb"/></linearGradient></defs>
<rect rx="8" width="160" height="40" fill="url(#g)"/>
<path d="M18 10l10 5v6c0 6-6 9-10 10-4-1-10-4-10-10v-6l10-5z" fill="#111827" opacity=".95"/>
<text x="48" y="26" font-family="Inter,Segoe UI,Arial" font-size="16" fill="#fff" font-weight="700">SatpamBot</text>
</svg>""", encoding="utf-8")

# ---------- base.html: link CSS + brand ----------
base = TEMPLATES/"base.html"
if base.exists():
    s = base.read_text(encoding="utf-8", errors="ignore")
    if "dashboard.css" not in s:
        s = s.replace("</head>", '  <link rel="stylesheet" href="{{ url_for(\'static\', filename=\'dashboard.css\') }}">\n</head>')
    if 'class="brand"' not in s:
        s = s.replace(
            "<nav", 
            "<nav>\n  <div class=\"brand\">\n    <img class=\"logo\" src=\"{{ url_for('static', filename='img/logo.svg') }}\" alt=\"SatpamBot\">\n    <span class=\"title\">SatpamBot</span>\n  </div>\n", 
            1
        )
        # perbaiki tag <nav> yang terduplikasi ">" akibat replace sederhana
        s = s.replace("<nav>\n<nav", "<nav")
    base.write_text(s, encoding="utf-8")

# ---------- login.html: pastikan form & tombol ----------
login = TEMPLATES/"login.html"
if login.exists():
    t = login.read_text(encoding="utf-8", errors="ignore")
    # tambahkan class login-form ke form pertama
    if "<form" in t:
        head, rest = t.split("<form", 1)
        if 'class="' not in rest.split(">",1)[0]:
            rest = ' class="login-form"' + rest
        elif "login-form" not in rest.split('"',3)[1]:
            # sisipkan login-form ke class yang sudah ada
            parts = rest.split('"',3)
            parts[1] = parts[1] + " login-form"
            rest = '"'.join(parts)
        t = head + "<form" + rest
    # bungkus .login-card bila belum
    if "login-card" not in t:
        t = t.replace("<form", '<div class="login-card">\n<form', 1).replace("</form>", "</form>\n</div>", 1)
    # pastikan ada tombol submit bertuliskan Login
    if "type=\"submit\"" not in t and ">Login<" not in t:
        t = t.replace("</form>", '\n  <div class="form-row"><button type="submit" class="login-btn btn-primary">Login</button></div>\n</form>', 1)
    login.write_text(t, encoding="utf-8")

# ---------- app.py: tambah import & routes bila belum ada ----------
APP_PY.parent.mkdir(parents=True, exist_ok=True)
if APP_PY.exists():
    s = APP_PY.read_text(encoding="utf-8", errors="ignore")
else:
    s = "from flask import Flask\napp = Flask(__name__)\n"

def ensure_top(line: str):
    global s
    if line not in s:
        s = line + "\n" + s

ensure_top("import os")
ensure_top("from werkzeug.utils import secure_filename")
ensure_top("from flask import request, jsonify, redirect, url_for")

if '@app.get("/discord/login")' not in s:
    s += """

# --- stub: /discord/login ---
@app.get("/discord/login")
def discord_login_stub():
    return redirect(url_for("login"))
"""

if '@app.post("/upload/background")' not in s:
    s += """

# --- simple upload handler: saves to static/uploads ---
@app.post("/upload/background")
def upload_background():
    file = request.files.get("file")
    if not file:
        return jsonify(ok=False, error="no file"), 400
    save_dir = os.path.join(os.path.dirname(__file__), "static", "uploads")
    os.makedirs(save_dir, exist_ok=True)
    fname = secure_filename(file.filename or "background.bin")
    path = os.path.join(save_dir, fname)
    file.save(path)
    rel = f"uploads/{fname}"
    return jsonify(ok=True, path=url_for('static', filename=rel))
"""
APP_PY.write_text(s, encoding="utf-8")
print("Patch applied OK")
