# Render Auto-Boot Pack (Quiet + Auto-Thread + Live Config)

## Apa ini?
Paket siap-tempel supaya bot:
- **Jalan otomatis di Render** tanpa set ENV manual di dashboard.
- **Tenang (no DM ke user)** dan **auto-bikin thread** di `#log-botphising`.
- **Konfigurasi live** via `config/live_config.json` (dibaca periodik).
- Skema yang sama bisa dipakai di **MINIPC** (tinggal jalankan `scripts/start_render.sh`).

## File penting
- `scripts/start_render.sh` — entrypoint Render/MiniPC. Meload `SatpamBot.env` / `secrets/SatpamBot.env`, set default env, lalu jalanin bot.
- `config/live_config.json` — toggle runtime (quiet + thread on).
- `SatpamBot.env.template` — contoh ENV. Copy jadi `SatpamBot.env` dan isi token.
- `scripts/verify_render_setup.py` — cek cepat sebelum boot.

## Cara pakai di Render
1. Commit folder ini ke repo (bebas di mana; contoh di root atau `render/`).
2. Buat file `SatpamBot.env` (atau `secrets/SatpamBot.env`) dari template dan **isi DISCORD_TOKEN**.
3. Set **Start Command** di Render ke:
   ```bash
   bash scripts/start_render.sh
   ```
   (Jika folder ini tidak di root repo, sesuaikan path.)
4. Deploy. Script akan memuat ENV lokal dan menjalankan bot.

## Catatan Keamanan
- **Jangan** commit token ke repo publik.
- Lebih aman taruh `secrets/SatpamBot.env` dan gitignore folder `secrets/`.

## Migrasi ke MiniPC
- Cukup jalankan:
  ```bash
  bash scripts/start_render.sh
  ```
  Pastikan Python path sudah benar (root repo jadi working dir). Token diambil dari `SatpamBot.env`/`secrets/SatpamBot.env`.
