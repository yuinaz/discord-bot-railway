# Strict AND + Groq-Assist Patch

- TK 2 level dan SD 6 level tetap berurutan.
- **AND mode**: tiap level butuh *dua-duanya* melewati ambang **slang_ratio** dan **function_ratio**.
- **Groq confirm** (opsional, ON by default): ketika metrik lokal lewat ambang,
  bot sampling chat terbaru (maks 12) dan minta Groq menilai.
  Level baru dihitung `stable` kalau Groq juga setuju (pass rate >= 80%).

Ubah ambang di:
`satpambot/bot/modules/discord_bot/cogs/self_learning_autoprogress.py`

Konstanta penting:
- `REQ_TK`, `REQ_SD` -> target `seen`, `slang`, `func`, dan `stable` per level.
- `GROQ_CONFIRM_ENABLED`, `GROQ_MIN_INTERVAL_MIN`, `GROQ_SAMPLE_N`, `GROQ_PASS_RATE`.

Catatan:
- Ambang 100% + 100% literal tidak realistis untuk bahasa alami. Patch ini menerapkan **ketat** tetapi masuk akal.
- Kalau Groq tidak tersedia, konfirmasi dilewati dan hanya metrik lokal yang dipakai.
