from discord.ext import commands
import discord

class TestBanBasic(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="testban", aliases=["tb"])
    async def testban(self, ctx: commands.Context, member: discord.Member=None, *, reason: str="Test ban"):
        if member is None:
            await ctx.reply("Gunakan: !testban @user [alasan]")
            return
        await ctx.send(f"(Simulasi) TestBan aktif. Target: {member.mention}. Alasan: {reason}")

async def setup(bot: commands.Bot):
    await bot.add_cog(TestBanBasic(bot))
