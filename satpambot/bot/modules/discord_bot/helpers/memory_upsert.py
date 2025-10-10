import json
import logging
from typing import Any, Dict, Optional

log = logging.getLogger(__name__)

async def upsert_pinned_memory(
    bot,
    *,
    guild_id: Optional[int] = None,
    channel_id: Optional[int] = None,
    title: str = "XP: Miner Memory",
    payload: Optional[Dict[str, Any]] = None,
    max_keep: int = 3,
) -> bool:
    # Send (or upsert) a JSON snapshot to a report channel and pin it.
    # Keeps only the newest `max_keep` pins from this bot.
    # Falls back to LOG_CHANNEL_ID if specific report channel isn't provided.
    try:
        if channel_id is None:
            try:
                from satpambot.config.runtime import cfg
            except Exception:
                cfg = lambda k, d=None: d  # fallback no-op
            channel_id = (
                cfg("PUBLIC_REPORT_CHANNEL_ID")
                or cfg("REPORT_CHANNEL_ID")
                or cfg("SATPAMBOT_LOG_CHANNEL_ID")
                or cfg("LOG_CHANNEL_ID")
            )
        if not channel_id:
            log.warning("memory_upsert: channel_id missing; skip upsert.")
            return False

        # Get channel
        ch = bot.get_channel(int(channel_id))
        if ch is None:
            ch = await bot.fetch_channel(int(channel_id))

        # Prepare embed
        desc = ""
        try:
            from discord import Embed
            embed = Embed(title=title)
            if payload is not None:
                txt = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2)
                if len(txt) > 3900:
                    txt = txt[:3900] + "\n... (truncated)"
                desc = f"```json\n{txt}\n```"
            embed.description = desc or "—"
        except Exception:
            # Discord not available? Fallback to plain text send
            embed = None
            if payload is not None:
                desc = json.dumps(payload, ensure_ascii=False)[:1900]

        msg = await ch.send(embed=embed) if embed else await ch.send(content=desc or title)
        try:
            await msg.pin()
        except Exception:
            pass

        # Keep only `max_keep` newest pins from this bot
        try:
            pins = await ch.pins()
            mine = [m for m in pins if getattr(m.author, "id", None) == getattr(bot.user, "id", None)]
            # sort by created_at desc
            mine.sort(key=lambda m: getattr(m, "created_at", 0), reverse=True)
            for m in mine[max_keep:]:
                try:
                    await m.unpin()
                except Exception:
                    pass
        except Exception:
            pass

        log.info("memory_upsert: pinned %s snapshot to channel %s", title, channel_id)
        return True
    except Exception as e:
        log.exception("memory_upsert failed: %s", e)
        return False
