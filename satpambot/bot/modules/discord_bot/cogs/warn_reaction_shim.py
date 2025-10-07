
import os, asyncio, logging
import discord

log = logging.getLogger(__name__)

REACT_OK = os.getenv("REACT_WARN_ENABLE", "false").lower() in ("1","true","yes","on")

_patched = getattr(discord.Message, "_patched_by_warn_shim", False)

if not _patched and not REACT_OK:
    _orig_add = discord.Message.add_reaction
    async def _add_reaction_patched(self, emoji, *args, **kwargs):
        try:
            if str(emoji) in ("⚠️", "⚠"):
                # swallow this reaction silently
                log.debug("[warn_reaction_shim] blocked warn reaction on message id=%s", getattr(self, "id", "?"))
                await asyncio.sleep(0)
                return
        except Exception:
            pass
        return await _orig_add(self, emoji, *args, **kwargs)
    discord.Message.add_reaction = _add_reaction_patched
    discord.Message._patched_by_warn_shim = True
    log.info("[warn_reaction_shim] patch active (REACT_WARN_ENABLE=%s)", REACT_OK)

async def setup(bot):
    # This is a shim-only cog; nothing to add, but presence ensures loader imports us.
    log.info("[warn_reaction_shim] setup() completed")
