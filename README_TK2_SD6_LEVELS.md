# Multi-level TK(2) + SD(6) Gate Patch

## Aturan
- **TK** punya 2 level: L1 → L2. Keduanya harus 100% dulu.
- Setelah TK selesai, lanjut **SD** 6 level: L1 → L6. Enam-enamnya 100%.
- Baru setelah SD lengkap, bot **DM owner** untuk `!gate unlock`.
- Boot selalu mulai **LOCK** (shadow-mode).

## Otomatisasi
- `self_learning_autoprogress.py` observasi chat Indonesia lalu
  meluluskan level secara **berurutan** berdasarkan:
  - jumlah sampel (seen),
  - rata-rata coverage (slang+fungsi),
  - stabilitas beberapa tick.

## File yang ditimpa
```
satpambot/shared/progress_gate.py
satpambot/bot/modules/discord_bot/cogs/self_learning_autoprogress.py
satpambot/bot/modules/discord_bot/cogs/public_chat_gate.py
```

## Cek cepat
- Lihat `data/progress_gate.json` → akan ada `tk_levels` dan `sd_levels`.
- Status ringkas muncul di report harian/weekly/monthly dan `!gate status` (jika ada).

## Konfigurasi
Threshold per level ada di `self_learning_autoprogress.py`:
```
REQ_TK = [{seen, cov, stable}, ...]
REQ_SD = [{seen, cov, stable}, ...]
```
Ubah sewaktu-waktu sesuai kebutuhan.