
# HotEnv Reload — Safe Patch (Zip Drop-in)

**Tujuan:** menghilangkan warning
`RuntimeWarning: coroutine 'BotBase.reload_extension' was never awaited`
saat HotEnv me-reload cogs setelah `SatpamBot.env` berubah.

## Isi Zip
- `satpambot/bot/modules/discord_bot/helpers/hotenv_reload_helpers.py`
  – helper versi-agnostik untuk reload (support sync/async).
- `patches/patch_hot_env_reload_inplace.py`
  – skrip patch in-place ke `cogs/hot_env_reload.py`.

## Cara Pakai (3 langkah):
1. **Ekstrak** zip ini ke root repo SatpamBot (struktur folder akan sesuai).
2. Jalankan patcher:
   ```bash
   # Windows
   py -3 patches/patch_hot_env_reload_inplace.py
   # atau tentukan path file secara eksplifit:
   # py -3 patches/patch_hot_env_reload_inplace.py satpambot/bot/modules/discord_bot/cogs/hot_env_reload.py
   ```
   Output akan membuat backup: `hot_env_reload.py.bak-<epoch>`.
3. **Test cepat**:
   ```bash
   set PYTHONWARNINGS=error
   # edit/save SatpamBot.env untuk memicu reload
   # pastikan tidak ada lagi 'was never awaited'
   ```

## Catatan Teknis
- Patcher mengganti loop sederhana semacam:
  ```py
  for ext in exts:
      self.bot.reload_extension(ext)
  ```
  menjadi satu pemanggilan aman:
  ```py
  reload_extensions_safely(self.bot, exts, logger=globals().get("log"), skip_self=__name__)
  ```
- Helper akan otomatis:
  - *Skip* me-reload dirinya sendiri (mengurangi race).
  - Menangani API `reload_extension` yang sync **atau** async.
  - Menjadwalkan ke `bot.loop` kalau dipanggil dari thread watchdog.

Kalau struktur kode kamu berbeda dan patcher tidak menemukan pola loop,
jalankan lagi patcher dengan path file, atau kasih tahu aku—nanti kubuatin
patch yang disesuaikan dengan file-mu.
