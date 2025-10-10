#!/usr/bin/env python3
from __future__ import annotations

# Idempotent patcher: hanya menambah file MINIMAL kalau hilang.
from pathlib import Path
import base64

ROOT = Path(__file__).resolve().parents[1]
DASH = ROOT / "satpambot" / "dashboard"

def ensure_file(path: Path, content: bytes | str):
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, str):
        content = content.encode("utf-8")
    path.write_bytes(content)
    return True

def main():
    print(f"[patch] repo: {ROOT}")
    created = []

    # 1) favicon (fallback mini)
    ico_b64 = (
        "AAABAAEAEBAAAAEAIABoBAAAFgAAACgAAAAQAAAAIAAAAAEAGAAAAAAAQAAAAAAAAAAAAAAA"
        "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        "AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD///8A////AP///wD/"
        "//8A////AP///wD///8A////AP///wD///8A////AP///wAAAAA="
    )
    if ensure_file(DASH/"static"/"favicon.ico", base64.b64decode(ico_b64)):
        created.append("static/favicon.ico")

    # 2) CSS/JS minimal (hanya jika hilang)
    if ensure_file(DASH/"static"/"css"/"login_exact.css",
        "/* minimal login */\n.lg-card{max-width:420px;margin:10vh auto;padding:24px;"
        "background:#1118;border:1px solid #fff2;border-radius:16px;color:#e6e8ee;}\n"):
        created.append("static/css/login_exact.css")

    if ensure_file(DASH/"static"/"css"/"neo_aurora_plus.css",
        "/* minimal dashboard */\n.neo-bg{min-height:100vh;background:linear-gradient(160deg,#0b0f1a,#091d2e);} "
        ".card{background:#0c1220cc;border:1px solid #ffffff22;border-radius:16px;padding:16px;color:#dfe3ea}\n"):
        created.append("static/css/neo_aurora_plus.css")

    if ensure_file(DASH/"static"/"js"/"neo_dashboard_live.js",
        "(function(){function q(u,cb){fetch(u).then(r=>r.json()).then(cb).catch(()=>{});} "
        "setInterval(function(){q('/api/live/stats',function(j){var e=document.getElementById('statsRaw');"
        "if(e){e.textContent=JSON.stringify(j);}});},2000);}());"):
        created.append("static/js/neo_dashboard_live.js")

    # 3) logo.svg minimal
    if ensure_file(DASH/"static"/"logo.svg",
        '<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64">'
        '<rect width="100%" height="100%" fill="#0b0f1a"/><text x="50%" y="54%" fill="#9ad1ff" '
        'font-size="18" text-anchor="middle" font-family="Arial">SB</text></svg>'):
        created.append("static/logo.svg")

    # 4) templates minimal (login/dashboard) hanya kalau hilang
    if ensure_file(DASH/"templates"/"login.html",
        "<!doctype html><html lang='id'><head><meta charset='utf-8'>"
        "<link rel='stylesheet' href='/dashboard-static/css/login_exact.css'>"
        "<link rel='stylesheet' href='/dashboard-static/themes/gtake/theme.css'>"
        "<title>Login</title></head><body class='neo-bg'><div class='lg-card'>"
        "<h2>Login</h2><form method='post'><input name='username' placeholder='Username'/>"
        "<input name='password' type='password' placeholder='Password'/>"
        "<button type='submit'>Login</button></form></div></body></html>"):
        created.append("templates/login.html")

    if ensure_file(DASH/"templates"/"dashboard.html",
        "<!doctype html><html lang='id'><head><meta charset='utf-8'>"
        "<link rel='stylesheet' href='/dashboard-static/css/neo_aurora_plus.css'>"
        "<link rel='stylesheet' href='/dashboard-theme/gtake/theme.css'>"
        "<title>Dashboard</title></head><body class='neo-bg'>"
        "<div class='card'><h1>Dashboard</h1><pre id='statsRaw'></pre>"
        "<canvas id='activityChart' width='600' height='220'></canvas></div>"
        "<script src='/dashboard-static/js/neo_dashboard_live.js'></script></body></html>"):
        created.append("templates/dashboard.html")

    # 5) theme gtake minimal
    if ensure_file(DASH/"themes"/"gtake"/"templates"/"login.html",
        "<!doctype html><html lang='id'><head><meta charset='utf-8'>"
        "<link rel='stylesheet' href='/dashboard-static/themes/gtake/theme.css'>"
        "<title>Login</title></head><body class='neo-bg'><div class='lg-card'>"
        "<h2>Login</h2><form method='post'><input name='username'/><input name='password' type='password'/>"
        "<button type='submit'>Login</button></form></div></body></html>"):
        created.append("themes/gtake/templates/login.html")

    if ensure_file(DASH/"themes"/"gtake"/"templates"/"dashboard.html",
        "<!doctype html><html lang='id'><head><meta charset='utf-8'>"
        "<link rel='stylesheet' href='/dashboard-theme/gtake/theme.css'>"
        "<title>Dashboard</title></head><body class='neo-bg'>"
        "<header class='toprow'><div class='crumbs'><span>Home</span>"
        "<span class='sep'>/</span><span class='muted'>Dashboard</span></div>"
        "<div class='toptools'><button class='pill sm' onclick='history.back()'>Back</button>"
        "<a class='pill sm' href='/dashboard'>Home</a>"
        "<a class='pill sm' href='/dashboard/settings'>Settings</a>"
        "<a class='pill sm' href='/dashboard/logout'>Logout</a></div></header>"
        "<main class='wrap'><section class='card'><h2>Traffic</h2>"
        "<canvas id='activityChart' width='640' height='240'></canvas></section>"
        "<section class='card'><h2>Drop Zone</h2>"
        "<input id='dashPick' type='file' hidden><div id='dashDrop' "
        "style='border:1px dashed #6aa; padding:24px;'>Drag & Drop here</div></section></main>"
        "<script src='/dashboard-static/js/neo_dashboard_live.js'></script></body></html>"):
        created.append("themes/gtake/templates/dashboard.html")

    if ensure_file(DASH/"themes"/"gtake"/"static"/"theme.css",
        "/* G.TAKE minimal */\n.neo-bg{min-height:100vh;background:linear-gradient(160deg,#0b0f1a,#081a2a);} "
        ".wrap{max-width:1100px;margin:24px auto;display:grid;gap:16px;grid-template-columns:1fr 1fr;} "
        ".card{background:#0c1220cc;border:1px solid #ffffff22;border-radius:16px;padding:16px;color:#e6e8ee}"
        ".pill{display:inline-flex;align-items:center;padding:6px 10px;border-radius:999px;background:#fff1;border:1px solid #fff3;color:#e6e8ee;text-decoration:none;} "
        ".pill.sm{font-size:12px}.toprow{display:flex;justify-content:space-between;align-items:center;padding:12px 16px}\n"):
        created.append("themes/gtake/static/theme.css")

    if created:
        print("[patch] created:", ", ".join(created))
    else:
        print("[patch] nothing to do (everything exists)")

if __name__ == "__main__":
    main()
