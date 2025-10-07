
# Sinkronisasi PC Utama Dengan GitHub (sama seperti repo lokal)

**A. Kalau belum ada folder repo di PC utama:**
```bash
git clone https://github.com/<ORG>/<REPO>.git
cd <REPO>
# Tarik patch terbaru
git fetch origin
git checkout main
git reset --hard origin/main
```

**B. Kalau sudah ada folder repo, tapi mau samakan ke GitHub `main`:**
> Hati‑hati: ini akan menghapus perubahan lokal yang belum dipush.
```bash
cd <REPO>
git remote -v               # pastikan remote `origin` benar
git fetch --all --prune
git checkout main
git reset --hard origin/main
git clean -fdx              # bersihkan file yang tidak dilacak (opsional)
```

**C. Lindungi file lokal sensitif agar tidak ikut commit:**
Tambahkan ke `.gitignore` (atau pastikan sudah ada):
```
satpambot_config.local.json
secrets/
SatpamBot.env
```

**D. Update cepat dari Git:**
```bash
git pull --ff-only origin main
```

> Bila pakai Windows, jalankan perintah di **Git Bash** atau PowerShell (dengan Git).
