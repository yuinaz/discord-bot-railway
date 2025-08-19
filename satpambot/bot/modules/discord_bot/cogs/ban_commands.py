import typing, datetime as dt, discord
from discord.ext import commands

WIB = dt.timezone(dt.timedelta(hours=7))

async def _infer_member(ctx: commands.Context) -> typing.Optional[discord.Member]:
    # coba dari mention
    if ctx.message.mentions:
        m = ctx.message.mentions[0]
        if isinstance(m, discord.Member):
            return m
        try:
            return await ctx.guild.fetch_member(m.id)
        except Exception:
            pass
    # coba dari reply
    try:
        if ctx.message.reference and ctx.message.reference.message_id:
            ref = await ctx.channel.fetch_message(ctx.message.reference.message_id)
            if isinstance(ref.author, discord.Member):
                return ref.author
            try:
                return await ctx.guild.fetch_member(ref.author.id)
            except Exception:
                pass
    except Exception:
        pass
    return None

def _now_wib():
    return dt.datetime.now(WIB).strftime("%Y-%m-%d %H:%M:%S WIB")

def build_testban_embed(target: discord.abc.User, reason: typing.Optional[str] = None) -> discord.Embed:
    # Gaya seperti screenshot: judul + deskripsi bahasa Indonesia + badge simulasi
    e = discord.Embed(
        title="💀 Simulasi Ban oleh SatpamBot",
        description=(f"{target.mention} terdeteksi mengirim pesan mencurigakan.\n"
                     "(Pesan ini hanya simulasi untuk pengujian.)"),
        color=0xF59E0B,  # amber/ornanye
    )
    e.add_field(name="🟩 Simulasi testban", value=reason or "-", inline=False)
    e.set_footer(text=f"SatpamBot • {_now_wib()}")
    return e

def build_realban_embed(target: discord.abc.User, moderator: discord.abc.User, reason: typing.Optional[str]) -> discord.Embed:
    e = discord.Embed(
        title="🚫 Ban oleh SatpamBot",
        description=f"{target.mention} telah di-*ban* dari server.",
        color=0xEF4444,  # merah
    )
    e.add_field(name="Moderator", value=moderator.mention, inline=True)
    e.add_field(name="Alasan", value=reason or "-", inline=False)
    e.set_footer(text=f"SatpamBot • {_now_wib()}")
    return e

class BanCommands(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="testban", help="Post simulasi ban (tanpa image, tidak spam).")
    @commands.has_permissions(manage_guild=True)
    @commands.guild_only()
    async def testban(self, ctx: commands.Context, member: typing.Optional[discord.Member] = None, *, reason: typing.Optional[str] = None):
        if member is None:
            member = await _infer_member(ctx) or ctx.author
        # hapus embed simulasi sebelumnya agar tidak spam
        async for m in ctx.channel.history(limit=50):
            if m.author.id == ctx.me.id and m.embeds:
                title = (m.embeds[0].title or "").strip().lower()
                if "simulasi ban oleh satpambot" in title or "test ban" in title:
                    try: await m.delete()
                    except Exception: pass
                    break
        e = build_testban_embed(member, reason)
        await ctx.send(embed=e)

    @commands.command(name="ban", help="Ban member: !ban @user [alasan]. Juga bisa reply lalu ketik !ban.")
    @commands.has_permissions(ban_members=True)
    @commands.guild_only()
    async def ban(self, ctx: commands.Context, member: typing.Optional[discord.Member] = None, *, reason: typing.Optional[str] = None):
        if member is None:
            member = await _infer_member(ctx)
            if member is None:
                return await ctx.reply("Gunakan: `!ban @user [alasan]` atau **reply** pesan user lalu ketik `!ban`.", delete_after=12)
        if member == ctx.author:
            return await ctx.reply("Tidak bisa ban diri sendiri.", delete_after=8)
        if ctx.guild.owner_id == member.id:
            return await ctx.reply("Tidak bisa ban pemilik server.", delete_after=8)
        try:
            await member.ban(reason=reason or f"By {ctx.author}")
        except discord.Forbidden:
            return await ctx.reply("Bot tidak punya izin ban user ini.", delete_after=8)
        except Exception as e:
            return await ctx.reply(f"Gagal ban: {e}", delete_after=10)
        e = build_realban_embed(member, ctx.author, reason)
        await ctx.send(embed=e)

async def setup(bot: commands.Bot):
    await bot.add_cog(BanCommands(bot))
