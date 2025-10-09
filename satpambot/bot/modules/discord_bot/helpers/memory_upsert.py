# -*- coding: utf-8 -*-
"""
Memory upserter with Discord 4k content guard.

Drop-in replacement for satpambot.bot.modules.discord_bot.helpers.memory_upsert
so that when the keeper body > 4000 chars, we DON'T fail with
"Invalid Form Body: content must be 4000 or fewer".

Strategy:
- If body <= SOFT_LIMIT -> normal edit on the pinned keeper message.
- Else -> send a new message in the same channel with the FULL body as a .txt attachment,
  then edit the keeper to a short index that points to that message.jump_url.
- Keeps the keeper pinned, the attachment message is not pinned (to avoid clutter).

This module keeps all config IN-CODE (no ENV read), per user's request.
"""

from __future__ import annotations
import io, asyncio, json, hashlib
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import discord

# ---- Tunables (kept in module, NOT env) ----
HARD_LIMIT = 4000           # Discord absolute max
SOFT_LIMIT = 3800           # edit safety margin
ATTACHMENT_FILENAME = "memory_keeper.txt"
KEEPER_TITLE = "🧠 Memory Keeper (pinned)"
INDEX_HEADER = "📌 Memory is larger than 4k, full snapshot is attached below."

# Optional footer to help humans/mods
INDEX_FOOTER = (
    "\n\n— This message stays pinned. The full content is stored in the attached file "
    "message linked above. Auto-delete jobs should ignore this pinned message."
)

# ---- Small helpers ----

def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

def _sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()  # nosec

async def _send_attachment_msg(channel: discord.abc.Messageable, body: str) -> discord.Message:
    data = body.encode("utf-8")
    f = discord.File(io.BytesIO(data), filename=ATTACHMENT_FILENAME)
    head = f"📎 Memory snapshot {_now_iso()} • size={len(data)} bytes"
    return await channel.send(content=head, file=f)

async def _safe_edit_keeper(keeper: discord.Message, body: str) -> None:
    """
    Edit pinned keeper safely. If > SOFT_LIMIT, send attachment message and
    then edit keeper to a compact index that references it.
    """
    if len(body) <= SOFT_LIMIT:
        await keeper.edit(content=body)
        return

    # Overflow path: upload file and index
    attach_msg = await _send_attachment_msg(keeper.channel, body)
    digest = _sha1(body)[:12]
    index = (
        f"{KEEPER_TITLE}\n{INDEX_HEADER}\n"
        f"🧷 Snapshot: {attach_msg.jump_url}\n"
        f"🆔 Digest: `{digest}` • {_now_iso()}"
        f"{INDEX_FOOTER}"
    )
    # Ensure index fits
    if len(index) > HARD_LIMIT:
        # Ultra-compact fallback (shouldn't happen, but guard anyway)
        index = f"{KEEPER_TITLE}\n{attach_msg.jump_url}\nsha1:{digest} • {_now_iso()}"
    await keeper.edit(content=index)

# ---- Public API ----

async def upsert_pinned_memory(bot, payload: Dict[str, Any]) -> bool:
    """
    PUBLIC: called by slang_hourly_miner / phish_text_hourly_miner, etc.
    - Find an existing pinned keeper message (created by neuro_memory_pinner),
      or create one minimally if not found.
    - Render 'payload' into body string (JSON pretty) unless caller already passed 'body'.
    - Smart-edit with 4k guard.

    Returns True if edit/upload succeeded.
    """
    # Locate a keeper message that is pinned & authored by this bot
    user_id = bot.user.id if getattr(bot, "user", None) else None

    async def _find_keeper_in_guilds() -> Optional[discord.Message]:
        # Scan recent pins for messages authored by the bot that look like keeper
        for g in getattr(bot, "guilds", []):
            try:
                for ch in g.text_channels:
                    try:
                        pins = await ch.pins()
                    except Exception:
                        continue
                    for m in pins:
                        if user_id and m.author.id != user_id:
                            continue
                        # Heuristic: either has our title line or looks like previous keeper
                        txt = (m.content or "")
                        if "Memory Keeper" in txt or "memory keeper" in txt or "satpambot:auto_prune_state" in txt or "neuro-lite progress" in txt.lower():
                            return m
            except Exception:
                continue
        return None

    keeper: Optional[discord.Message] = await _find_keeper_in_guilds()
    if keeper is None:
        # As last resort, try to use the first text channel we can write to and create a keeper.
        # We keep content tiny so it won't clash with auto-delete rules.
        target = None
        for g in getattr(bot, "guilds", []):
            for ch in g.text_channels:
                perms = ch.permissions_for(g.me) if getattr(g, "me", None) else None
                if perms and perms.send_messages and perms.read_message_history:
                    target = ch
                    break
            if target:
                break
        if target is None:
            # Can't locate a writable channel in smoke mode or limited context.
            return False
        keeper = await target.send(f"{KEEPER_TITLE}\nInitialized {_now_iso()}")
        try:
            await keeper.pin()
        except Exception:
            pass  # ignore if cannot pin in this context

    # Render body
    if "body" in payload and isinstance(payload["body"], str):
        body = payload["body"]
    else:
        # Pretty JSON plus lightweight header
        pretty = json.dumps(payload, ensure_ascii=False, indent=2)
        digest = _sha1(pretty)[:12]
        body = f"{KEEPER_TITLE}\nsha1:{digest} • {_now_iso()}\n\n```json\n{pretty}\n```"

    try:
        await _safe_edit_keeper(keeper, body)
        return True
    except discord.HTTPException as e:
        # If we still hit a 400/429, do a final compact write to avoid task crash
        compact = f"{KEEPER_TITLE}\n(Compact mode) {_now_iso()}\nlen={len(body)}"
        try:
            await keeper.edit(content=compact[:HARD_LIMIT])
            return True
        except Exception:
            raise e
