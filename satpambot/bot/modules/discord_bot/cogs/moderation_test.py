from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

import discord
from discord.ext import commands

# Helper ban-log
from satpambot.bot.modules.discord_bot.helpers.banlog_thread import (
    ensure_ban_thread,
    get_log_channel,
)

# Checker izin bawaan proyek
from satpambot.bot.modules.discord_bot.helpers.permissions import is_mod_or_admin


class ModerationTest(commands.Cog):



    """Perintah uji moderasi (embed-only, tanpa aksi nyata)."""







    def __init__(self, bot: commands.Bot):



        self.bot = bot







    @commands.guild_only()



    @commands.check(is_mod_or_admin)



    @commands.command(



        name="testban",



        help="Kirim embed simulasi ban ke channel ini dan mirror ke Ban Log (tanpa aksi nyata).",



    )



    async def testban(



        self,



        ctx: commands.Context,



        member: Optional[discord.Member] = None,



        *,



        reason: str = "kirim link NSFW / phishing",



    ):



        target = member.mention if isinstance(member, discord.Member) else "—"







        # WIB time



        wib = timezone(timedelta(hours=7))



        ts = datetime.now(timezone.utc).astimezone(wib).strftime("%Y-%m-%d %H:%M WIB")







        emb = discord.Embed(



            title="💀 Simulasi Ban oleh SatpamBot",



            description=(



                f"{target} terdeteksi mengirim pesan mencurigakan.\n"



                f"(Pesan ini hanya simulasi untuk pengujian.)\n"



                f"Alasan mencurigakan: {reason}"



            ),



            colour=discord.Colour.red(),



        )



        emb.set_footer(text=f"Simulasi testban • Tidak ada aksi nyata yang dilakukan • {ts}")







        # Kirim ke channel ini



        try:



            await ctx.send(embed=emb)



        except Exception:



            pass







        # Mirror ke Ban Log



        try:



            ch = await get_log_channel(ctx.guild)



            if ch:



                th = await ensure_ban_thread(ch)



                await th.send(embed=emb)



        except Exception:



            pass











async def setup(bot: commands.Bot):



    await bot.add_cog(ModerationTest(bot))



