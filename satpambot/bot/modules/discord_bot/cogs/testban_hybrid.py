import typing, datetime as dt, discord
from discord.ext import commands
WIB = dt.timezone(dt.timedelta(hours=7))
def _now_wib(): return dt.datetime.now(WIB).strftime("%Y-%m-%d %H:%M:%S WIB")
async def _infer_member(ctx: commands.Context) -> typing.Optional[discord.Member]:
    if ctx.message.mentions:
        m = ctx.message.mentions[0]
        if isinstance(m, discord.Member): return m
        try: return await ctx.guild.fetch_member(m.id)
        except Exception: pass
    try:
        if ctx.message.reference and ctx.message.reference.message_id:
            ref = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            if isinstance(ref.author, discord.Member): return ref.author
            try: return await ctx.guild.fetch_member(ref.author.id)
            except Exception: pass
    except Exception: pass
    return None
def build_embed(target: discord.abc.User, reason: typing.Optional[str] = None) -> discord.Embed:
    e = discord.Embed(title="💀 Simulasi Ban oleh SatpamBot",
                      description=(f"{target.mention} terdeteksi mengirim pesan mencurigakan.\n"
                                   "(Pesan ini hanya simulasi untuk pengujian.)"),
                      color=0xF59E0B)
    e.add_field(name="🟩 Simulasi testban", value=(reason or "-"), inline=False)
    e.set_footer(text=f"SatpamBot • {_now_wib()}")
    return e
class Testban(commands.Cog):
    def __init__(self, bot: commands.Bot): self.bot = bot
    @commands.command(name="tb", help="Simulasi ban: !tb [@user?] [alasan?]. Bisa reply lalu ketik !tb")
    @commands.has_permissions(manage_guild=True)
    @commands.guild_only()
    async def tb(self, ctx: commands.Context, *, reason: typing.Optional[str] = None):
        member = await _infer_member(ctx)
        if member is None:
            try:
                tokens = reason.split() if isinstance(reason, str) else []
                if tokens and tokens[0].startswith("<@") and tokens[0].endswith(">"):
                    uid = int(tokens[0].strip("<@!>"))
                    member = await ctx.guild.fetch_member(uid)
                    reason = " ".join(tokens[1:]) if len(tokens)>1 else None
            except Exception:
                member = None
        if member is None:
            member = ctx.author
        async for m in ctx.channel.history(limit=50):
            if m.author.id == ctx.me.id and m.embeds:
                title = (m.embeds[0].title or "").lower()
                if "simulasi ban oleh satpambot" in title:
                    try: await m.delete()
                    except Exception: pass
                    break
        e = build_embed(member, reason)
        await ctx.send(embed=e)
async def setup(bot: commands.Bot):
    try: bot.remove_command("tb")
    except Exception: pass
    await bot.add_cog(Testban(bot))
