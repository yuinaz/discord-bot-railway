# -*- coding: utf-8 -*-
"""Hotfix: make Message.delete idempotent/safe.
Swallow NotFound(10008) and Forbidden to avoid noisy ERRORs when multiple cogs delete same message.
"""
import logging
import discord
from discord.ext import commands

log = logging.getLogger(__name__)

def _install_safe_delete_wrapper():
    original_delete = discord.Message.delete
    async def _safe_delete(self: discord.Message, *args, **kwargs):
        try:
            return await original_delete(self, *args, **kwargs)
        except discord.NotFound:
            log.debug("[delete_safe_shim] ignore NotFound (msg_id=%s)", getattr(self, "id", "?"))
            return None
        except discord.Forbidden:
            log.debug("[delete_safe_shim] ignore Forbidden (msg_id=%s)", getattr(self, "id", "?"))
            return None
        except discord.HTTPException as e:
            if getattr(e, "code", None) == 10008:
                log.debug("[delete_safe_shim] ignore HTTP 10008 Unknown Message (msg_id=%s)", getattr(self, "id", "?"))
                return None
            raise
    if getattr(discord.Message.delete, "__name__", "") != "_safe_delete":
        discord.Message.delete = _safe_delete
        log.info("[delete_safe_shim] Message.delete patched to be idempotent/safe.")
    else:
        discord.Message.delete = _safe_delete
        log.info("[delete_safe_shim] Message.delete re-wrapped to ensure safety.")

class DeleteSafeShim(commands.Cog):
    def __init__(self, bot: commands.Bot):
        _install_safe_delete_wrapper()

async def setup(bot: commands.Bot):
    await bot.add_cog(DeleteSafeShim(bot))
