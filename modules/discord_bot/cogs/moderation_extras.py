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

class ModerationExtras(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

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
        if g.icon: embed.set_thumbnail(url=g.icon.url)
        await ctx.send(embed=embed)

    @commands.command(name="testban")
    @commands.guild_only()
    async def testban_cmd(self, ctx: commands.Context, member: discord.Member=None, *, reason: str = "Simulasi ban untuk pengujian"):
        if not is_moderator(ctx.author):
            return await ctx.send("❌ Hanya moderator yang dapat menggunakan perintah ini.")
        if member is None:
            return await ctx.send("Gunakan: `!testban @user [alasan]`")
        embed = discord.Embed(
            title="💀 Simulasi Ban oleh SatpamBot",
            description=f"{member.mention} terdeteksi mengirim pesan mencurigakan.\n*(Simulasi)*",
            color=discord.Color.orange(),
            timestamp=datetime.now(timezone.utc)
        )
        embed.add_field(name="📝 Alasan", value=reason, inline=False)
        try:
            if member.display_avatar: embed.set_thumbnail(url=member.display_avatar.url)
        except Exception: pass
        # sticker FibiLaugh
        sticker_url=None
        try:
            for s in ctx.guild.stickers:
                if s.name.lower()=="fibilaugh":
                    sticker_url = getattr(s,'url',None); break
        except Exception: sticker_url=None
        if sticker_url:
            embed.set_image(url=sticker_url); await ctx.send(embed=embed)
        else:
            try:
                file = discord.File("assets/fibilaugh.png", filename="fibilaugh.png")
                embed.set_image(url="attachment://fibilaugh.png")
                await ctx.send(embed=embed, file=file)
            except Exception:
                await ctx.send(embed=embed)

    @commands.command(name="ban")
    @commands.guild_only()
    @commands.has_permissions(ban_members=True)
    async def ban_cmd(self, ctx: commands.Context, member: discord.Member=None, *, reason: str = "Melanggar aturan"):
        if member is None:
            return await ctx.send("Gunakan: `!ban @user [alasan]`")
        if member == ctx.author:
            return await ctx.send("Tidak bisa ban diri sendiri.")
        try:
            await member.ban(reason=reason, delete_message_days=0)
        except discord.Forbidden:
            return await ctx.send("❌ Aku tidak punya izin untuk memban user ini.")
        except Exception as e:
            return await ctx.send(f"❌ Gagal memban: {e}")
        embed = discord.Embed(title="🚫 User Dibanned", description=f"{member.mention} telah dibanned.", color=discord.Color.red(), timestamp=datetime.now(timezone.utc))
        embed.add_field(name="Moderator", value=ctx.author.mention, inline=True)
        embed.add_field(name="Alasan", value=reason, inline=False)
        try:
            if member.display_avatar: embed.set_thumbnail(url=member.display_avatar.url)
        except Exception: pass
        sticker_url=None
        try:
            for s in ctx.guild.stickers:
                if s.name.lower()=="fibilaugh":
                    sticker_url = getattr(s,'url',None); break
        except Exception: sticker_url=None
        if sticker_url:
            embed.set_image(url=sticker_url); await ctx.send(embed=embed)
        else:
            try:
                file = discord.File("assets/fibilaugh.png", filename="fibilaugh.png")
                embed.set_image(url="attachment://fibilaugh.png")
                await ctx.send(embed=embed, file=file)
            except Exception:
                await ctx.send(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(ModerationExtras(bot))
