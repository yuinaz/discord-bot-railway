SatpamBot — FULL PATCH (Render Free Plan Safe)
=================================================
Berisi:
- main.py  -> entry untuk 'python main.py' (HTTP /healthz,/uptime, quiet logs, run satpambot.bot)
- scripts/render_entry.py -> alternatif (tidak wajib dipakai)
- patches/hotfix_tile_phash.py + hotfix_elon_casino_tile_phash.json -> blokir varian screenshot scam dg tile pHash
- patches/auto_inject_guard_hooks.py -> injector aman (skip URL cogs), idempotent
- scripts/lint_quick_fix.sh, scripts/lint_strict.sh, ruff.tighten.toml -> opsional lint tools

Cara apply (bash):
  # backup dulu
  cp main.py main.py.bak 2>/dev/null || true

  # copy pack ini ke root repo SatpamBot/ (unzip, timpa file yang sama)
  # start command Render tetap: python main.py (TIDAK DIUBAH)

  # jalankan injector (opsional, jika ingin menambah hook ke cogs)
  python patches/auto_inject_guard_hooks.py

  # smoke (opsional)
  python scripts/smoke_all.py --inject --strict-lint || true

Catatan:
- Patch ini tidak mengubah konfigurasi Render (tetap 'python main.py').
- Hotfix tile pHash ringan (tanpa OCR), cocok untuk free plan.
- Jika sudah ada ruff.toml, file ruff.tighten.toml ini hanya opsional.
- Untuk seed pHash, paste JSON hotfix ke thread referensi imagephishing atau pakai admin command yang tersedia.
