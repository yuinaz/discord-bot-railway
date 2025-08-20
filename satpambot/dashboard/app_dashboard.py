from satpambot.dashboard.live_routes import register_live_routes
import time
import json
# -*- coding: utf-8 -*-
"""Patched dashboard app — themes list + upload logo/background + ui-config logo_url"""
from __future__ import annotations
import os, json, time
from pathlib import Path
from typing import Dict, Any
from flask import Flask, jsonify, request, send_from_directory, Blueprint, render_template
from werkzeug.utils import secure_filename

APP_ROOT = Path(__file__).resolve().parent
DATA_DIR = Path('data')
UPLOAD_DIR = DATA_DIR / 'uploads'
THEMES_DIR = DATA_DIR / 'themes'
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
THEMES_DIR.mkdir(parents=True, exist_ok=True)

CONFIG_PATH = DATA_DIR / 'ui_config.json'
DEFAULT_CONFIG = {
    'theme': 'Dark',
    'accent': '#2563eb',
    'bg_mode': 'None',
    'bg_url': '',
    'apply_login': False,
    'logo_url': ''
}

def _load_config() -> Dict[str, Any]:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding='utf-8'))
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()

def _save_config(cfg: Dict[str, Any]):
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding='utf-8')

def _themes_builtin():
    return ['Dark','Light','Nord','Dracula','Ocean','Forest','Aurora','Neo','Solar','Monokai']

def _themes_custom():
    names = []
    if THEMES_DIR.exists():
        for p in THEMES_DIR.glob('*.json'):
            names.append(p.stem)
    return sorted(set(names))

def create_app():
    app = Flask('satpambot_dashboard', static_folder=None)

    static_bp = Blueprint('dashboard_static', __name__, static_folder=str(APP_ROOT / 'static'))
    app.register_blueprint(static_bp, url_prefix='/dashboard-static')

    @app.route('/uploads/<path:filename>')
    def uploads(filename: str):
        return send_from_directory(str(UPLOAD_DIR), filename, conditional=True)

    @app.get('/api/ui-config')
    def get_ui_config():
        cfg = _load_config()
        return jsonify({
            'theme': cfg.get('theme'),
            'accent': cfg.get('accent'),
            'bg_mode': cfg.get('bg_mode'),
            'bg_url': cfg.get('bg_url'),
            'apply_login': bool(cfg.get('apply_login')),
            'logo_url': cfg.get('logo_url','')
        })

    @app.post('/api/ui-config')
    def post_ui_config():
        payload = request.get_json(force=True, silent=True) or {}
        cfg = _load_config()
        theme = payload.get('theme') or payload.get('Theme') or payload.get('theme_name')
        if theme: cfg['theme'] = str(theme)
        accent = payload.get('accent') or payload.get('accent_color')
        if accent: cfg['accent'] = str(accent)
        bg_mode = payload.get('bg_mode') or payload.get('background_mode')
        if bg_mode: cfg['bg_mode'] = str(bg_mode)
        bg_url = payload.get('bg_url') or payload.get('background_url')
        if bg_url is not None: cfg['bg_url'] = str(bg_url)
        apply_login = payload.get('apply_login') or payload.get('apply_to_login')
        if apply_login is not None: cfg['apply_login'] = bool(apply_login)
        logo_url = payload.get('logo_url')
        if logo_url is not None: cfg['logo_url'] = str(logo_url)
        _save_config(cfg)
        return jsonify({'ok': True, 'config': cfg})

    @app.get('/api/themes')
    def api_themes():
        all_names = list(dict.fromkeys(_themes_builtin() + _themes_custom()))
        return jsonify({'themes': all_names, 'count': len(all_names)})

    @app.post('/api/upload/background')
    def upload_bg():
        f = request.files.get('file')
        if not f: return jsonify({'ok': False, 'error': 'no file'}), 400
        name = secure_filename(f.filename or 'bg')
        ts = time.strftime('%Y%m%d_%H%M%S')
        ext = os.path.splitext(name)[1] or '.jpg'
        out = UPLOAD_DIR / f'bg_{ts}{ext}'
        f.save(out)
        if request.args.get('apply') == '1':
            cfg = _load_config()
            cfg['bg_url'] = f'/uploads/{out.name}'
            _save_config(cfg)
        return jsonify({'ok': True, 'path': f'/uploads/{out.name}'})

    @app.post('/api/upload/logo')
    def upload_logo():
        f = request.files.get('file')
        if not f: return jsonify({'ok': False, 'error': 'no file'}), 400
        name = secure_filename(f.filename or 'logo')
        ts = time.strftime('%Y%m%d_%H%M%S')
        ext = os.path.splitext(name)[1] or '.png'
        out = UPLOAD_DIR / f'logo_{ts}{ext}'
        f.save(out)
        cfg = _load_config()
        cfg['logo_url'] = f'/uploads/{out.name}'
        _save_config(cfg)
        return jsonify({'ok': True, 'path': f'/uploads/{out.name}'})

    START = time.time()
    @app.get('/healthz')
    def healthz(): return 'ok', 200

    @app.get('/uptime')
    def uptime(): return jsonify({'uptime_sec': int(time.time()-START)})

    @app.get('/dashboard/settings')
    def page_settings(): return render_template('settings.html')

    @app.get('/dashboard')
    def page_dashboard(): return render_template('dashboard.html')

    @app.get('/login')
    def page_login(): return render_template('login.html')

    return app

app = create_app()
if __name__ == '__main__':
    port = int(os.getenv('PORT', '10000'))
    app.run(host='0.0.0.0', port=port, debug=False)

try:
    register_live_routes(app)
except Exception:
    pass
