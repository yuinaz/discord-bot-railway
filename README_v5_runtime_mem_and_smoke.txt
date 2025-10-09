
PATCH v5 — Runtime memory config + hardened smoke + CF/Groq guards

✓ Pusat ENV di memory bot: satpambot/config/runtime_memory.py
  - get/set/dump, bisa persist kembali ke satpambot_config.local.json
  - tetap hormati compat_conf (file-first) sebagai fallback

✓ SMOKE_MODE: set `SMOKE_MODE=true` di environment/JSON agar semua loop background tidak jalan saat smoke tests.

✓ Fix SyntaxError pada smoke_utils (hilangkan literal '\n' yang nyangkut) dan satukan API DummyBot.

✓ scripts/smoketest_all.py & scripts/smoke_deep.py:
  - compileall + import check
  - async setup cogs pakai DummyBot
  - fail-fast jika ada import yang benar-benar rusak

✓ rl_shim_history & log_autodelete_bot:
  - tahan 403/Cloudflare/Forbidden agar task tidak crash (swallow & continue)

✓ groq_helper:
  - backoff 1 jam jika 403 (disable sementara agar tidak spam log)
  - bisa matikan konsultasi di Render: set `ALLOW_GROQ_ON_RENDER=false`

Cara pakai smoke:
  $ python scripts/smoketest_all.py
  $ python scripts/smoke_deep.py
