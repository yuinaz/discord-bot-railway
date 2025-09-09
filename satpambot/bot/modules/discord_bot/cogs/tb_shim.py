from __future__ import annotations

import datetime as _dt
from typing import Optional

import discord
from discord.ext import commands

WIB = _dt.timezone(_dt.timedelta(hours=7))

def _wib_now_str() -> str:
    return _dt.datetime.now(WIB).strftime("%Y-%m-%d %H:%M:%S WIB")

def _resolve_target(ctx: commands.Context) -> Optional[discord.abc.User]:
    """Try to find a target for simulation:
    - If command is a reply -> author of the referenced message
    - Else first mentioned user/member
    - Else None (still allowed)"""
    # reply target
    ref = ctx.message.reference
    if ref and isinstance(ref.resolved, discord.Message) and ref.resolved.author:
        return ref.resolved.author

    # mention target
    if ctx.message.mentions:
        return ctx.message.mentions[0]

    return None

class TBShimFormatted(commands.Cog):
    """Single-source `!tb` simulation. Always responds with a clean embed (no errors)."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="tb", aliases=["testban"], help="Simulasi ban (tidak ada aksi nyata).")
    async def tb(self, ctx: commands.Context, *, reason: str = "") -> None:
        target = _resolve_target(ctx)
        location = f"#{ctx.channel.name} • {ctx.guild.name}" if ctx.guild and ctx.channel else "DM/Unknown"
        alasan = reason.strip() if reason.strip() else "—"

        e = discord.Embed(title="💀 Simulasi Ban oleh SatpamBot")
        if target is not None:
            desc = (
                f"{target.mention} terdeteksi mengirim pesan mencurigakan.\n"
                f"(Pesan ini hanya simulasi untuk pengujian.)"
            )
        else:
            desc = (
                "Terjadi deteksi pesan mencurigakan.\n"
                "(Pesan ini hanya simulasi untuk pengujian.)"
            )
        e.description = desc
        e.add_field(name="Lokasi", value=location, inline=False)
        e.add_field(name="Alasan", value=alasan, inline=False)
        e.set_footer(text=f"Simulasi testban • Tidak ada aksi nyata yang dilakukan • {_wib_now_str()}")

        try:
            await ctx.reply(embed=e, mention_author=False)
        except Exception:
            # As a last resort, try to send normally so this never throws to user.
            await ctx.send(embed=e)

async def setup(bot: commands.Bot):
    # Make sure we become the single `tb` command if the runtime supports it.
    if hasattr(bot, "remove_command") and hasattr(bot, "get_command"):
        if bot.get_command("tb"):
            bot.remove_command("tb")
    await bot.add_cog(TBShimFormatted(bot))
