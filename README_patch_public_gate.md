
# Public Mode Gate Patch (DM-only toggle + auto-nudge + progress reports)

**Ringkas:** 
- Bot **diam total** di publik sampai progress & akurasi shadow-mode = `PUBLIC_MIN_PROGRESS` (default **100%**).
- Owner bisa toggle via **DM**: `!public on|off|status` (hanya aktif kalau progress >= ambang).
- Bot akan **DM owner otomatis** saat ambang tercapai untuk minta izin membuka publik.
- Laporan **daily/weekly/monthly** otomatis dikirim via DM ke owner.

## File baru
- `satpambot/bot/modules/discord_bot/helpers/progress_gate.py`
- `satpambot/bot/modules/discord_bot/cogs/public_mode_gate.py`
- `satpambot/bot/modules/discord_bot/cogs/learning_progress_reporter.py`
- `scripts/smoke_public_gate.py`

## ENV (opsional, default aman)
- `DISCORD_OWNER_IDS` : daftar user id owner, koma/semicolon separated.
- `PUBLIC_MIN_PROGRESS` : ambang progress & akurasi (0.0..1.0). Default `1.0` (100%).
- `SILENT_PUBLIC` : default `1` (blok publik). Saat `!public on`, runtime akan override tanpa restart.
- `PROGRESS_JSON` : path sumber progress (jika modul learning belum expose fungsi).
- `PROGRESS_VALUE` : override progress cepat untuk testing (0..1).
- `BOT_TZ` : default `Asia/Jakarta`.

## Integrasi dengan chat module
Di modul yang melakukan reply publik (contoh `chat_neurolite.py`), sebelum mengirim balasan di **guild** tambahkan:

```py
from satpambot.bot.modules.discord_bot.helpers import progress_gate as gate
if message.guild and not gate.is_public_allowed():
    return  # tetap DM jalan, publik diam total
```

## Install cepat
```
python -m pip install -r requirements.latest.txt
python scripts/smoke_public_gate.py
```

Kalau semua `[OK]`, deploy. Di DM ke bot: `!public status` / `!public on` setelah ambang tercapai.
