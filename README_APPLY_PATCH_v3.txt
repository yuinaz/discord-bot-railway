
PATCH v3 (reset + manual bump)
- Command `neuro_progress_reset`: Hapus semua pesan bot di channel/thread berjalan, unpin lama, dan bikin 1 embed progress baru lalu PIN.
  Jalankan command ini DI DALAM thread/channel "neuro-lite progress".
- Command `neuro_bump <stage> <level> <delta>`: Tambah progress secara manual, misal `neuro_bump TK L1 2.5` lalu embed otomatis refresh.
- Command `progress_refresh`: paksa render ulang embed.

Permissions:
  - progress_refresh & neuro_progress_reset: requires Manage Messages
  - neuro_bump: requires Manage Guild
