# Neuro-Lite Memory Autoclean v4

Tujuan:
- Memastikan 1 pesan **tetap** dipakai untuk memory (edit-in-place + pin).
- Menghindari numpuk pesan setiap restart.

Komponen:
- `cogs/neuro_memory_pinner.py` v4: 
  - Cari pesan keeper lama (pinned/history) berbasis marker, lalu **edit** di tempat.
  - Kalau tidak ada, buat baru (keeper/fallback) lalu pin.
  - Bersihkan duplikat: **unpin**, dan **opsional hapus** (lihat ENV).
- `cogs/delete_safe_shim.py` v3: 
  - Melindungi pesan di thread `neuro-lite progress` dari penghapusan agresif.
  - **Allowlist** untuk penghapusan terkontrol via fungsi `allow_delete_for(msg_id)`.

ENV opsional:
- `NEURO_MEMORY_SEND_FALLBACK=1` (default ON)
- `NEURO_MEMORY_CLEANUP_DELETE=1` → selain unpin, duplikat juga dihapus (aman melalui allowlist).

Cara pakai:
1. Timpa file di repo sesuai path dalam ZIP.
2. Pastikan kedua cog dimuat.
3. Restart bot.
