import discord
from discord.ext import commands
from datetime import datetime, timezone

MOD_ROLE_NAMES = {"mod","moderator","admin","administrator","staff"}

def is_moderator(member: discord.Member) -> bool:
    gp = member.guild_permissions
    if gp.administrator or gp.manage_guild or gp.ban_members or gp.kick_members or gp.manage_messages:
        return True
    role_names = {r.name.lower() for r in getattr(member, "roles", [])}
    return any(n in role_names for n in MOD_ROLE_NAMES)

class ModerationTest(commands.Cog):
    """Moderation utilities: !status, !serverinfo, !testban"""
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.start_time = datetime.now(timezone.utc)

    @commands.command(name="status")
    async def status_cmd(self, ctx: commands.Context):
        latency_ms = round(self.bot.latency * 1000) if self.bot.latency is not None else 0
        uptime_delta = datetime.now(timezone.utc) - self.start_time
        embed = discord.Embed(
            title="Bot Status",
            description="Status & metrik dasar",
            color=discord.Color.green()
        )
        embed.add_field(name="Latency", value=f"{latency_ms} ms")
        embed.add_field(name="Uptime", value=str(uptime_delta).split('.')[0], inline=True)
        embed.add_field(name="Guilds", value=str(len(self.bot.guilds)), inline=True)
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=getattr(ctx.author.display_avatar, 'url', discord.Embed.Empty))
        await ctx.send(embed=embed)

    @commands.command(name="serverinfo")
    async def serverinfo_cmd(self, ctx: commands.Context):
        g = ctx.guild
        if not g:
            return await ctx.send("Perintah ini hanya untuk server.")
        embed = discord.Embed(
            title=f"Server Info — {g.name}",
            color=discord.Color.blurple(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="Server ID", value=str(g.id), inline=True)
        embed.add_field(name="Owner", value=getattr(g.owner, 'mention', 'Unknown'), inline=True)
        embed.add_field(name="Members", value=str(g.member_count), inline=True)
        embed.add_field(name="Created", value=g.created_at.strftime("%Y-%m-%d %H:%M UTC"), inline=True)
        if g.icon:
            embed.set_thumbnail(url=g.icon.url)
        await ctx.send(embed=embed)

    @commands.command(name="testban")
    @commands.guild_only()
    async def testban_cmd(self, ctx: commands.Context, member: discord.Member=None, *, reason: str = "Simulasi ban untuk pengujian"):
        """Simulasi ban (HANYA moderator). Tidak benar-benar memban user."""
        if not is_moderator(ctx.author):
            return await ctx.send("❌ Hanya moderator yang dapat menggunakan perintah ini.")
        if member is None:
            return await ctx.send("Gunakan: `!testban @user [alasan]`")

        embed = discord.Embed(
            title="💀 Simulasi Ban oleh SatpamBot",
            description=f"{member.mention} terdeteksi mengirim pesan mencurigakan.\n*(Pesan ini hanya simulasi untuk pengujian.)*",
            color=discord.Color.orange(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="📝 Alasan", value=reason, inline=False)
        try:
            if member.display_avatar:
                embed.set_thumbnail(url=member.display_avatar.url)
        except Exception:
            pass
        embed.set_footer(text="🟢 Simulasi testban")

        sticker_url = None
        try:
            for s in ctx.guild.stickers:
                if s.name.lower() == "fibilaugh":
                    sticker_url = getattr(s, "url", None)
                    break
        except Exception:
            sticker_url = None

        if sticker_url:
            embed.set_image(url=sticker_url)
            await ctx.send(embed=embed)
        else:
            # Fallback: local asset if provided
            try:
                path = "assets/fibilaugh.png"
                file = discord.File(path, filename="fibilaugh.png")
                embed.set_image(url="attachment://fibilaugh.png")
                await ctx.send(embed=embed, file=file)
            except Exception:
                msg = await ctx.send(embed=embed)
                try:
                    await msg.add_reaction("😂")
                except Exception:
                    pass

async def setup(bot: commands.Bot):
    await bot.add_cog(ModerationTest(bot))
