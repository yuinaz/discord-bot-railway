# SatpamBot — Upgrade ke Versi Terbaru (2025-10-07)

## Ringkas
- **Aman di-upgrade** ke versi terbaru *dengan satu catatan*: di Windows lokal kamu (Python 3.10), **NumPy dibatasi < 2.3**.
- Di Render (Python 3.13), NumPy **2.3.3** aman.

## Kenapa?
- `discord.py 2.6.3` adalah rilis terbaru dan mendukung Python 3.8+.
- `aiohttp 3.13.0` adalah rilis terbaru dan tersedia wheel cp310/cp313.
- `Flask 3.1.2` terbaru.
- `openai 2.2.0` terbaru; kode kita sudah pakai `OpenAI(...).chat.completions.create(...)` jadi kompatibel.
- `NumPy 2.3.x` **tidak** mendukung Python 3.10; di lokal gunakan `2.2.6`.

## File yang disiapkan
- `requirements.latest.render.txt` → dipakai Render (Py 3.13).  
- `requirements.latest.local310.txt` → dipakai lokal Windows (Py 3.10).  
- `scripts/build_render.sh` → otomatis pakai `requirements.latest.render.txt` kalau ada.

## Cara upgrade di Render
1. Commit/push file-file ini ke repo.
2. Pastikan Build Command:  
   ```bash
   bash scripts/build_render.sh
   ```
3. Deploy. Build akan:
   - upgrade pip
   - install paket terbaru (file `requirements.latest.render.txt`)
   - jalanin semua **smoketest** (fatal jika gagal)

## Cara upgrade di Lokal (Windows, Python 3.10)
```powershell
python -m venv .venv
.\.venv\Scriptsctivate
pip install -r requirements.latest.local310.txt
# cek
python scripts\smoke_env.py
python scripts\smoke_local_all.py
```

## Catatan penting
- Render Free Plan: runtime `pip install` **tidak persisten**. Selalu update requirements & redeploy.
- Kalau suatu paket krusial (mis. `openai`) butuh approval manual, gunakan perintah DM bot:
  - `config set UPD_APPROVE_ONCE ["openai"]`
  - `config set UPD_APPROVE_TS <unix_ts>`
  - lalu trigger auto-update yang sudah ada (atau redeploy dengan requirements baru).

Semua patch kompatibilitas (self-heal router, chat neurolite, maintenance manager, learning_progress) tetap aman di versi ini.
