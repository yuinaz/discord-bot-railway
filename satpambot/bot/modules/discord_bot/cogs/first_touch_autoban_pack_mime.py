import re
from typing import Iterable

import discord
from discord.ext import commands

from satpambot.ml.guard_hooks import GuardAdvisor  # auto-injected

PACK_NAME_PATTERN = re.compile(r"^([1-9]\d*)\.(?:jpe?g|png|gif|webp)$", re.IGNORECASE)















# Seconds = 7 days for delete history on ban (Discord supports up to 604800s)







DELETE_HISTORY_SECONDS = 604800























def is_pack_like(attachments: Iterable[discord.Attachment]) -> bool:







    """Return True if attachments look like 1.jpg, 2.jpg, 3.jpg..., regardless of case."""







    names = []







    for a in attachments:







        if not a.filename:







            continue







        m = PACK_NAME_PATTERN.match(a.filename)







        if not m:







            return False







        try:







            idx = int(m.group(1))







        except Exception:







            return False







        names.append(idx)







    if len(names) < 2:







        return False







    names.sort()







    # consecutive starting from 1 or any start is fine; require increasing sequence







    return all(b > a for a, b in zip(names, names[1:]))























def looks_like_webp_masquerade(attachments: Iterable[discord.Attachment]) -> bool:







    """







    Some phishers upload webp but name .jpg







    Discord still exposes content_type.







    If any content_type indicates webp OR filename extension mismatches content_type, flag it.







    """







    for a in attachments:







        ctype = (a.content_type or "").lower()  # e.g. 'image/webp'







        fname = (a.filename or "").lower()







        if "webp" in ctype and not fname.endswith(".webp"):







            return True







        # if file named jpg/png but contains 'webp' hint in size/description (rare); skip here







    return False























class FirstTouchAutoBanPackMime(commands.Cog):







    """Auto-ban users that first-post a pack attachments like 1.jpg..4.jpg, esp. webp-masquerade."""















    def __init__(self, bot: commands.Bot):







        self.bot = bot















    async def _ban_with_history(self, guild: discord.Guild, member_or_user: discord.abc.Snowflake, reason: str):







        # Prefer Member.ban when possible (more consistent audit log)







        try:







            if isinstance(member_or_user, discord.Member):







                await member_or_user.ban(reason=reason, delete_message_seconds=DELETE_HISTORY_SECONDS)







                return







        except TypeError:







            # Older discord.py: no delete_message_seconds on Member.ban; fall back to guild.ban







            pass







        except discord.Forbidden:







            pass















        # Guild.ban fallback with both kwargs for broad compatibility







        try:







            await guild.ban(member_or_user, reason=reason, delete_message_seconds=DELETE_HISTORY_SECONDS)







            return







        except TypeError:







            # Fallback older parameter name







            await guild.ban(member_or_user, reason=reason, delete_message_days=7)















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







        # Skip DMs and bots







        if not message.guild:







            return







        if message.author.bot:







            return







        atts = list(message.attachments or ())







        if not atts:







            return







        if not is_pack_like(atts):







            return







        # If any masquerade detected or simply pack-like, we consider it malicious







        if looks_like_webp_masquerade(atts) or True:







            try:







                reason = "Auto-ban: suspicious pack attachments (possible phishing)."







                await self._ban_with_history(message.guild, message.author, reason=reason)







            except discord.Forbidden:







                # Not enough perms; try delete message as a fallback but don't raise







                try:







                    await message.delete()







                except Exception:







                    pass







            except Exception:







                pass























async def setup(bot: commands.Bot):







    await bot.add_cog(FirstTouchAutoBanPackMime(bot))







