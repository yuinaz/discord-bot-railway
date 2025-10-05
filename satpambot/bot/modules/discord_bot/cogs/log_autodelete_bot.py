import asyncio

import discord
from discord.ext import commands

from satpambot.ml.guard_hooks import GuardAdvisor  # auto-injected

AUTO_DELETE_TTL_SECONDS = 300  # 5 minutes (edit as needed)



# Channels/threads to watch. Names are case-insensitive.



LOG_CHANNEL_NAMES = {"log-botphising"}



THREAD_NAMES = {"imagephising"}







KEEP_MARKERS = ("[KEEP]", "SATPAMBOT_PHASH_DB_V1")











def _is_keep_message(message: discord.Message) -> bool:



    content = (message.content or "").lower()



    for marker in KEEP_MARKERS:



        if marker.lower() in content:



            return True



    # Never auto delete pinned messages



    if getattr(message, "pinned", False):



        return True



    return False











def _is_log_scope(channel: discord.abc.GuildChannel) -> bool:



    # In scope if channel name is in LOG_CHANNEL_NAMES,



    # or if it's a thread whose parent is a log channel,



    # or if thread name matches THREAD_NAMES explicitly.



    try:



        name = (channel.name or "").lower()



    except AttributeError:



        name = ""



    if name in {n.lower() for n in LOG_CHANNEL_NAMES}:



        return True



    if isinstance(channel, discord.Thread):



        tname = (channel.name or "").lower()



        if tname in {n.lower() for n in THREAD_NAMES}:



            return True



        parent = channel.parent



        if parent and (parent.name or "").lower() in {n.lower() for n in LOG_CHANNEL_NAMES}:



            return True



    return False











class LogAutoDeleteBot(commands.Cog):



    """Auto-deletes the bot's own transient log/status messages in log channels/threads."""







    def __init__(self, bot: commands.Bot):



        self.bot = bot







    async def _delete_later(self, message: discord.Message, delay: int):



        try:



            await asyncio.sleep(delay)



            if _is_keep_message(message):



                return



            await message.delete()



        except (discord.NotFound, discord.Forbidden):



            # Message gone or lacking perms; nothing to do



            return



        except Exception:



            return







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



        # Only consider the bot's own messages



        if message.author.id != self.bot.user.id:



            return



        channel = message.channel



        if not _is_log_scope(channel):



            return



        if _is_keep_message(message):



            return



        # schedule delete later



        self.bot.loop.create_task(self._delete_later(message, AUTO_DELETE_TTL_SECONDS))











async def setup(bot: commands.Bot):



    await bot.add_cog(LogAutoDeleteBot(bot))



