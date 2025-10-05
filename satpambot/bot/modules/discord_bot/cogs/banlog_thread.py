from __future__ import annotations

import json
import os

import discord
from discord.ext import commands

from satpambot.bot.modules.discord_bot.helpers.banlog_helper import get_banlog_thread

RECENT_PATH = os.getenv("RECENT_BANS_PATH", "data/recent_bans.json")























def _append_recent_ban(user: discord.abc.User, guild: discord.Guild | None):







    try:







        try:







            data = json.load(open(RECENT_PATH, "r", encoding="utf-8"))







        except Exception:







            data = []







        row = {







            "user_id": str(getattr(user, "id", "-")),







            "user": str(user),







            "guild_id": str(getattr(guild, "id", "-")),







        }







        data = (data + [row])[-100:]







        os.makedirs(os.path.dirname(RECENT_PATH), exist_ok=True)







        json.dump(data, open(RECENT_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=2)







    except Exception:







        pass























class BanLogThread(commands.Cog):







    def __init__(self, bot: commands.Bot):







        self.bot = bot















    @commands.Cog.listener()







    async def on_member_ban(self, guild: discord.Guild, user: discord.User):







        th_or_ch = await get_banlog_thread(guild)







        if not th_or_ch:







            return







        emb = discord.Embed(title="Banned", description=f"{user} (`{getattr(user, 'id', user)}`)")







        try:







            await th_or_ch.send(embed=emb)







            _append_recent_ban(user, guild)







        except Exception:







            pass























async def setup(bot):







    await bot.add_cog(BanLogThread(bot))







