# Patch Notes - 2025-08-16T02:50:14.643807Z

Added/ensured the following files for dashboard + login with live particle:

- templates/login.html  -> created
- templates/dashboard.html  -> created
- static/css/auth.css  -> created
- static/js/particles_login.js  -> created
- static/js/dashboard.js  -> created
- static/js/mini_monitor.js  -> created

base.html status: missing_created
- `templates/base.html` created (Bootstrap 5 skeleton).

**Endpoints expected:**
- GET `/login` -> render `templates/login.html`
- GET `/` -> render `templates/dashboard.html`
- GET `/api/stats`, `/api/traffic`, `/api/top_guilds`, `/api/mini-monitor` -> for dynamic widgets

If your `app.py` differs, wire these routes accordingly.
