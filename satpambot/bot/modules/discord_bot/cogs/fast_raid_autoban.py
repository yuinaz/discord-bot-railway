from __future__ import annotations

import re, os
from typing import Optional

import discord
from discord.ext import commands

from satpambot.bot.modules.discord_bot.helpers import static_cfg
from satpambot.bot.modules.discord_bot.helpers.lists_loader import load_lists, url_to_host

URL_RE = re.compile(r"(https?://\S+|discord\.gg/\S+|discordapp\.com/invite/\S+)", re.IGNORECASE)

class FastRaidAutoban(commands.Cog):
    """Instant ban for messages containing @everyone + URL (non-whitelist)."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._wl_hosts, self._bl_hosts, self._soft_domains, self._soft_keywords = load_lists()

    def _exempt(self, message: discord.Message) -> bool:
        try:
            ex_roles = set(map(str.lower, getattr(static_cfg, "PHISH_EXEMPT_ROLES", "").split(",")))
            roles = [r.name.lower() for r in getattr(message.author, "roles", []) if getattr(r, "name", None)]
            if ex_roles and any(r in ex_roles for r in roles):
                return True
        except Exception:
            pass
        try:
            ex_channels = set(map(str.lower, getattr(static_cfg, "PHISH_EXEMPT_CHANNELS", "").split(",")))
            if message.channel and getattr(message.channel, "name", None):
                if message.channel.name.lower() in ex_channels:
                    return True
        except Exception:
            pass
        return False

    def _is_soft_allowed(self, content: str, host: str) -> bool:
        c = content.lower()
        if host in self._soft_domains:
            return True
        for kw in self._soft_keywords:
            if kw and kw in c:
                return True
        return False

    async def _ban_author(self, message: discord.Message, reason: str):
        try:
            delete_days = int(os.getenv("PHISH_BAN_DELETE_DAYS", "7"))
        except Exception:
            delete_days = 7
        try:
            await message.guild.ban(message.author, reason=reason, delete_message_days=max(0, min(7, delete_days)))
        except Exception:
            try:
                await message.guild.kick(message.author, reason=reason)
            except Exception:
                pass

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # --- PublicChatGate pre-send guard (auto-injected) ---
        gate = None
        try:
            gate = self.bot.get_cog("PublicChatGate")
        except Exception:
            pass
        try:
            if message.guild and gate and hasattr(gate, "should_allow_public_reply") and not gate.should_allow_public_reply(message):
                return
        except Exception:
            pass
        # --- end guard ---

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
        if message.guild is None or message.author.bot:
            return
        if self._exempt(message):
            return
        if "@everyone" not in message.content:
            return
        m = URL_RE.search(message.content)
        if not m:
            return
        host = url_to_host(m.group(0))

        # Whitelist (exact or suffix match)
        if host in self._wl_hosts or any(host.endswith("." + w) or host == w for w in self._wl_hosts):
            return

        # Soft allow (NSFW soft)
        if self._is_soft_allowed(message.content, host):
            return

        # Hard blacklist hits OR generic mass-mention
        await message.delete()
        await self._ban_author(message, "Mass mention + external URL (non-whitelist)")

async def setup(bot: commands.Bot):
    await bot.add_cog(FastRaidAutoban(bot))