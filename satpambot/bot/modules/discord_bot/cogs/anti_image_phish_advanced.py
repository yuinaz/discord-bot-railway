from __future__ import annotations

import logging

import discord
from discord.ext import commands

from satpambot.ml.guard_hooks import GuardAdvisor  # auto-injected

log = logging.getLogger(__name__)























class AntiImagePhishAdvanced(commands.Cog):







    def __init__(self, bot: commands.Bot):







        self.bot = bot















    @commands.Cog.listener()







    async def on_message(self, message: discord.Message):







        # auto-injected precheck (global thread exempt + whitelist)







        try:







            _gadv = getattr(self, "_guard_advisor", None)







            if _gadv is None:







                self._guard_advisor = GuardAdvisor(self.bot)







                _gadv = self._guard_advisor







            from inspect import iscoroutinefunction















            if _gadv.is_exempt(message):







                return







            if iscoroutinefunction(_gadv.any_image_whitelisted_async):







                if await _gadv.any_image_whitelisted_async(message):







                    return







        except Exception:







            pass







        # THREAD/FORUM EXEMPTION — auto-inserted







        ch = getattr(message, "channel", None)







        if ch is not None:







            try:







                import discord















                # Exempt true Thread objects







                if isinstance(ch, getattr(discord, "Thread", tuple())):







                    return







                # Exempt thread-like channel types (public/private/news threads)







                ctype = getattr(ch, "type", None)







                if ctype in {







                    getattr(discord.ChannelType, "public_thread", None),







                    getattr(discord.ChannelType, "private_thread", None),







                    getattr(discord.ChannelType, "news_thread", None),







                }:







                    return







            except Exception:







                # If discord import/type checks fail, do not block normal flow







                pass







        # Placeholder: no-op to keep compilation stable







        return























async def setup(bot: commands.Bot):







    await bot.add_cog(AntiImagePhishAdvanced(bot))







