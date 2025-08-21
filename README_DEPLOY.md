# SatpamBot — Deploy Ready

## Endpoints penting
- `GET /healthz` — untuk UptimeRobot (HTTP 200 = sehat)
- `GET /api/live/stats` — data untuk live tile dashboard
- `POST /api/phish/phash` — tambah hash phishing (form-data: `file` atau `url`)
- `GET /api/phish/phash` — list hash phishing
- `POST /api/ui-config` — simpan theme/accent/bg/logo (opsional, jika dipakai)

## Static dashboard
- Di-serve pada prefix **/dashboard-static**, folder fisik `dashboard/static/`
- Semua template sudah pakai `<script src="/dashboard-static/js/...">`

## Render.com
- Service menjalankan `python main.py` dan **bind ke PORT** env yang diberikan Render
- Health check: `/healthz`
- Gunakan `LOG_LEVEL=INFO` (opsional)

## UptimeRobot
- Tambahkan monitor HTTP ke `https://<domain>/healthz`
