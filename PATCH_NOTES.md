# Patch: Fix "Invalid Form Body (content > 4000)" + reduce 429 collisions

This zip contains **drop-in** files. You asked to keep config in modules (no ENV), so all knobs are constants inside the files.

## What it fixes

1. **4000-char hard limit** when updating the pinned memory keeper:
   - If the keeper body > 4000, we now upload the **full text as a .txt attachment**,
     then **edit the pinned keeper** to a small index that points to that attachment.
   - The pinned keeper stays small and safe; the heavy content lives in the attachment message.
   - The index includes a short digest and timestamp.

2. **429 bursts** on hourly jobs (slang/phish miners) starting at the same time:
   - Optional patches add a **random start jitter** so the two loops don't collide on the same minute.

## Files

- `satpambot/bot/modules/discord_bot/helpers/memory_upsert.py`
  - **REQUIRED**: replace your existing file with this one.
  - Public API kept: `async def upsert_pinned_memory(bot, payload) -> bool`.
  - No ENV used.

- `satpambot/bot/modules/discord_bot/cogs/slang_hourly_miner.py` (optional)
  - Shows how to add jitter and calls the new safe upserter.
  - If you don't want to replace your cog, at least ensure your cog **imports** and **uses**
    `upsert_pinned_memory` from the new helper so it never calls `keeper.edit(content=...)` directly.

- `satpambot/bot/modules/discord_bot/cogs/phish_text_hourly_miner.py` (optional)
  - Same jitter idea so both hourly loops don't begin at the exact same second.

## How to apply

1. **Stop your bot**.
2. Extract this zip at repo root; it will create the same folder structure under `satpambot/...`.
3. Copy/overwrite the files into your project.
4. Commit the changes:
   ```bash
   git add -A
   git commit -m "fix(memory): guard 4k limit by attaching overflow; add jitter to hourly miners"
   ```
5. Start your bot again and watch logs. You should see the keeper updated even when payloads are big.
   The channel will receive a **separate message with a .txt attachment** when needed; the pinned keeper
   will contain a compact pointer and digest.

### Notes

- We keep the **keeper pinned only**. The attachment message is not pinned (to avoid clutter). If you want it pinned, you can pin it in `_send_attachment_msg` after sending.
- The index text stays well below 4k. If for any reason it goes above, an ultra-compact fallback kicks in.
- This module **intentionally** keeps all knobs in code (no ENV), per your instruction.
