
# -*- coding: utf-8 -*-
"""
Overlay: Inject dual-mode markers into QnA embeds after they are posted.
Looks for embeds with title starting "Answer by {PROVIDER}" and appends markers:
  footer: "markers: [QNA][PROVIDER:{gemini|groq}][MODE:{primary|fallback}]"
"primary" is when provider equals the first item in QNA_PROVIDER env (default "gemini,groq")
This overlay is *additive* — tidak mengubah cara QnA bekerja, hanya menambah marker.
"""
from __future__ import annotations
import os, logging
from typing import Optional

try:
    import discord  # type: ignore
    from discord.ext import commands  # type: ignore
except Exception:  # pragma: no cover
    discord = None  # type: ignore
    commands = object  # type: ignore

log = logging.getLogger(__name__)

def _provider_order() -> list[str]:
    raw = (os.getenv("QNA_PROVIDER", "gemini,groq") or "gemini,groq").lower()
    order = [p.strip() for p in raw.split(",") if p.strip()]
    return order or ["gemini","groq"]

def _normalize_provider_from_title(title: str) -> Optional[str]:
    # Expected title: "Answer by GEMINI" / "Answer by GROQ"
    t = (title or "").strip().lower()
    if not t.startswith("answer by "): 
        return None
    prov = t.replace("answer by ","").strip()
    if prov.startswith("gemini") or prov.startswith("google"):
        return "gemini"
    if prov.startswith("groq") or prov.startswith("llama") or prov.startswith("mixtral"):
        return "groq"
    return prov or None

def _mode_for(provider: str) -> str:
    order = _provider_order()
    if provider and order and provider == order[0]:
        return "primary"
    return "fallback"

def _mk_markers(provider: str, mode: str) -> str:
    return f"markers: [QNA][PROVIDER:{provider}][MODE:{mode}]"

class QnaDualModeMarkersOverlay(commands.Cog if commands!=object else object):
    def __init__(self, bot=None):
        self.bot = bot

    @getattr(commands, "Cog", object).listener()
    async def on_message(self, message):
        try:
            if not message or not getattr(message, "author", None):
                return
            if not self.bot or message.author.id != getattr(self.bot.user, "id", None):
                return  # only touch messages from this bot
            embeds = getattr(message, "embeds", None) or []
            if not embeds:
                return
            e = embeds[0]
            title = getattr(e, "title", "") or ""
            prov = _normalize_provider_from_title(title)
            if not prov:
                return
            mode = _mode_for(prov)
            markers = _mk_markers(prov, mode)

            # If already marked, skip
            ft = getattr(getattr(e, "footer", None), "text", "") or ""
            if "markers:" in ft and "[QNA]" in ft:
                return

            # Rebuild embed to add footer (discord.Embed is immutable at runtime)
            data = e.to_dict() if hasattr(e, "to_dict") else {}
            data.setdefault("footer", {})
            # Preserve existing footer text if any
            old_footer = (data.get("footer") or {}).get("text") or ""
            new_footer = (old_footer + " | " if old_footer else "") + markers
            data["footer"]["text"] = new_footer

            new_embed = discord.Embed.from_dict(data) if hasattr(discord, "Embed") else e
            await message.edit(embed=new_embed)
            log.info("[qna-markers] injected: %s", markers)
        except Exception as ex:  # pragma: no cover
            try:
                log.warning("[qna-markers] failed to inject markers: %s", ex)
            except Exception:
                pass

def setup(bot):
    try:
        bot.add_cog(QnaDualModeMarkersOverlay(bot)); log.info("✅ Loaded cog (sync): %s", __name__)
    except Exception as e:
        log.exception("Failed to load (sync): %s", e)

async def setup(bot):
    try:
        await bot.add_cog(QnaDualModeMarkersOverlay(bot)); log.info("✅ Loaded cog (async): %s", __name__)
    except Exception as e:
        log.exception("Failed to load (async): %s", e)
