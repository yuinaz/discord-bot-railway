
# SatpamBot — Useful Features Pack

## Baru di patch ini
1. **Nap adaptif + Noon Relax**
   - Jeda siang otomatis (default 12:00 WIB, durasi 30 menit).
   - Perintah cepat: `quiet now <menit>` untuk paksa nap sementara.

2. **Resource Monitor (embed)**
   - Periodik monitor CPU/Mem/Disk, DM owner kalau melewati ambang.
   - Perintah: `status now` / `/status_now`.

3. **CrashGuard**
   - Deteksi lonjakan error (default >12/10m), otomatis switch **half-power** + DM owner.
   - Perintah: `errors recent` (ringkasan 15 error terakhir).

4. **Auto Update — Approval Gate**
   - Paket **crucial** (default: openai, discord.py, numpy, pandas, Pillow) butuh approval:  
     DM `/approve_update <package>` (berlaku 1 jam).
   - `update check`, `update apply` tetap ada; di Render → report-only.

5. **Config Manager — Import ENV Now**
   - DM `import env` untuk re-import `SatpamBot.env` dan memicu DM **Import Report**.

## Konfigurasi opsional (via config JSON / DM `config set`)
- `RELAX_NOON_ENABLE=true`
- `RELAX_NOON_START=12:00`
- `RELAX_NOON_DURATION_MIN=30`
- `RELAX_TZ_OFFSET_MIN=420` (WIB)
- `RESMON_INTERVAL_SEC=300`
- `RESMON_CPU_WARN=85`
- `RESMON_MEM_WARN=85`
- `RESMON_DISK_WARN=90`
- `RESMON_COOLDOWN_SEC=1800`
- `STATUS_CHANNEL_ID=<ID channel, opsional>`
- `CRUCIAL_PACKAGES=openai,discord.py,numpy,pandas,Pillow`

## Pasang
Extract patch ke **root repo**, commit & jalankan seperti biasa.
