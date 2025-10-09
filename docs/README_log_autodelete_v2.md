# Log Auto Delete v2

Tujuan: bersihkan spam di `#log-botphising` tanpa menyentuh thread **neuro-lite progress**.

Default:
- TTL 15 menit untuk pesan bot (tidak pinned) di channel log.
- Jaga **satu** pesan terbaru per judul (mis. hanya 1 'Periodic Status', 1 'Proposal', dst).

ENV:
- `LOG_AUTODELETE_TTL_SECONDS=900`  → ubah TTL (detik).
- `LOG_AUTODELETE_CHANNEL_ID=<id>` → kalau tidak diset, pakai `LOG_CHANNEL_ID`.
- `LOG_AUTODELETE_PATTERNS=Proposal:,Periodic Status,Maintenance` → hanya hapus jika judul/konten mengandung salah satu pola. Kosongkan untuk hapus semua pesan bot.
- `LOG_AUTODELETE_KEEP_LATEST_PER_TITLE=1` → simpan yang terbaru, hapus duplikat sebelumnya.

Catatan: integrasi dengan `delete_safe_shim` melalui `allow_delete_for()` agar penghapusan tidak diblok.
