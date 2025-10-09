
SHADOW LEARN v4 (silent observer + Groq assist) — no public replies.

Tambahan komponen:
  - satpambot/ml/shadow_metrics.py  -> simpan metrik observasi harian + rollup → progress
  - satpambot/ml/groq_helper.py     -> tanya Groq (OpenAI-compatible) opsional
  - cogs/shadow_learn_observer.py   -> pantau pesan (tanpa reply), update metrik, rollup periodik

Konfigurasi (file JSON via compat_conf):
{
  "SHADOW_LEARN_ENABLED": true,
  "SHADOW_DM_SUMMARY": false,
  "SHADOW_DM_OWNER_ID": 0,
  "PHISH_THREAD_KEYWORDS": "imagephish,phishing,phish-lab",
  "SHADOW_GROQ_WHEN_UNSURE": true,
  "SHADOW_GROQ_SAMPLE_RATE": 0.01,
  "NEURO_SHADOW_METRIC_PATH": "data/neuro-lite/observe_metrics.json",

  "GROQ_API_KEY": "<opsional, biar bisa tanya>",
  "GROQ_BASE_URL": "https://api.groq.com/openai/v1",
  "GROQ_MODEL": "llama-3.1-8b-instant"
}

Cara kerja progress (tanpa chat):
  - Setiap pesan user di guild dihitung 'exposure' (TK.L1)
  - Banyak user unik -> TK.L2
  - Pesan ada gambar -> SD.L1
  - Pesan ada link  -> SD.L2
  - Di thread phish lab -> SD.L3
  - Pertanyaan sampling ke Groq (tanpa reply publik) -> SD.L4
  - Rollup 6 jam sekali, progress 'overall' dihitung otomatis; embed progress akan ikut ter-update oleh cog progress_embed_solo.

Tidak ada balasan publik. Semua diam-diam, hanya DM owner opsional untuk summary.
