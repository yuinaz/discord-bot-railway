
PATCH ISI:
- app_fixed.py : perbaikan login (DB-first + sync env), change-password, route /ping, cache_bust
- templates/partials/mini_monitor.html : widget mini monitor (CPU/RAM/Uptime) untuk dashboard
- static/js/mini_monitor.js : polling /api/live_stats
- static/themes/default.css : theme fallback

Cara pasang ringkas:
1) Ganti app.py dengan app_fixed.py
   mv app_fixed.py app.py
2) Tambah partial & js ke project:
   - copy templates/partials/mini_monitor.html -> templates/partials/mini_monitor.html
   - copy static/js/mini_monitor.js -> static/js/mini_monitor.js
   - (opsional) copy static/themes/default.css -> static/themes/default.css
3) Sisipkan mini monitor di atas konten dashboard:
   Buka templates/dashboard.html, di dalam block content tambahkan:
       {% include 'partials/mini_monitor.html' %}
4) Commit & deploy.

Catatan:
- Change Password sekarang tersimpan di SQLite dan login menggunakan DB terlebih dahulu.
- Jika login pertama kali pakai ENV (SUPER_ADMIN_* atau ADMIN_PASSWORD), user & password otomatis disinkron ke DB.
- /ping tersedia untuk UptimeRobot (respon 'pong').
