import typing, datetime as dt, discord
from discord.ext import commands
WIB = dt.timezone(dt.timedelta(hours=7))
def _now_wib(): return dt.datetime.now(WIB).strftime("%Y-%m-%d %H:%M:%S WIB")
def build_realban_embed(target: discord.abc.User, moderator: discord.abc.User, reason: typing.Optional[str]):
    e = discord.Embed(title="🚫 Ban oleh SatpamBot", description=f"{target.mention} telah di-*ban* dari server.", color=0xEF4444)
    e.add_field(name="Moderator", value=moderator.mention, inline=True)
    e.add_field(name="Alasan", value=reason or "-", inline=False)
    e.set_footer(text=f"SatpamBot • {_now_wib()}"); return e
class BanCommands(commands.Cog):
    def __init__(self, bot: commands.Bot): self.bot = bot
    @commands.command(name="ban", help="Ban member: !ban @user [alasan]. Juga bisa reply lalu ketik !ban (auto target).")
    @commands.has_permissions(ban_members=True)
    @commands.guild_only()
    async def ban(self, ctx: commands.Context, member: typing.Optional[discord.Member] = None, *, reason: typing.Optional[str] = None):
        if member is None:
            try:
                if ctx.message.mentions:
                    member = ctx.message.mentions[0]
                elif ctx.message.reference and ctx.message.reference.message_id:
                    ref = await ctx.channel.fetch_message(ctx.message.reference.message_id)
                    member = ref.author if isinstance(ref.author, discord.Member) else None
            except Exception:
                member = None
        if member is None: return await ctx.reply("Gunakan: `!ban @user [alasan]` atau **reply** pesan user lalu ketik `!ban`.", delete_after=12)
        if member == ctx.author: return await ctx.reply("Tidak bisa ban diri sendiri.", delete_after=8)
        if ctx.guild.owner_id == member.id: return await ctx.reply("Tidak bisa ban pemilik server.", delete_after=8)
        try:
            await member.ban(reason=reason or f"By {ctx.author}")
        except discord.Forbidden:
            return await ctx.reply("Bot tidak punya izin ban user ini.", delete_after=8)
        except Exception as e:
            return await ctx.reply(f"Gagal ban: {e}", delete_after=10)
        e = build_realban_embed(member, ctx.author, reason)
        await ctx.send(embed=e)
async def setup(bot): await bot.add_cog(BanCommands(bot))
