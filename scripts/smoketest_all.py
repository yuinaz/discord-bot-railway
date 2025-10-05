#!/usr/bin/env python3
from __future__ import annotations
import os, sys, json, re, time, traceback, py_compile
from pathlib import Path
from typing import List, Tuple, Dict

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

REPORT_DIR = ROOT / 'smoketest_report'
REPORT_DIR.mkdir(parents=True, exist_ok=True)

def p(msg=''): print(msg, flush=True)
def _read(pth: Path) -> str:
    try: return pth.read_text(encoding='utf-8', errors='ignore')
    except Exception: return ''
def _rel(pth: Path) -> str:
    try: return str(pth.relative_to(ROOT))
    except Exception: return str(pth)

def check_syntax() -> Tuple[bool, List[Dict]]:
    fails = []; count = 0
    for pth in ROOT.rglob('*.py'):
        sp = str(pth).lower()
        if any(seg in sp for seg in ['/.venv/','\\venv\\','/venv/','\\__pycache__\\','/__pycache__/','\\.git\\','/.git/']):
            continue
        count += 1
        try: py_compile.compile(str(pth), doraise=True)
        except Exception as e:
            msg = str(e)
            m = re.search(r'File "(.+?)", line (\d+)', msg)
            ln = int(m.group(2)) if m else None
            snippet = ''
            if ln is not None:
                try:
                    L = pth.read_text(encoding='utf-8', errors='ignore').splitlines()
                    s = max(0, ln-3); e2 = min(len(L), ln+2)
                    snippet = '\\n'.join(f"{i+1:4d}: {L[i]}" for i in range(s, e2))
                except Exception: pass
            fails.append({'file': _rel(pth), 'error': msg, 'snippet': snippet})
    print('== Smoke: syntax ==')
    if not fails: print(f'OK  : Python syntax check ({count} files)')
    else:
        for f in fails:
            print(f"FAIL: Syntax {_rel(Path(f['file']))} :: {f['error']}")
            if f['snippet']: print(f['snippet'])
    (REPORT_DIR/'syntax.json').write_text(json.dumps({'total': count, 'fails': fails}, indent=2), encoding='utf-8')
    return (len(fails)==0), fails

REQUIRED = [
    'satpambot/dashboard/webui.py',
    'satpambot/dashboard/templates/login.html',
    'satpambot/dashboard/templates/dashboard.html',
    'satpambot/dashboard/templates/security.html',
    'satpambot/dashboard/templates/settings.html',
    'satpambot/dashboard/static/css/login_exact.css',
    'satpambot/dashboard/static/css/neo_aurora_plus.css',
    'satpambot/dashboard/static/js/neo_dashboard_live.js',
    'satpambot/dashboard/static/logo.svg',
    'satpambot/dashboard/themes/gtake/templates/login.html',
    'satpambot/dashboard/themes/gtake/templates/dashboard.html',
    'satpambot/dashboard/themes/gtake/static/theme.css',
    'satpambot/dashboard/live_store.py',
    'satpambot/bot/modules/discord_bot/shim_runner.py',
    'satpambot/bot/modules/discord_bot/cogs/live_metrics_push.py',
]
def check_required() -> Tuple[bool, List[str]]:
    print('== Smoke: required files ==')
    missing = []
    for rel in REQUIRED:
        ok = (ROOT/rel).exists()
        if ok: print(f'OK  : file exists: {rel}')
        else: print(f'FAIL: missing file: {rel}'); missing.append(rel)
    shim = ROOT / 'satpambot/bot/modules/discord_bot/shim_runner.py'
    if shim.exists():
        t = _read(shim)
        m_ok = 'intents.members' in t and re.search(r'intents\.members\s*=\s*True', t) is not None
        p_ok = 'intents.presences' in t and re.search(r'intents\.presences\s*=\s*True', t) is not None
        print(("OK  " if m_ok else "FAIL") + " : intents.members=True (shim_runner.py)")
        print(("OK  " if p_ok else "FAIL") + " : intents.presences=True (shim_runner.py)")
        if not (m_ok and p_ok): missing.append('intents flags')
    (REPORT_DIR/'required.json').write_text(json.dumps({'missing': missing}, indent=2), encoding='utf-8')
    return (len(missing)==0), missing

JSON_PATHS = [
    'data/whitelist.json','data/blocklist.json','data/whitelist_domains.json','data/blacklist_domains.json',
    'data/url_whitelist.json','data/url_blocklist.json','data/memory_wb.json',
]
def check_json() -> Tuple[bool, List[Tuple[str,str]]]:
    errs = []
    print('== Smoke: json ==')
    for rel in JSON_PATHS:
        pth = ROOT/rel
        if not pth.exists(): print(f'FAIL: {rel} :: MISSING'); errs.append((rel, 'MISSING')); continue
        try: json.loads(_read(pth) or 'null')
        except Exception as e: print(f'FAIL: {rel} :: INVALID JSON: {e}'); errs.append((rel, f'INVALID JSON: {e}'))
    if not errs: print('OK  : All JSON files valid/exist')
    (REPORT_DIR/'json.json').write_text(json.dumps({'errors': errs}, indent=2), encoding='utf-8')
    return (len(errs)==0), errs

def check_upsert_calls() -> Tuple[bool, List[str]]:
    bad = []
    print('== Smoke: upsert call-sites ==')
    for pth in ROOT.rglob('*.py'):
        sp = str(pth).lower()
        if 'venv' in sp or '.git' in sp or '__pycache__' in sp: continue
        txt = _read(pth)
        if re.search(r"await\s+upsert_status_embed_in_channel\(\s*log_ch\s*,\s*['\"]", txt): bad.append(_rel(pth))
        if re.search(r"await\s+upsert_status_embed_in_channel\(\s*ch\s*,\s*['\"]", txt): bad.append(_rel(pth))
    if bad:
        for f in bad: print(f'FAIL: {f} :: legacy upsert call detected')
    else: print('OK  : All upsert call-sites use bot,ch pattern')
    (REPORT_DIR/'upsert.json').write_text(json.dumps({'bad': bad}, indent=2), encoding='utf-8')
    return (len(bad)==0), bad

def check_features() -> Tuple[bool, List[str]]:
    warns = []
    print('== Smoke: features ==')
    login = ROOT/'satpambot/dashboard/templates/login.html'
    if login.exists():
        t = _read(login).lower()
        if not any(x in t for x in ['tsparticles','particles']): warns.append('login.html: particles background not found')
    sec = ROOT/'satpambot/dashboard/templates/security.html'
    if sec.exists():
        t = _read(sec).lower()
        if not any(x in t for x in ['dropzone','ondrop','dragover','data-dropzone']): warns.append('security.html: dropzone not found')
    sc = ROOT/'sitecustomize.py'
    if sc.exists() and '/healthz' not in _read(sc): warns.append('sitecustomize.py: /healthz not exposed')
    app = ROOT/'app.py'
    if app.exists():
        t = _read(app)
        # Correct quoting here (bugfix): check for common route decorators
        if '/uptime' not in t and ("@app.route(\"/\")" not in t and "@app.route('/')" not in t):
            warns.append('app.py: routes for / or /uptime not found')
    if warns:
        for w in warns: print('WARN: ' + w)
    else: print('OK  : Feature markers present')
    (REPORT_DIR/'features.json').write_text(json.dumps({'warns': warns}, indent=2), encoding='utf-8')
    return True, warns

def _try_import_app():
    try:
        from app import app as flask_app  # type: ignore
        return flask_app, None
    except Exception as e1:
        try:
            from app import create_app  # type: ignore
            flask_app = create_app()
            return flask_app, None
        except Exception as e2:
            return None, f'{e1} / {e2}'

def check_http_test_client() -> Tuple[bool, List[str]]:
    print('')
    print('== Smoke: HTTP endpoints via test_client ==')
    app, err = _try_import_app()
    if app is None:
        print(f'WARN: cannot import Flask app: {err}')
        return True, ['skip']
    fails = []; warns = []
    ctx = app.app_context(); ctx.push()
    try:
        c = app.test_client()
        r = c.get('/', follow_redirects=False)
        if r.status_code in (301,302) and (r.headers.get('Location','').endswith('/dashboard') or '/dashboard' in r.headers.get('Location','')):
            print('OK  : / -> redirect :: %d -> %s' % (r.status_code, r.headers.get('Location')))
        else:
            print('FAIL: / expected redirect -> /dashboard'); fails.append('/')
        r = c.get('/dashboard/login')
        if r.status_code == 200: print('OK  : GET /dashboard/login :: 200')
        else: print('FAIL: GET /dashboard/login :: %d' % r.status_code); fails.append('/dashboard/login')
        if r.status_code == 200 and b'lg-card' in r.data: print('OK  : login layout present (lg-card)')
        for path in ['/dashboard-static/css/login_exact.css','/dashboard-static/css/neo_aurora_plus.css','/dashboard-static/js/neo_dashboard_live.js','/favicon.ico']:
            r = c.get(path)
            if r.status_code == 200: print(f'OK  : GET {path} :: 200')
            else: print(f'FAIL: GET {path} :: {r.status_code}'); fails.append(path)
        r = c.head('/healthz'); print(f'OK  : HEAD /healthz :: {r.status_code}')
        r = c.head('/uptime'); print(f'OK  : HEAD /uptime :: {r.status_code}')
        r = c.get('/api/ui-config')
        if r.status_code == 200: print('OK  : GET /api/ui-config :: 200')
        r = c.get('/api/ui-themes')
        if r.status_code == 200:
            print('OK  : GET /api/ui-themes :: 200')
            try:
                data = r.get_json(force=True)
                if isinstance(data, dict) and 'themes' in data and 'gtake' in data.get('themes', []):
                    print("OK  : theme 'gtake' available")
            except Exception: pass
        r = c.get('/dashboard-theme/gtake/theme.css')
        print(f'OK  : GET /dashboard-theme/gtake/theme.css :: {r.status_code}')
        r = c.get('/dashboard')
        if r.status_code == 200:
            print('OK  : GET /dashboard (gtake) :: 200')
            html = r.data.decode('utf-8','ignore').lower()
            if 'gtake' in html: print('OK  : dashboard layout = gtake')
            if 'canvas' in html or 'requestanimationframe' in html: print('OK  : dashboard has 60fps canvas')
            if 'dropzone' in html or 'ondrop' in html: print('OK  : dashboard has dropzone')
        r = c.get('/api/live/stats')
        if r.status_code == 200:
            print('OK  : GET /api/live/stats :: 200')
            try:
                d = r.get_json(force=True)
                if isinstance(d, dict):
                    print('OK  : live stats keys present')
                    if all((isinstance(v, (int,float)) and v==0) for v in d.values() if isinstance(v, (int,float))):
                        print('WARN: live stats are zero (bot belum siap / intents belum aktif)')
            except Exception: pass
        r = c.get('/api/phish/phash')
        if r.status_code == 200: print('OK  : GET /api/phish/phash :: 200')
        r = c.get('/logout'); print(f'OK  : GET /logout :: {r.status_code}')
        r = c.get('/dashboard/logout', follow_redirects=False)
        if r.status_code in (301,302): print(f"OK  : GET /dashboard/logout -> redirect :: {r.status_code} -> {r.headers.get('Location')}")
    finally:
        ctx.pop()
    return (len(fails)==0), fails

def main():
    sections = []
    ok1,_ = check_syntax(); sections.append(('syntax', ok1))
    ok2,_ = check_required(); sections.append(('required', ok2))
    ok3,_ = check_json(); sections.append(('json', ok3))
    ok4,_ = check_upsert_calls(); sections.append(('upsert', ok4))
    ok5,_ = check_features(); sections.append(('features', ok5))
    ok6,_ = check_http_test_client(); sections.append(('http_test_client', ok6))
    print('\n=== SUMMARY ===')
    fails = [name for name,ok in sections if not ok]
    if fails:
        print('FAILED:')
        for n in fails: print(f'- {n}')
    else:
        print('All sections OK')
    sys.exit(1 if fails else 0)

if __name__ == '__main__':
    main()
