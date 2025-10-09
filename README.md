# Self-Learning Neuro Bundle — No-ENV Version (v2)

Semua konfigurasi ada di **`config/self_learning_cfg.py`** (tidak memakai ENV).
Modul yang disertakan:
- `helpers/memory_upsert.py` — upsert + pin MEMORY JSON ke thread neuro.
- `cogs/slang_hourly_miner.py` — mining slang/emoji/phrases (hourly).
- `cogs/phish_text_hourly_miner.py` — intel phishing berbasis teks/URL (hourly).
- `cogs/phash_hourly_scheduler.py` — reconcile/collect pHash per jam.
- `cogs/http_429_backoff.py` — global 429 backoff.
- `cogs/patch_collect_phash_wrapper.py` — batasi panggilan collect_phash.

Ubah nilai-nilai di `self_learning_cfg.py` sesuai kebutuhan servermu.
