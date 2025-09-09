
# -*- coding: utf-8 -*-
from __future__ import annotations

import datetime as _dt
from typing import List, Tuple, Optional
import discord
from discord.ext import commands

WIB_OFFSET = _dt.timedelta(hours=7)
def _fmt_wib(dt: Optional[_dt.datetime] = None) -> str:
    if dt is None:
        dt = _dt.datetime.utcnow().replace(tzinfo=_dt.timezone.utc) + WIB_OFFSET
    return dt.strftime("%Y-%m-%d %H:%M:%S") + " WIB"

def _exists(bot: commands.Bot, name: str) -> bool:
    return bot.get_command(name) is not None

def _first_existing(bot: commands.Bot, names: List[str]) -> Optional[str]:
    for n in names:
        if _exists(bot, n):
            return n
    return None

USAGE = {
    "tb": {
        "title": "💀 Simulasi Ban — `!tb`",
        "desc": "Simulasi tanpa aksi nyata. Bisa **reply** ke pesan lalu ketik `!tb [alasan?]`, "
                "atau `!tb @user [alasan]`. Hasil embed menampilkan **Lokasi**, **Alasan**, dan timestamp **WIB**.",
        "examples": [
            "`!tb` (sambil reply pesan)",
            "`!tb @Frisca spam link phish`",
            "`!tb alasan uji`",
        ],
    },
    "ban": {
        "title": "🔨 Ban — `!ban`",
        "desc": "Ban permanen. Bot membutuhkan permission ban pada server & channel ini.",
        "examples": [
            "`!ban @Frisca promosi phising`",
        ],
    },
    "tban": {
        "title": "⏳ Temp Ban — `!tban` / `!tempban`",
        "desc": "Ban sementara dengan durasi. Format: angka + satuan (`m`, `h`, `d`).",
        "examples": [
            "`!tban @Frisca 5m spam`",
            "`!tempban @Frisca 2h iklan`",
        ],
    },
}

class HelpBasic(commands.Cog):
    """Help prefix sederhana (drop-in). Tidak mengubah config."""
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="help", aliases=["h"])
    async def help_cmd(self, ctx: commands.Context, *, subject: str = ""):
        subject = subject.strip().lower()
        if subject in ("tb", "ban", "tban", "tempban"):
            key = subject if subject != "tempban" else "tban"
            await self._send_detail(ctx, key)
            return

        # Ringkasan: tampilkan perintah yang tersedia di runtime
        available: List[Tuple[str,str]] = []
        for key, data in USAGE.items():
            if key == "tban":
                ok = _first_existing(self.bot, ["tban", "tempban"])
            else:
                ok = _first_existing(self.bot, [key])
            if ok:
                available.append((key, data["title"]))

        embed = discord.Embed(title="📖 Bantuan — Prefix Commands", colour=discord.Colour.green())
        if available:
            for key, title in available:
                usage = USAGE[key]
                ex1 = usage["examples"][0]
                embed.add_field(name=title, value=f"{usage['desc']}\nContoh: {ex1}", inline=False)
        else:
            embed.description = "Tidak ada perintah prefix yang aktif."
        embed.set_footer(text="SatpamBot Help • " + _fmt_wib())
        await ctx.reply(embed=embed)

    async def _send_detail(self, ctx: commands.Context, key: str):
        usage = USAGE[key]
        embed = discord.Embed(title=usage["title"], description=usage["desc"], colour=discord.Colour.blurple())
        embed.add_field(name="Contoh", value="\n".join(usage["examples"]), inline=False)
        embed.set_footer(text="SatpamBot Help • " + _fmt_wib())
        await ctx.reply(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(HelpBasic(bot))
