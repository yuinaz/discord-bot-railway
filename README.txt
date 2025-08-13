Full Dashboard Assets Patch
===========================

- app.py (patched):
  * Menulis upload background/logo ke asset_history (aktif otomatis + emit socketio 'asset_updated')
  * Registrasi Assets Manager blueprint
- assets_manager.py + templates/settings_assets.html
  * Halaman /assets-manager untuk galeri background/logo dengan pagination (Prev/Next), Set Active, Delete, Download
- modules/discord_bot/helpers/paginator.py + threaded_log.py + cogs/log_viewer.py
  * Command /banlog atau !banlog: buat thread + embed paginated

Cara pakai:
1) Backup project.
2) Replace file app.py dengan versi di bundle ini.
3) Tambahkan file lainnya sesuai struktur folder.
4) Jalankan lokal: python run_local.py --threading
5) Cek:
   - http://127.0.0.1:8080/assets-manager
   - /upload/background dan /upload/logo menambah entry ke asset_history dan langsung aktif.
   - Di Discord: /banlog untuk thread + paginator.
6) Commit & push.
