Render Free Plan – prod-safe guard for Flask dev server
======================================================
Tujuan:
- Hilangkan konflik port & spam "Serving Flask app ..." di Render.
- Pastikan hanya satu web server (yang dari main.py) berjalan.
- Bot tetap 24/7, healthcheck /healthz tetap OK.

Isi ZIP:
- patches/no_dev_server_in_prod.diff
- patches/apply_no_dev_server_guard.py
- patches/README-apply-patch.txt (file ini)

Cara pakai (pilih salah satu):

A) Script Python (Windows friendly)
----------------------------------
1) Copy folder `patches/` ini ke ROOT repo kamu.
2) Jalanin:
   PowerShell:
     py -3 patches\apply_no_dev_server_guard.py
   atau Git Bash/macOS/Linux:
     python3 patches/apply_no_dev_server_guard.py
3) Cek:
     python scripts/smoketest_all.py
4) Commit:
     git add -A && git commit -m "prod-safe: guard app.run() behind RUN_LOCAL_DEV"

B) Git apply diff
-----------------
1) Simpan `patches/no_dev_server_in_prod.diff` di repo root.
2) Jalanin:
     git apply -v patches/no_dev_server_in_prod.diff
3) Cek & commit seperti di atas.

ENV:
- Di Render: JANGAN set RUN_LOCAL_DEV (biarkan default "0").
- Di lokal (kalau mau dev server):
    Windows: setx RUN_LOCAL_DEV 1 (baru buka shell)
    Linux/macOS: export RUN_LOCAL_DEV=1
