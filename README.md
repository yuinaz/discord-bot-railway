# SatpamBot — Patch Latest for Render Free

Isi patch ini:
- `requirements.latest.txt` — versi terbaru yang aman untuk Render.
- `scripts/build_render.sh` — sekarang baca file requirement lewat env `REQUIREMENTS_FILE`.
- `scripts/smoke_env.py` — tambah cek kompatibilitas (OpenCV↔NumPy, httpx↔googletrans, tzdata).
- `scripts/use_latest.sh` — helper buat install latest + smoke lokal (Git Bash).

## Cara pakai (Render)
1. Tambah env var di service Render:
   - `REQUIREMENTS_FILE=requirements.latest.txt`
2. Deploy seperti biasa (Start Command tetap `python main.py`).

## Cara pakai (Lokal)
```bash
# dari root repo kamu
cp requirements.latest.txt ./
cp scripts/build_render.sh ./scripts/
cp scripts/smoke_env.py ./scripts/
cp scripts/use_latest.sh ./scripts/
bash scripts/use_latest.sh
```

## Catatan kompatibilitas
- OpenCV 4.12.x masih butuh NumPy `< 2.3`. Pip akan memilih NumPy 2.2.x otomatis.
- Bila pakai googletrans lama, pastikan forknya mendukung httpx 0.28.x (disarankan `googletrans-py`).
- Untuk timezone `Asia/Jakarta` di Windows, pastikan `tzdata` terinstall.
