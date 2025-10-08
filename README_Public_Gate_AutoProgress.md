# Public Chat Gate + Auto-Progress (Indonesian-centric)

## Yang ditambahkan
- **Auto Progress** (tanpa manual command):
  - Observasi chat publik (manusia) → hitung **coverage** slang/func kata Indonesia.
  - Hitung progres **TK** dan **SD** otomatis berdasarkan **rolling average** dan **jumlah sampel**.
  - Stabilitas: butuh beberapa *tick* lulus sebelum 100% supaya tidak premature.
- **Gate 2 Fase (TK→SD)** tetap aktif:
  - Public chat tetap **silent** sampai dua fase 100%.
  - Setelah 100% → bot **DM owner** untuk `!gate unlock` (tetap butuh izin agar aman).
  - **Failsafe**: jika masih terkunci, pesan bot di public akan dihapus.
- **Laporan Harian/Weekly/Monthly** edit-in-place anti-spam.

## File baru
```
satpambot/shared/lingua_id_slang.py
satpambot/shared/progress_gate.py
satpambot/bot/modules/discord_bot/cogs/self_learning_autoprogress.py
satpambot/bot/modules/discord_bot/cogs/public_chat_gate.py
scripts/smoke_autoprogress.py
data/ (dipakai untuk menyimpan state JSON)
```

## Cara pakai
- Pastikan loader cogs Anda **auto-discover** file di folder `cogs/`.
- Jalankan smoke test:
```
python -m scripts.smoke_autoprogress
```
- Tidak perlu `!progress ...`. Progres akan naik sendiri seiring bot mengamati dan memahami bahasa Indonesia (slang & fungsi).

## Siap untuk jenjang lanjut (SMP→S3)
- `ProgressGate` sudah menyiapkan enum untuk SMP/SMA/S1/S2/S3 — tinggal tambahkan kriteria dan modul evaluator lanjutan (mis. klasifikasi niat, emosi, diskursus panjang).
