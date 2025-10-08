
# Warn Reaction Blocker (Total)
Menghapus total reaction peringatan ⚠️/⚠ di seluruh channel & DM.

## Pasang
1) Salin file ke repo:
   - `satpambot/bot/modules/discord_bot/cogs/warn_reaction_blocker.py`
   - `scripts/smoke_warn_blocker.py`
2) (Opsional) Test:
   ```bash
   python scripts/smoke_warn_blocker.py
   # output: [OK] import: satpambot.bot.modules.discord_bot.cogs.warn_reaction_blocker
   ```
3) Restart bot.

## Lingkungan (opsional)
- `WARN_REACTION_BLOCKLIST` default: `⚠️,⚠`
- `WARN_REACTION_REMOVE_DELAY_S` default: `0.0`

Catatan: untuk menghapus reaction milik orang lain, bot perlu permission
**Manage Messages** di channel tersebut. Tanpa itu, bot tetap tidak akan
menambahkan ⚠️ sama sekali (karena dipotong di sumbernya).
