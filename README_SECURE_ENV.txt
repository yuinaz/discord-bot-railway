Secure ENV Setup for SatpamBot
Date: 2025-10-14

1) Buka .gitignore dan tambahkan isi dari .gitignore.append (di patch ini).
2) Salin satpambot_config.local.example.json → satpambot_config.local.json (ISI KUNCI LOKAL, JANGAN COMMIT).
3) Pasang hooks (mencegah commit secrets):
   - Windows:  double-click install_hooks.bat (di root repo)
   - Linux/Mac: bash ./install_hooks.sh
4) Hentikan tracking build lokal (kalau sudah terlanjur):
   git rm -r --cached build && git commit -m "chore: stop tracking build"
5) Verifikasi:
   python -m scripts.smoke_env   (exit 0 kalau semua key ada / setidaknya yang dibutuhkan)

GitHub Actions (tanpa commit rahasia):
  env:
    GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
    GROQ_API_KEY:  ${{ secrets.GROQ_API_KEY }}
    DISCORD_TOKEN: ${{ secrets.DISCORD_TOKEN }}

Render/Server: set ENV di dashboard, bukan di repo.

Jika sempat commit rahasia:
  - git rm --cached file
  - rotate key di provider
  - pertimbangkan rewrite history (git filter-repo)
