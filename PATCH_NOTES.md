# Patch: hourly miners smoke-safe + memory-safe

This patch replaces two cogs:
- `slang_hourly_miner.py`
- `phish_text_hourly_miner.py`

Key fixes:
1) **async setup(bot)** so smoke tools that `await setup()` won't error.
2) **sync `cog_load`** (no `async def`) so smoke doesn't complain about "coroutine was never awaited".
3) Start loops on **on_ready** with jitter, not during import.
4) Use `upsert_pinned_memory(bot, payload)` for writes. Body size is handled by your patched `memory_upsert.py` (attachment fallback for >4k).
5) Never delete any messages or pinned items.

Drop these files into:
`satpambot/bot/modules/discord_bot/cogs/`

Then:
```
git add -A
git commit -m "fix(cogs): hourly miners async setup + safe memory upsert"
```
