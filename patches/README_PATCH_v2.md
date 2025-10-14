# SatpamBot Render-Safe Self-Learning Boost Patch (v2)
Tambahan v2:
- **a00_overlay_bootstrap.py**: memastikan overlay ter-load lebih awal (termasuk untuk smoke test).
- **a03_tts_guard_overlay.py**: cegah crash `tts_voice_reply` di Render (TTS dimatikan default).
- **scripts/smoke_*.py** diperbarui untuk meng-import bootstrap lebih dulu.
- **scripts/merge_local_json.py**: merge otomatis konfigurasi Render-Safe ke `satpambot_config.local.json`.

Langkah cepat:
1) Ekstrak ZIP di root repo.
2) Jalankan:
   ```bash
   python -m scripts.merge_local_json configs/satpambot_config.local.json.example.render_boost.json
   python -m scripts.smoke_learn_fast
   python -m scripts.smoke_miner_accel
   python -m scripts.smoke_vision_router
   ```
3) Start bot. Jika CPU stabil >85% beberapa menit, naikkan `*_PERIOD_SEC` atau turunkan `MINER_TOTAL_BUDGET`.
