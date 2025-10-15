# Shadow Public Silencer — Hotfix v3

Perbaikan:
- Ganti `bot.loop.create_task(...)` → `asyncio.create_task(...)` di `cog_load()` (aman di DummyBot/discord.py 2.x).
- Patch `Messageable.send` sekali, amankan DM & thread **neuro-lite progress**.
- Whitelist channel ID via ENV (otomatis menyertakan `LOG_CHANNEL_ID`).

ENV:
- `SHADOW_PUBLIC_FORCE=1` → izinkan public (default 0 = blok).
- `SHADOW_PUBLIC_WHITELIST_IDS=123,456` → ID channel tambahan yang diizinkan.

Pasang:
1) Timpa `satpambot/bot/modules/discord_bot/cogs/shadow_public_silencer.py`.
2) Pull & restart bot.
