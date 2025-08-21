
    import os, sys, hashlib
    from pathlib import Path

    ROOT = Path(__file__).resolve().parents[1]
    WEBUI = ROOT / "satpambot" / "dashboard" / "webui.py"
    STATIC = ROOT / "satpambot" / "dashboard" / "static"

    # Assets to ensure exist (create only if missing)
    ASSETS = {
        STATIC / "themes" / "gtake" / "theme.css": """/* fallback theme (only created if missing) */
:root{--bg:#0b0f1a;--card:#11182b;--muted:#9aa3b2;--text:#e6e8ee;--accent:#4f67ff;--accent-2:#7aa2ff;--radius:16px;--shadow:0 10px 30px rgba(0,0,0,.35)}
html,body{height:100%}*{box-sizing:border-box}
body{margin:0;background:#0b0f1a;color:var(--text);font-family:Inter,system-ui,-apple-system,Segoe UI,Roboto,Ubuntu,"Helvetica Neue",Arial,"Noto Sans"}
.wrapper{max-width:1200px;margin:0 auto;padding:16px}
.card{background:linear-gradient(180deg,rgba(255,255,255,.04),rgba(255,255,255,.02));border:1px solid rgba(255,255,255,.06);
  border-radius:var(--radius);box-shadow:var(--shadow);padding:16px}
h1,h2,h3{font-weight:700;margin:8px 0 12px} h1{font-size:28px} h2{font-size:22px} h3{font-size:18px}
button,.btn{border:0;background:linear-gradient(90deg,var(--accent),var(--accent-2));color:#fff;padding:10px 16px;border-radius:14px;cursor:pointer}
input,select,textarea{width:100%;border-radius:12px;border:1px solid rgba(255,255,255,.12);background:rgba(255,255,255,.04);color:var(--text);padding:10px 12px}
body.login-page,.login-page{min-height:100vh;display:flex;align-items:center;justify-content:center;padding:24px}
.login-card{padding:24px 22px}.login-title{margin-bottom:12px;font-size:22px;font-weight:700}.login-sub{color:var(--muted);margin-bottom:18px}
.stats-grid{display:grid;gap:16px;grid-template-columns:repeat(auto-fit,minmax(180px,1fr))}
.stat{padding:14px}.stat .label{color:var(--muted);font-size:13px}.stat .value{font-size:22px;font-weight:700;margin-top:4px}
.dnd-item{user-select:none;cursor:grab;padding:10px 12px;margin:8px 0;background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);border-radius:12px}
.dnd-item.dragging{opacity:.6;transform:scale(.98)}.dnd-placeholder{height:44px;border:1px dashed rgba(255,255,255,.2);border-radius:12px;margin:8px 0}
""",
        STATIC / "themes" / "gtake" / "main.css": '@import "/dashboard-static/themes/gtake/theme.css";\n',
        STATIC / "themes" / "gtake" / "style.css": '@import "/dashboard-static/themes/gtake/theme.css";\n',
        STATIC / "themes" / "gtake" / "dashboard.css": '@import "/dashboard-static/themes/gtake/theme.css";\n',
        STATIC / "css" / "login_layout_fix.css": """:root{--gap:16px}html,body{height:100%}body{margin:0}
.login-page,.login-center{min-height:100vh;display:flex;align-items:center;justify-content:center;padding:24px}
.login-center .card,.login-card{width:min(430px,94vw)}form.login-form{display:grid;gap:var(--gap)}\n""",
        STATIC / "css" / "login_modern.css": '@import "/dashboard-static/themes/gtake/theme.css";\n@import "/dashboard-static/css/login_layout_fix.css";\n',
        STATIC / "css" / "login_theme.css": '@import "/dashboard-static/themes/gtake/theme.css";\n@import "/dashboard-static/css/login_layout_fix.css";\n',
        STATIC / "css" / "dashboard_layout.css": ".dashboard-center{max-width:1200px;margin:0 auto;padding:16px}\n",
        STATIC / "js" / "ui_theme_bridge.js": "(function(){try{var l=document.createElement('link');l.rel='stylesheet';l.href='/dashboard-static/themes/gtake/theme.css';document.head.appendChild(l);}catch(e){};console.log('[ui_theme_bridge] ready');})();\n",
        STATIC / "js" / "login_apply_theme.js": "(function(){window.addEventListener('DOMContentLoaded',function(){try{document.body.classList.add('login-page');var root=document.querySelector('.login-center')||document.querySelector('.login-shell');if(!root){root=document.createElement('div');root.className='login-center';var form=document.querySelector('form')||document.querySelector('form#login')||document.querySelector('form[name=\"login\"]');if(form){var card=document.createElement('div');card.className='card login-card';var title=document.createElement('div');title.className='login-title';title.textContent='Masuk';var sub=document.createElement('div');sub.className='login-sub';sub.textContent='Gunakan kredensial admin yang valid.';form.classList.add('login-form');card.appendChild(title);card.appendChild(sub);card.appendChild(form);root.appendChild(card);document.body.innerHTML='';document.body.appendChild(root);}}var u=document.querySelector('input[name=\"username\"],input[type=\"email\"],input[type=\"text\"]');if(u&&!u.value)u.focus();}catch(e){};console.log('[login_apply_theme] centered');});})();\n",
        STATIC / "js" / "dnd_security.js": "(function(){function enableList(list){if(!list)return;var placeholder=document.createElement('div');placeholder.className='dnd-placeholder';var dragEl=null;list.querySelectorAll('[data-id],li,.dnd-item').forEach(function(item){item.setAttribute('draggable','true');item.classList.add('dnd-item');item.addEventListener('dragstart',function(e){dragEl=item;item.classList.add('dragging');e.dataTransfer.effectAllowed='move';try{e.dataTransfer.setData('text/plain',item.dataset.id||item.id||item.textContent.trim());}catch(_){ } item.parentNode.insertBefore(placeholder,item.nextSibling);});item.addEventListener('dragend',function(){item.classList.remove('dragging');if(placeholder.parentNode)placeholder.parentNode.replaceChild(item,placeholder);dragEl=null;save();});});list.addEventListener('dragover',function(e){e.preventDefault();var target=e.target.closest('.dnd-item');if(!target||target===placeholder||target===dragEl)return;var r=target.getBoundingClientRect();var before=(e.clientY-r.top)<r.height/2;if(before)target.parentNode.insertBefore(placeholder,target);else target.parentNode.insertBefore(placeholder,target.nextSibling);});function save(){var items=[].slice.call(list.querySelectorAll('.dnd-item')).map(function(el){return el.dataset.id||el.id||el.textContent.trim();});fetch('/api/security/reorder',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({list:list.getAttribute('data-dnd-list')||'security',items:items})}).catch(function(){});console.log('[dnd_security] saved order',items);} } enableList(document.querySelector('[data-dnd-list=\"security\"]')||document.querySelector('#security-list')||document.querySelector('.security-list'));console.log('[dnd_security] ready');})();\n",
    }

    def ensure(path: Path, content: str):
        if path.exists():
            print(f"[skip] {path} already exists")
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        print(f"[add ] {path}")

    # 1) Ensure assets exist
    for p, c in ASSETS.items():
        ensure(p, c)

    # 2) Append dashboard fallbacks into webui.py (idempotent)
    FALLBACK_MARK = "# <<< DASHBOARD_FALLBACKS_V1 >>>"
    APPEND = f"""{FALLBACK_MARK}
try:
    from flask import Response, request, redirect, send_from_directory
    from pathlib import Path as _P
    import logging as _logging, struct as _struct
    __SB_STATIC = _P(__file__).resolve().parent / "static"

    def __tiny_ico_bytes():
        w=h=16
        header=_struct.pack("<HHH",0,1,1)
        bih=_struct.pack("<IIIHHIIIIII",40,w,h*2,1,32,0,w*h*4,0,0,0,0)
        xor=b"\\x00\\x00\\x00\\x00"*(w*h); andmask=(b"\\x00\\x00\\x00\\x00")*h
        img=bih+xor+andmask; size=len(img); offset=6+16
        entry=_struct.pack("<BBBBBBHHII",w,h,0,0,1,32,size & 0xFFFF,(size>>16)&0xFFFF,offset,0)
        return header+entry+img

    def __register_dashboard_fallbacks(app):
        if not app.view_functions.get("dashboard_static_alias"):
            app.add_url_rule("/dashboard-static/<path:filename>","dashboard_static_alias",
                lambda filename: send_from_directory(str(__SB_STATIC), filename, conditional=True))

        if not app.view_functions.get("favicon"):
            def _favicon():
                p=__SB_STATIC / "favicon.ico"
                if p.exists(): return send_from_directory(str(__SB_STATIC), "favicon.ico", conditional=True)
                return Response(__tiny_ico_bytes(), mimetype="image/x-icon")
            app.add_url_rule("/favicon.ico","favicon",_favicon)

        if not app.view_functions.get("dashboard_login_get"):
            @app.get("/dashboard/login")
            def dashboard_login_get():
                return Response(\"\"\"<!doctype html><meta charset='utf-8'><title>Masuk • SatpamBot</title>
<link rel='stylesheet' href='/dashboard-static/themes/gtake/theme.css'>
<link rel='stylesheet' href='/dashboard-static/css/login_modern.css'>
<link rel='stylesheet' href='/dashboard-static/css/login_theme.css'>
<script src='/dashboard-static/js/ui_theme_bridge.js' defer></script>
<script src='/dashboard-static/js/login_apply_theme.js' defer></script>
<style>html,body{height:100%}body{margin:0;display:flex;align-items:center;justify-content:center;background:#0b0f1a}
._card{max-width:420px;width:92vw;background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.08);border-radius:16px;padding:22px;color:#e6e8ee;font-family:system-ui,Segoe UI,Roboto,Arial}
._title{font-size:22px;font-weight:700;margin:0 0 10px}._sub{opacity:.75;margin:0 0 16px}._row{margin:10px 0}
._in{width:100%;padding:10px 12px;border-radius:12px;border:1px solid rgba(255,255,255,.12);background:rgba(255,255,255,.04);color:#e6e8ee}
._btn{display:inline-block;padding:10px 16px;border-radius:14px;border:0;background:linear-gradient(90deg,#4f67ff,#7aa2ff);color:#fff;cursor:pointer}</style>
<body class='login-page'><div class='_card'><div class='_title'>Masuk</div><div class='_sub'>Gunakan kredensial admin yang valid.</div>
<form class='login-form' action='/dashboard/login' method='post' autocomplete='off'>
<div class='_row'><input class='_in' name='username' type='text' placeholder='Username' required></div>
<div class='_row'><input class='_in' name='password' type='password' placeholder='Password' required></div>
<div class='_row'><button class='_btn' type='submit'>LOGIN</button></div></form></div></body>\"\"\", mimetype="text/html; charset=utf-8")

        if not app.view_functions.get("dashboard_login_post"):
            @app.post("/dashboard/login")
            def dashboard_login_post():
                return redirect("/dashboard", code=303)

        _log=_logging.getLogger("werkzeug")
        if not getattr(_log, "_sb_hide_ping", False):
            class _NoPing(_logging.Filter):
                def filter(self, rec):
                    m=rec.getMessage()
                    return ("/uptime" not in m) and ("/healthz" not in m)
            _log.addFilter(_NoPing()); _log._sb_hide_ping=True

    if 'register_webui_builtin' in globals():
        _old=register_webui_builtin
        def register_webui_builtin(app):
            _old(app)
            try: __register_dashboard_fallbacks(app)
            except Exception: pass
    else:
        def register_webui_builtin(app):
            try: __register_dashboard_fallbacks(app)
            except Exception: pass
except Exception:
    pass
"""
    # Append if not present
    if not WEBUI.exists():
        WEBUI.parent.mkdir(parents=True, exist_ok=True)
        WEBUI.write_text("def register_webui_builtin(app):\n    pass\n", encoding="utf-8")

    text = WEBUI.read_text(encoding="utf-8", errors="ignore")
    if FALLBACK_MARK not in text:
        WEBUI.write_text(text + "\n\n" + APPEND, encoding="utf-8")
        print("[patch] webui.py fallbacks appended")
    else:
        print("[skip] webui.py already has fallbacks")

    print("Dashboard patch applied. Run smoketest with:")
    print("  python scripts/smoketest_dashboard.py")
