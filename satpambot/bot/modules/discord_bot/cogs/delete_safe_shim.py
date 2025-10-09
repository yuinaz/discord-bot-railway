# -*- coding: utf-8 -*-
"""Hotfix v2: make Message.delete safe + **protect neuro thread messages**.
- Swallow NotFound(10008)/Forbidden.
- If the message is inside thread "neuro-lite progress" OR looks like our keeper
  (NEURO-LITE MEMORY / NEURO-LITE GATE STATUS / key prefix "[neuro-lite:"), ignore deletion.
"""
import logging
import discord
from discord.ext import commands
from satpambot.bot.modules.discord_bot.helpers.thread_utils import DEFAULT_THREAD_NAME

log = logging.getLogger(__name__)

def _in_neuro_thread(msg: discord.Message) -> bool:
    try:
        ch = getattr(msg, "channel", None)
        name = (getattr(ch, "name", "") or "").strip().lower()
        return name == (DEFAULT_THREAD_NAME or "").strip().lower()
    except Exception:
        return False

def _is_keeper(msg: discord.Message) -> bool:
    try:
        c = (getattr(msg, "content", "") or "")
        if not isinstance(c, str):
            return False
        c_low = c.lower()
        return ("neuro-lite memory" in c_low) or ("neuro-lite gate status" in c_low) or ("[neuro-lite:" in c_low)
    except Exception:
        return False

def _install_safe_delete_wrapper():
    original_delete = discord.Message.delete
    async def _safe_delete(self: discord.Message, *args, **kwargs):
        try:
            # PROTECT: neuro thread & keeper messages
            if _in_neuro_thread(self) or _is_keeper(self):
                log.info("[delete_safe_shim] ignore delete for protected message in #%s", getattr(getattr(self, "channel", None), "name", "?"))
                return None
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
        log.info("[delete_safe_shim] Message.delete patched to be idempotent/safe (v2, with neuro protection).")
    else:
        # If already wrapped by older version, re-wrap to ensure our protection applies
        discord.Message.delete = _safe_delete
        log.info("[delete_safe_shim] Message.delete re-wrapped (v2).")

class DeleteSafeShim(commands.Cog):
    def __init__(self, bot: commands.Bot):
        _install_safe_delete_wrapper()

async def setup(bot: commands.Bot):
    await bot.add_cog(DeleteSafeShim(bot))
