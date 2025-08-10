# Deploy ke Render.com (Blueprint)

## 1) Push ke GitHub
- Pastikan repo berisi `Dockerfile` dan `render.yaml` ini.
- Jangan commit `.env.local` atau secret-sensitive. Isi secrets di dashboard Render.

## 2) Hubungkan ke Render
- Masuk ke Render → New → Blueprint → pilih repo.
- Render akan membaca `render.yaml` dan membuat 1 service **web** (docker).
- Klik **Deploy**.

## 3) Set Environment Variables (Dashboard Render)
Wajib/Umum:
- `DISCORD_TOKEN` (token produksi)
- `RENDER=true` (opsional; sudah diset di blueprint)
- (opsional) `DATABASE_URL` untuk Postgres

Keamanan & Integrasi:
- `VIRUSTOTAL_API_KEY` (opsional)
- `HF_API_TOKEN` (opsional)
- `DESKTOP_RESTART_TOKEN` (untuk POST /restart)
- `DESKTOP_STATUS_SECRET` (untuk HMAC GET /desktop-status)
- (opsional) `UPTIMEROBOT_API_KEY`

**Catatan Port**  
Jangan set `PORT` manual. Render menyediakan `PORT` otomatis. App kita otomatis membaca nilai ini.

## 4) Health Check & UptimeRobot
- Endpoint: `/healthcheck` → 200 OK
- Heartbeat untuk status bot: `/heartbeat`

## 5) Logs & Debug
- Render Logs akan menampilkan **[HEARTBEAT]** per interval.
- Jika bot tidak online: cek token, intents, permission, dan error logs.

## 6) Redeploy
- Perubahan pada repo akan auto-deploy (autoDeploy=true).
- Bisa juga trigger **Manual Deploy** di dashboard Render.
