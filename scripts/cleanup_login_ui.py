from pathlib import Path
import re

ROOT = Path(".")
STATIC = ROOT / "satpambot/dashboard/static"
IMG    = STATIC / "img"
TPL    = ROOT / "satpambot/dashboard/templates"

STATIC.mkdir(parents=True, exist_ok=True)
IMG.mkdir(parents=True, exist_ok=True)

# --- Pastikan CSS login & styling tombol seragam
css = STATIC / "dashboard.css"
need_tokens = [".login-card{", ".login-form input[type=text]", ".login-btn"]
css_base = """
:root{--card-bg:rgba(17,24,39,.65);--card-radius:14px;--input-h:44px}
.login-card{background:var(--card-bg);border-radius:var(--card-radius);padding:1.25rem 1.5rem;box-shadow:0 10px 24px rgba(0,0,0,.35);max-width:980px;margin:0 auto}
.login-card h1,.login-card h2{text-align:center;margin:.25rem 0 1rem}
.form-row{max-width:900px;margin:0 auto 12px}
.form-row label{display:block;margin:.35rem 0 .25rem;opacity:.85}
.login-form input[type=text],.login-form input[type=password],
form[action="/login"] input[type=text],form[action="/login"] input[type=password],
form#login input[type=text],form#login input[type=password]{
 display:block;width:100%;height:var(--input-h);box-sizing:border-box;padding:.6rem .8rem;
 border-radius:12px;border:1px solid rgba(255,255,255,.08);background:rgba(0,0,0,.35);color:#fff}
.btn-primary,.login-btn{display:block;width:100%;height:var(--input-h);border-radius:12px;border:0;cursor:pointer;background:#1a56db;color:#fff;font-weight:600}
.particles-js-canvas-el{opacity:.35!important}
""".lstrip()
if not css.exists() or not all(tok in css.read_text(encoding="utf-8", errors="ignore") for tok in need_tokens):
    css.write_text(css_base, encoding="utf-8")

# --- Taruh logo default jika belum ada (untuk menghilangkan 404)
logo = IMG / "logo.svg"
if not logo.exists():
    logo.write_text("""<svg xmlns="http://www.w3.org/2000/svg" width="160" height="40" viewBox="0 0 160 40">
<defs><linearGradient id="g" x1="0" x2="1"><stop stop-color="#7c3aed"/><stop offset="1" stop-color="#2563eb"/></linearGradient></defs>
<rect rx="8" width="160" height="40" fill="url(#g)"/><path d="M18 10l10 5v6c0 6-6 9-10 10-4-1-10-4-10-10v-6l10-5z" fill="#111827" opacity=".95"/>
<text x="48" y="26" font-family="Inter,Segoe UI,Arial" font-size="16" fill="#fff" font-weight="700">SatpamBot</text></svg>""", encoding="utf-8")

# --- Bersihkan login.html: hapus submit ganda, sisakan 1 tombol
login_html = TPL / "login.html"
if login_html.exists():
    html = login_html.read_text(encoding="utf-8", errors="ignore")

    # pastikan form punya class login-form (untuk styling seragam)
    html = re.sub(
        r'<form([^>]*?)>',
        lambda m: (
            f'<form{m.group(1)} class="login-form">' if 'class=' not in m.group(1)
            else (m.group(0) if 'login-form' in m.group(0) else m.group(0).replace('class="', 'class="login-form '))
        ),
        html, count=1
    )

    # hapus SEMUA submit lama (input/button)
    html = re.sub(r'<input[^>]*type=["\']submit["\'][^>]*>', '', html, flags=re.I)
    html = re.sub(r'<button[^>]*type=["\']submit["\'][^>]*>.*?</button>', '', html, flags=re.I|re.S)
    html = re.sub(r'<button[^>]*>\s*Login\s*</button>', '', html, flags=re.I)

    # tambah satu tombol submit rapi jika belum ada
    if 'id="btn-login"' not in html:
        html = html.replace(
            "</form>",
            '\n  <div class="form-row"><button id="btn-login" type="submit" class="login-btn btn-primary">Login</button></div>\n</form>',
            1
        )

    # bungkus card jika belum ada
    if "login-card" not in html:
        html = html.replace("<form", '<div class="login-card">\n<form', 1).replace("</form>", "</form>\n</div>", 1)

    login_html.write_text(html, encoding="utf-8")

print("✓ Login UI dibersihkan, tombol tunggal dipastikan, logo & CSS tersedia.")
