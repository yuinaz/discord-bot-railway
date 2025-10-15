# Patch: await `bot.add_cog(...)` in hourly miners

## Why
You saw warnings like:
```
RuntimeWarning: coroutine 'BotBase.add_cog' was never awaited
```
from:
- `cogs/phish_text_hourly_miner.py` (line ~144)
- `cogs/slang_hourly_miner.py` (line ~142)

In discord.py≥2.x `Bot.add_cog` is **async** when your cog defines `cog_load` or other async hooks. So `setup(bot)` must be `async` **and** call `await bot.add_cog(...)`.

## What this patch does
The included `quick_patcher.py` will, in-place, update both files to:
```py
async def setup(bot):
    await bot.add_cog(YourCog(bot))
```
It preserves everything else.

## How to apply
From your repo root (same level as `satpambot/`):

```bash
python quick_patcher.py
# optional: verify
python verify_snippet.py
# then test
python scripts/smoke_deep.py
```

## Files
- `quick_patcher.py` – edits the two target files safely.
- `verify_snippet.py` – prints whether the awaited add_cog is present.
