# SatpamBot — Auto Update Patch (Flat, migration-ready)

**Tidak mengubah Build/Start Command kamu.**  
- Build: `bash scripts/build_render.sh` (tetap)  
- Start: `python main.py` (tetap)

## Fitur
- **Updater PIP otomatis** (non-kritis): cek & update paket seperti `openai` ke versi terbaru **1.x** (aman), `python-dotenv`, dsb.
- **Owner‑gated untuk modul krusial** (ban/moderation/anti_image*): perlu persetujuan owner sebelum update.
- **Schedule**: cek tiap 4 hari (default), bisa diubah via slash command.
- **Rollback aman**: snapshot `requirements.lock.local` sebelum update; rollback otomatis jika smoke test gagal.
- **Render aware**: di Render, updater hanya **mencatat & minta redeploy** (runtime FS ephemeral). Di MiniPC, updater **benar‑benar install & restart**.
- **Tanpa ketergantungan Render ENV**: env bisa dari `.env` (lihat `sitecustomize.py`).

## File yang ditambahkan
- `scripts/build_render.sh` → pastikan deps dasar + `openai>=1,<2` + `python-dotenv` (tetap aman buat Render).
- `scripts/smoketest_render.py` → cek import ringan (non-fatal).
- `sitecustomize.py` → auto-load `.env` & default aman (stickers off, no DM).
- `updater_config.yaml` → allow/deny list & jadwal.
- `satpambot/bot/modules/discord_bot/cogs/auto_update_manager.py` → Cog updater.
- `scripts/update_from_git.py` → opsional tarik update dari Git (MiniPC), owner‑gated utk cogs krusial.
- `.env.sample` → contoh untuk MiniPC.

## Slash Commands (contoh)
- `/update check` – tampilkan paket yang outdated.
- `/update apply` – update paket **non‑kritis** (langsung).  
- `/update approve package <name>` – owner menyetujui paket tertentu (atau `/update approve all`).
- `/update schedule days:<n>` – atur interval cek (owner).

> Owner diambil dari ENV `OWNER_USER_ID`. Jika kosong, hanya admin discord (Manage Guild) yang bisa approve.
