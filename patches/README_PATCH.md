# SatpamBot Render-Safe Self-Learning Boost Patch (ZIP)
Tujuan: menaikkan XP **lebih cepat** namun **aman** untuk Render Free (~80–85% batas), plus perbaikan kompatibilitas `upsert_pinned_memory` dan opsi Vision (pengganti Groq yang tidak punya vision).

## Isi patch
- `cogs/a01_learning_passive_overlay.py` — overlay untuk **learning_passive_observer** (window, cap, delta, XP weights, burst).
- `cogs/a02_miner_accel_overlay.py` — overlay untuk **text/slang/phish miners** (period, per_channel, total_budget, skip_mod) + throttle ringan.
- `cogs/a26_memory_upsert_compat_overlay.py` — wrapper kompatibilitas untuk panggilan `upsert_pinned_memory` (signature baru/lama).
- `helpers/memory_upsert_compat.py` — util kompat untuk dipakai langsung bila perlu.
- `cogs/temp_dismiss_log.py` — stub agar import error pada cog itu **tidak** bikin seluruh bot gagal load.
- `ml/vision_router.py` — router Vision: **gemini** (disarankan), **openai**, atau **none**, sebagai alternatif Groq.
- `scripts/smoke_*.py` — smoke test kecil.
- `configs/satpambot_config.local.json.example.render_boost.json` — **profil Render-Safe** (tinggal merge ke `satpambot_config.local.json`).

## Cara pasang (root repo)
1. Ekstrak ZIP ke root project (struktur folder `satpambot/...`, `scripts/...`, `configs/...` harus tersusun).
2. Merge contoh konfigurasi:
   - Buka `configs/satpambot_config.local.json.example.render_boost.json`,
   - Gabungkan isinya ke `satpambot_config.local.json` milikmu (atau salin blok yang belum ada).
3. (Opsional) pasang dependensi vision jika dipakai:
   - Gemini: `pip install google-generativeai`
   - OpenAI v1: `pip install openai>=1.0.0`
4. Jalankan smoke test:
   ```bash
   python -m scripts.smoke_learn_fast
   python -m scripts.smoke_miner_accel
   python -m scripts.smoke_vision_router
   ```
5. Jalankan bot. Pantau CPU & log. Kalau CPU > 85% stabil >3 menit, naikkan `period` miners + turunkan `total_budget` sedikit.

> Patch ini **tidak menghapus** apapun; sifatnya overlay/komplemen. Aman dipakai di Render free.
