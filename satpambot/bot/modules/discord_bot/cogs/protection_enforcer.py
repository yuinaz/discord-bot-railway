from __future__ import annotations
import types
import logging
from typing import Optional
import contextlib
import discord
from discord.ext import commands

from ..helpers import protect_utils

log = logging.getLogger(__name__)

class ProtectionEnforcer(commands.Cog):
    """
    - Cegah ban sungguhan terhadap moderator/admin/owner/role/IDs ENV (always-preview).
    - Force preview bila pesan dikirim di channel preview/mod-command dari ENV.
    - Lindungi channel preview dari auto-delete (monkey patch Message.delete).
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._patched_delete = False
        self._wrapped = False
        self._orig_delete = None

    @commands.Cog.listener()
    async def on_ready(self):
        if not self._patched_delete:
            ch_id = protect_utils.preview_channel_id_from_env()
            if ch_id:
                try:
                    self._orig_delete = discord.Message.delete
                    async def patched_delete(msg: discord.Message, *a, **k):
                        try:
                            if msg.channel and msg.channel.id == int(ch_id):
                                return  # no-op in preview channel
                        except Exception:
                            pass
                        return await self._orig_delete(msg, *a, **k)
                    discord.Message.delete = patched_delete  # type: ignore
                    self._patched_delete = True
                    log.info("[protection_enforcer] Patched Message.delete for channel %s", ch_id)
                except Exception as e:
                    log.exception("Failed to patch Message.delete: %s", e)

        if not self._wrapped:
            for name in ("PhashAutoBan", "FirstTouchAutoBanPackMime"):
                cog = self.bot.get_cog(name)
                if not cog or not hasattr(cog, "_ban_and_log"):
                    continue
                try:
                    orig = getattr(cog, "_ban_and_log")
                    async def wrapper(self_cog, message, author, reason, cfg, *_a, __orig=orig, __cog=cog):
                        protected = await protect_utils.is_protected_member(author)
                        force_preview = False
                        test_ch_id = protect_utils.preview_channel_id_from_env()
                        try:
                            if test_ch_id and message.channel.id == int(test_ch_id):
                                force_preview = True
                        except Exception:
                            pass
                        dry = False
                        try:
                            dry = bool(cfg.get("dry_run", False))
                        except Exception:
                            pass
                        if protected or force_preview or dry:
                            if hasattr(__cog, "_send_ban_preview"):
                                detail_bits = []
                                if protected: detail_bits.append("PROTECTED")
                                if force_preview: detail_bits.append("TEST-CHANNEL")
                                detail = " • ".join(detail_bits) or "preview"
                                try:
                                    dur = cfg.get("tb_duration","7d") if isinstance(cfg, dict) else "7d"
                                except Exception:
                                    dur = "7d"
                                try:
                                    await __cog._send_ban_preview(message.guild, author, reason, dur, message, detail, cfg)
                                except Exception:
                                    log.exception("preview send failed")
                            do_delete = True
                            try:
                                do_delete = bool(cfg.get("delete_on_hit", True))
                            except Exception:
                                pass
                            if do_delete:
                                with contextlib.suppress(Exception):
                                    await message.delete()
                            return
                        return await __orig(message, author, reason, cfg)
                    setattr(cog, "_ban_and_log", types.MethodType(wrapper, cog))
                    log.info("[protection_enforcer] Wrapped _ban_and_log for %s", name)
                except Exception as e:
                    log.exception("wrap failed for %s: %s", name, e)
            self._wrapped = True

async def setup(bot: commands.Bot):
    await bot.add_cog(ProtectionEnforcer(bot))
