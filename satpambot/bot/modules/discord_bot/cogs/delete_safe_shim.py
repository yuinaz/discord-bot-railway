# -*- coding: utf-8 -*-
"""Hotfix: make Message.delete idempotent/safe.

This cog wraps discord.Message.delete so that concurrent deletions (HTTP 10008 / NotFound)
are treated as a no-op instead of bubbling an error. It also soft-ignores Forbidden in
channels where the bot lacks perms.

Drop this file into: satpambot/bot/modules/discord_bot/cogs/delete_safe_shim.py
It uses the standard 2.0+ `setup` entrypoint so your cogs_loader should pick it up.
"""
import logging
import discord
from discord.ext import commands

log = logging.getLogger(__name__)

def _install_safe_delete_wrapper():
    # Keep whatever is currently installed (possibly already patched by other cogs)
    original_delete = discord.Message.delete

    async def _safe_delete(self: discord.Message, *args, **kwargs):
        try:
            return await original_delete(self, *args, **kwargs)
        except discord.NotFound:
            # Another cog/moderator removed it first — that's fine.
            log.debug("[delete_safe_shim] ignore NotFound (msg_id=%s, ch_id=%s)", getattr(self, "id", "?"), getattr(getattr(self, "channel", None), "id", "?"))
            return None
        except discord.Forbidden:
            # No permission to delete here — don't spam errors.
            log.debug("[delete_safe_shim] ignore Forbidden (msg_id=%s, ch_id=%s)", getattr(self, "id", "?"), getattr(getattr(self, "channel", None), "id", "?"))
            return None
        except discord.HTTPException as e:
            # 10008 is Unknown Message — treat it as already deleted.
            if getattr(e, "code", None) == 10008:
                log.debug("[delete_safe_shim] ignore HTTP 10008 Unknown Message (msg_id=%s)", getattr(self, "id", "?"))
                return None
            raise

    # Install our wrapper only once
    if getattr(discord.Message.delete, "__name__", "") != "_safe_delete":
        discord.Message.delete = _safe_delete
        log.info("[delete_safe_shim] Message.delete patched to be idempotent/safe.")
    else:
        # Already wrapped by someone using the same name — still re-wrap to ensure safety.
        discord.Message.delete = _safe_delete
        log.info("[delete_safe_shim] Message.delete re-wrapped to ensure safety.")

class DeleteSafeShim(commands.Cog):
    def __init__(self, bot: commands.Bot):
        _install_safe_delete_wrapper()

async def setup(bot: commands.Bot):
    await bot.add_cog(DeleteSafeShim(bot))
