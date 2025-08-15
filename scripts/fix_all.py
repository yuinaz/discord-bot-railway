import re, os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def insert_before(path: Path, pattern: str, block: str, marker: str):
    s = path.read_text(encoding="utf-8", errors="ignore")
    if marker in s:
        return False
    i = s.find(pattern)
    if i == -1:
        return False
    s = s[:i] + block + s[i:]
    path.write_text(s, encoding="utf-8")
    return True

def insert_after_line_contains(path: Path, needle: str, to_add: str, marker: str):
    s = path.read_text(encoding="utf-8", errors="ignore")
    if marker in s:
        return False
    lines = s.splitlines(True)
    out, done = [], False
    for ln in lines:
        out.append(ln)
        if (needle in ln) and (not done):
            indent = re.match(r"\s*", ln).group(0)
            out.append(indent + to_add + "\n")
            done = True
    if done:
        s2 = "".join(out)
        path.write_text(s2, encoding="utf-8")
    return done

def ensure_file(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

def patch_main_admin_login():
    p = ROOT / "main.py"
    s = p.read_text(encoding="utf-8", errors="ignore")

    # 1) Sisipkan helper di TOP-LEVEL, sebelum def serve_dashboard(
    helper_marker = "# == ADMIN_LOGIN_HELPER =="
    helper = f"""
{helper_marker}
def _bind_admin_login(app):
    \"\"\"Fallback login admin (username/password) tanpa OAuth.\"\"\"
    import os
    from flask import request, session, redirect as _redirect, render_template_string

    USER = os.getenv('ADMIN_USERNAME') or os.getenv('SUPER_ADMIN_USER')
    PASS = os.getenv('ADMIN_PASSWORD') or os.getenv('SUPER_ADMIN_PASS')

    app.config.setdefault('SECRET_KEY', os.getenv('FLASK_SECRET_KEY', 'dev-key'))
    app.config.setdefault('SESSION_COOKIE_SAMESITE', 'Lax')
    app.config.setdefault('SESSION_COOKIE_SECURE', True)

    LOGIN_HTML = \"\"\"<!doctype html><meta name=viewport content='width=device-width, initial-scale=1'>
    <style>
    body{{font-family:system-ui,-apple-system,Segoe UI,Roboto,Ubuntu,Helvetica,Arial,sans-serif;background:#0b0e14;color:#e6e6e6;display:grid;place-items:center;min-height:100vh;margin:0}}
    .card{{background:#141923;border:1px solid #222b3b;border-radius:16px;padding:28px;min-width:360px;max-width:520px;box-shadow:0 8px 32px rgba(0,0,0,.35)}}
    .brand{{display:flex;gap:10px;align-items:center;margin-bottom:12px}}
    .brand svg{{width:28px;height:28px}}
    input,button{{width:100%;padding:12px 14px;border-radius:10px}}
    input{{border:1px solid #334;background:#0f1320;color:#e6e6e6;margin-top:8px}}
    button{{margin-top:16px;border:none;background:#5865F2;color:#fff;font-weight:700;cursor:pointer}}
    .err{{color:#ff6b6b;margin:8px 0 0 0;font-size:.92rem}}
    </style>
    <div class=card>
      <div class=brand>
        <svg viewBox='0 0 24 24' fill='#5865F2'><path d='M12 2l3 4 5 1-3 4 1 5-6-3-6 3 1-5-3-4 5-1z'/></svg>
        <h2 style='margin:0'>SatpamBot • Admin</h2>
      </div>
      {% if err %}<div class=err>{{err}}</div>{% endif %}
      <form method=POST>
        <label>Username</label><input name=username autocomplete=username>
        <label>Password</label><input name=password type=password autocomplete=current-password>
        <button type=submit>Login</button>
      </form>
      <p style='opacity:.7;margin-top:10px'>Gunakan <code>ADMIN_USERNAME/ADMIN_PASSWORD</code> atau <code>SUPER_ADMIN_USER/SUPER_ADMIN_PASS</code>.</p>
    </div>
    \"\"\"  # noqa: E501

    @app.route('/admin/login', methods=['GET','POST'])
    def __admin_login():
        err=None
        if not USER or not PASS:
            return render_template_string('<p>Set ADMIN_USERNAME/ADMIN_PASSWORD atau SUPER_ADMIN_USER/SUPER_ADMIN_PASS di Render.</p>')
        if request.method=='POST':
            u=(request.form.get('username') or '').strip()
            p=(request.form.get('password') or '').strip()
            if u==USER and p==PASS:
                session['is_admin']=True; session['admin_user']=u
                return _redirect('/')
            err='Username / password salah'
        return render_template_string(LOGIN_HTML, err=err)

    @app.route('/logout')
    def __admin_logout():
        session.clear(); return _redirect('/')

    @app.route('/login')
    def __login_alias():
        return _redirect('/admin/login', 302)

    @app.route('/discord/login')
    def __discord_login_alias():
        return _redirect('/admin/login', 302)
"""
    inserted = insert_before(p, "def serve_dashboard(", helper, helper_marker)

    # 2) Panggil helper di jalur dashboard (Flask/SocketIO) & mini-web
    dash_call_marker = "# == BIND_LOGIN_DASH =="
    mini_call_marker = "# == BIND_LOGIN_MINI =="

    insert_after_line_contains(
        p, "app = getattr(mod, 'app'", f"{dash_call_marker}\n            _bind_admin_login(app)", dash_call_marker
    )
    insert_after_line_contains(
        p, "socketio = getattr(mod, 'socketio'", f"{dash_call_marker}\n                _bind_admin_login(app)", dash_call_marker
    )
    insert_after_line_contains(
        p, "mini = Flask(\"mini-web\")", f"{mini_call_marker}\n    _bind_admin_login(mini)", mini_call_marker
    )

def patch_cogs_loader_disable_image_poster():
    p = ROOT / "satpambot/bot/modules/discord_bot/cogs_loader.py"
    if not p.exists(): return
    s = p.read_text(encoding="utf-8", errors="ignore")
    if "DISABLED_COGS" not in s:
        s = s.replace(
            "def load_all_cogs(",
            "DISABLED_COGS = set((os.getenv('DISABLED_COGS') or 'image_poster').split(','))\n\ndef load_all_cogs("
        )
        s = s.replace(
            "for name in candidates:",
            "for name in candidates:\n        try:\n            _end = name.rsplit('.',1)[-1]\n            if _end in DISABLED_COGS:\n                continue\n        except Exception:\n            pass"
        )
        p.write_text(s, encoding="utf-8")

def patch_embed_only():
    # helper builder
    ensure_file(
        ROOT / "satpambot/bot/modules/discord_bot/helpers/ban_embed.py",
        """from discord import Embed, Colour
def build_ban_embed(target, *, reason=None, simulated=False):
    title = "💀 Simulasi Ban oleh SatpamBot" if simulated else "🔨 Ban oleh SatpamBot"
    desc  = f"{getattr(target,'mention',str(target))} terdeteksi mengirim pesan mencurigakan."
    if simulated: desc += "\\n\\n(Pesan ini hanya simulasi untuk pengujian.)"
    elif reason:  desc += f"\\n\\nAlasan: {reason}"
    emb = Embed(title=title, description=desc,
                colour=Colour.orange() if simulated else Colour.red())
    if simulated: emb.add_field(name="\\u200b", value="🧪 Simulasi testban", inline=False)
    return emb
"""
    )
    # override poster
    ensure_file(
        ROOT / "satpambot/bot/modules/discord_bot/helpers/ban_poster.py",
        """from .ban_embed import build_ban_embed
async def send_ban_poster(channel, target, *, reason=None, simulated=False, **kw):
    return await channel.send(embed=build_ban_embed(target, reason=reason, simulated=simulated))
async def post_ban_poster(channel, target, **kw): return await send_ban_poster(channel, target, **kw)
async def send_poster(channel, target, **kw):     return await send_ban_poster(channel, target, **kw)
async def post_ban(channel, target, **kw):        return await send_ban_poster(channel, target, **kw)
def build_poster(*a, **k): return None
def generate_ban_poster(*a, **k): return None
def render_ban_image(*a, **k): return None
def create_poster(*a, **k): return None
"""
    )
    # paksa !tb pakai embed
    tb = ROOT / "satpambot/bot/modules/discord_bot/cogs/testban_hybrid.py"
    if tb.exists():
        s = tb.read_text(encoding="utf-8", errors="ignore")
        if "helpers.ban_embed import build_ban_embed" not in s:
            s = re.sub(r"(^\s*from\s+discord\b.+?$)", r"\1\nfrom ..helpers.ban_embed import build_ban_embed", s, 1, flags=re.M)
        if "build_ban_embed(" not in s:
            s = re.sub(
                r"(@[^\n]*?(command|hybrid_command)[^\n]*?name\s*=\s*['\"]tb['\"][\s\S]{0,400}?\n\s*async\s+def\s+\w+\s*\([^)]*\)\s*:\s*\n)",
                r"\1        _target = (member if 'member' in locals() else ctx.author)\n        await ctx.send(embed=build_ban_embed(_target, simulated=True))\n        return\n",
                s, 1, flags=re.M,
            )
        tb.write_text(s, encoding="utf-8")

def patch_image_poster_guard():
    ip = ROOT / "satpambot/bot/modules/discord_bot/cogs/image_poster.py"
    if not ip.exists(): return
    s = ip.read_text(encoding="utf-8", errors="ignore")
    if "DISABLE_IMAGE_POSTER" in s and "startswith('!tb')" in s:
        return
    s = re.sub(
        r"(async\s+def\s+on_message\s*\(self,\s*message[^\)]*\)\s*:\s*\n)",
        r"\1        import os\n        if os.getenv('DISABLE_IMAGE_POSTER','1')!='0':\n            return\n        if getattr(message.author,'bot',False):\n            return\n        _c=(message.content or '').strip().lower()\n        if _c.startswith('!tb') or 'simulasi' in _c:\n            return\n        for _e in (message.embeds or []):\n            try:\n                _t=(_e.title or '').lower(); _d=(_e.description or '').lower()\n                if 'simulasi' in _t or 'simulasi' in _d:\n                    return\n            except Exception:\n                pass\n",
        s, count=1,
    )
    ip.write_text(s, encoding="utf-8")

def main():
    patch_main_admin_login()
    patch_cogs_loader_disable_image_poster()
    patch_embed_only()
    patch_image_poster_guard()
    print("[OK] patches applied")

if __name__ == "__main__":
    main()
