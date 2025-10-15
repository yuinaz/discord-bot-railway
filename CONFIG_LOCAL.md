# Konfigurasi Tunggal
Semua konfigurasi ada di **<project_root>/local.json**. File di `satpambot/config/local.json` hanya fallback.
Kunci penting: OWNER_USER_ID, LOG_CHANNEL_ID, PUBLIC_REPORT_CHANNEL_ID, PROGRESS_CHANNEL_ID, PROGRESS_THREAD_NAME, PROGRESS_FILE,
SEARCH_* dan SELFHEAL_DRY_RUN, GROQ_MODEL.

Progress relay akan mengedit pesan keeper lama yang mengandung marker `<!-- [neuro-lite:memory] -->` dan menampilkan XP = xp_total + hour_points.
