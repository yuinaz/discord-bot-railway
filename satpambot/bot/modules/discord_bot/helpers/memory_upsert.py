import json
import logging
from typing import Any, Dict, Optional

log = logging.getLogger(__name__)

async def upsert_pinned_memory(
    bot,
    payload: Optional[Dict[str, Any]] = None,
    *,
    guild_id: Optional[int] = None,
    channel_id: Optional[int] = None,
    title: str = "XP: Miner Memory",
    max_keep: int = 3,
) -> bool:
    # Back-compat helper for miners:
    # - Accepts positional (bot, payload) like existing calls.
    # - Optional channel fallback via cfg/ENV.
    # - Pins JSON embed and keeps only newest `max_keep` from this bot.
    try:
        # Resolve channel
        if channel_id is None:
            try:
                from satpambot.config.runtime import cfg  # type: ignore
            except Exception:
                cfg = lambda k, d=None: d  # noqa: E731
            channel_id = (
                cfg("PUBLIC_REPORT_CHANNEL_ID")
                or cfg("REPORT_CHANNEL_ID")
                or cfg("SATPAMBOT_LOG_CHANNEL_ID")
                or cfg("LOG_CHANNEL_ID")
            )
        if not channel_id:
            log.warning("memory_upsert: channel_id missing; skip upsert.")
            return False

        # Get channel object
        ch = bot.get_channel(int(channel_id))
        if ch is None:
            ch = await bot.fetch_channel(int(channel_id))

        # Build content
        desc = ""
        embed = None
        try:
            from discord import Embed  # type: ignore
            embed = Embed(title=title)
            if payload is not None:
                txt = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2)
                if len(txt) > 3900:
                    txt = txt[:3900] + "\n... (truncated)"
                desc = f"```json\n{txt}\n```"
            embed.description = desc or "—"
        except Exception:
            # Fallback plain text
            embed = None
            if payload is not None:
                try:
                    desc = json.dumps(payload, ensure_ascii=False)[:1900]
                except Exception:
                    desc = str(payload)[:1900]

        # Send & pin
        msg = await ch.send(embed=embed) if embed else await ch.send(content=desc or title)
        try:
            await msg.pin()
        except Exception:
            pass

        # Keep only recent pins from this bot
        try:
            pins = await ch.pins()
            mine = [m for m in pins if getattr(m.author, "id", None) == getattr(bot.user, "id", None)]
            mine.sort(key=lambda m: getattr(m, "created_at", 0), reverse=True)
            for m in mine[max_keep:]:
                try:
                    await m.unpin()
                except Exception:
                    pass
        except Exception:
            pass

        log.info("memory_upsert: pinned '%s' snapshot to channel %s", title, channel_id)
        return True
    except Exception as e:
        log.exception("memory_upsert failed: %s", e)
        return False
