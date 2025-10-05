import os
import re
from pathlib import Path

ROOT = Path(".")



STATIC = ROOT / "satpambot/dashboard/static"



IMG = STATIC / "img"



TPL = ROOT / "satpambot/dashboard/templates"



APP = ROOT / "satpambot/dashboard/app.py"







STATIC.mkdir(parents=True, exist_ok=True)



IMG.mkdir(parents=True, exist_ok=True)



(STATIC / "uploads").mkdir(parents=True, exist_ok=True)







# ---- CSS dasar untuk login & particles



css = STATIC / "dashboard.css"



need = [



    ".login-card{",



    ".login-form input[type=text]",



    ".login-btn",



    ".particles-js-canvas-el{opacity:.35",



]



base_css = """



:root{--card-bg:rgba(17,24,39,.65)



--card-radius:14px



--input-h:44px}



.login-card{background:var(--card-bg)



border-radius:var(--card-radius)



padding:1.25rem 1.5rem



box-shadow:0 10px 24px rgba(0,0,0,.35)



max-width:980px



margin:0 auto}



.login-card h1,.login-card h2{text-align:center



margin:.25rem 0 1rem}



.form-row{max-width:900px



margin:0 auto 12px}



.form-row label{display:block



margin:.35rem 0 .25rem



opacity:.85}



.login-form input[type=text],.login-form input[type=password],



form[action="/login"] input[type=text],form[action="/login"] input[type=password],



form#login input[type=text],form#login input[type=password]{



 display:block



 width:100%



 height:var(--input-h)



 box-sizing:border-box



 padding:.6rem .8rem



 border-radius:12px



 border:1px solid rgba(255,255,255,.08)



 background:rgba(0,0,0,.35)



 color:#fff;outline:none}



.login-form input:focus{border-color:rgba(59,130,246,.6)



box-shadow:0 0 0 3px rgba(59,130,246,.25)}



.btn-primary,.login-btn{display:block



width:100%



height:var(--input-h)



border-radius:12px



border:0



cursor:pointer



background:#1a56db;color:#fff;font-weight:600}



.brand{display:flex



align-items:center



gap:.6rem}.brand img.logo{height:28px



opacity:.9}.brand .title{font-weight:700



letter-spacing:.2px}



.particles-bg,#tsparticles,#particles-js{position:fixed;inset:0;z-index:-1;pointer-events:none;opacity:.35}



.particles-js-canvas-el{opacity:.35!important}



""".lstrip()



if not css.exists() or not all(k in css.read_text(encoding="utf-8", errors="ignore") for k in need):



    css.write_text(base_css, encoding="utf-8")







# ---- Logo default



logo = IMG / "logo.svg"



if not logo.exists():



    logo.write_text(



        """<svg xmlns="http://www.w3.org/2000/svg" width="160" height="40" viewBox="0 0 160 40">



<defs><linearGradient id="g" x1="0" x2="1"><stop stop-color="#7c3aed"/><stop offset="1" stop-color="#2563eb"/></linearGradient></defs>  # noqa: E501



<rect rx="8" width="160" height="40" fill="url(#g)"/>



<path d="M18 10l10 5v6c0 6-6 9-10 10-4-1-10-4-10-10v-6l10-5z" fill="#111827" opacity=".95"/>



<text x="48" y="26" font-family="Inter,Segoe UI,Arial" font-size="16" fill="#fff" font-weight="700">SatpamBot</text>



</svg>""",



        encoding="utf-8",



    )







# ---- base.html: tautkan CSS & brand



base_html = TPL / "base.html"



if base_html.exists():



    b = base_html.read_text(encoding="utf-8", errors="ignore")



    if "dashboard.css" not in b:



        b = b.replace(



            "</head>",



            "  <link rel=\"stylesheet\" href=\"{{ url_for('static', filename='dashboard.css') }}\">\n</head>",



        )



    if 'class="brand"' not in b and "<nav" in b:



        b = b.replace(



            "<nav",



            '<nav>\n  <div class="brand">\n    <img class="logo" src="{{ url_for(\'static\', filename=\'img/logo.svg\') }}" alt="SatpamBot">\n    <span class="title">SatpamBot</span>\n  </div>\n',  # noqa: E501



            1,



        )



        b = b.replace("<nav>\n<nav", "<nav")



    base_html.write_text(b, encoding="utf-8")







# ---- login.html: pastikan ada tombol submit & wrapper



login_html = TPL / "login.html"



if login_html.exists():



    t = login_html.read_text(encoding="utf-8", errors="ignore")



    if "<form" in t:



        head, rest = t.split("<form", 1)



        tag, body = rest.split(">", 1)



        if "class=" not in tag:



            tag += ' class="login-form"'



        elif "login-form" not in tag:



            tag = tag.replace('class="', 'class="login-form ')



        rest = tag + ">" + body



        t = head + "<form" + rest



    if "login-card" not in t:



        t = t.replace("<form", '<div class="login-card">\n<form', 1).replace("</form>", "</form>\n</div>", 1)



    if 'type="submit"' not in t and ">Login<" not in t:



        t = t.replace(



            "</form>",



            '\n  <div class="form-row"><button type="submit" class="login-btn btn-primary">Login</button></div>\n</form>',  # noqa: E501



            1,



        )



    login_html.write_text(t, encoding="utf-8")







# ---- app.py: tambah /discord/login & /upload/background



APP.parent.mkdir(parents=True, exist_ok=True)



s = APP.read_text(encoding="utf-8", errors="ignore") if APP.exists() else ""



m = re.search(r"^\s*([A-Za-z_]\w*)\s*=\s*Flask\(", s, flags=re.M)



app_var = m.group(1) if m else "app"











def ensure_import(line):



    global s



    if line not in s:



        s = line + "\n" + s











ensure_import("from werkzeug.utils import secure_filename")



if "from flask import" in s:



    s = re.sub(



        r"from flask import\s+([^\n]+)",



        lambda m: "from flask import "



        + ", ".join(



            sorted(



                set([x.strip() for x in (m.group(1) + ", request, jsonify, redirect, url_for").split(",") if x.strip()])



            )



        ),



        s,



        count=1,



    )



else:



    ensure_import("from flask import request, jsonify, redirect, url_for")







if f'@{app_var}.get("/discord/login")' not in s and '@app.get("/discord/login")' not in s:



    s += f"""







# --- stub: /discord/login (redirect ke /login) ---



@{app_var}.get("/discord/login")



def discord_login_stub():



    return redirect(url_for("login"))



"""







if f'@{app_var}.post("/upload/background")' not in s and '@app.post("/upload/background")' not in s:



    # pakai kurung kurawal ganda agar tidak dievaluasi saat skrip ini berjalan



    s += f"""







# --- upload background ke static/uploads ---



@{app_var}.post("/upload/background")



def upload_background():



    file = request.files.get("file")



    if not file:



        return jsonify(ok=False, error="no file"), 400



    save_dir = os.path.join(os.path.dirname(__file__), "static", "uploads")



    os.makedirs(save_dir, exist_ok=True)



    from datetime import datetime



    raw = file.filename or "background.bin"



    name, ext = os.path.splitext(raw)



    fname = f"bg_{{{{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}}}}{{{{ext or '.bin'}}}}"



    path = os.path.join(save_dir, fname)



    file.save(path)



    rel = f"uploads/{{{{fname}}}}"



    return jsonify(ok=True, path=f"/static/{{{{rel}}}}")



"""



APP.write_text(s, encoding="utf-8")



print("PATCH DONE: logo ✓, CSS ✓, tombol Login ✓, /discord/login ✓, /upload/background ✓")


