from __future__ import annotations

import asyncio
import os

import discord
from discord.ext import commands

from satpambot.ml.guard_hooks import GuardAdvisor  # auto-injected

TTL = int(os.getenv("TEMP_DISMISS_TTL_SEC", "60") or 60)



LOG_CH_ID = os.getenv("LOG_CHANNEL_ID", "").strip()



LOG_CH_NAME = os.getenv("LOG_CHANNEL_NAME", "log-botphising").strip() or "log-botphising"



TARGET_TITLES = {"Lists updated", "Phish image registered"}











class TempDismissLog(commands.Cog):



    def __init__(self, bot):



        self.bot = bot







    def _is_target(self, msg: discord.Message) -> bool:



        ch = getattr(msg, "channel", None)



        if ch is None:



            return False



        ok_ch = (LOG_CH_ID.isdigit() and str(getattr(ch, "id", "")) == LOG_CH_ID) or (



            getattr(ch, "name", "") == LOG_CH_NAME



        )



        if not ok_ch:



            return False



        if not msg.author or not msg.author.bot:



            return False



        titles = [e.title for e in (msg.embeds or []) if isinstance(e, discord.Embed) and e.title]



        return any(t in TARGET_TITLES for t in titles)







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



        if self._is_target(message):



            await asyncio.sleep(TTL)



            try:



                await message.delete()



            except Exception:



                pass











async def setup(bot: commands.Bot):



    await bot.add_cog(TempDismissLog(bot))



