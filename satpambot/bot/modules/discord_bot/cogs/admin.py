import discord
from discord.ext import commands

class Admin(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @commands.has_permissions(ban_members=True)
    @commands.command(name="unban")
    async def unban(self, ctx, user_id: int):
        user = await self.bot.fetch_user(user_id)
        await ctx.guild.unban(user, reason=f"Unban by {ctx.author}")
        await ctx.reply(f"✅ Unbanned `{user}`", mention_author=False)

    @commands.has_permissions(manage_roles=True)
    @commands.command(name="buatrole")
    async def buatrole(self, ctx, *, name: str):
        role = await ctx.guild.create_role(name=name, reason=f"Create by {ctx.author}")
        await ctx.reply(f"✅ Role `{role.name}` dibuat", mention_author=False)

    @commands.has_permissions(manage_channels=True)
    @commands.command(name="buatchannel")
    async def buatchannel(self, ctx, *, name: str):
        ch = await ctx.guild.create_text_channel(name)
        await ctx.reply(f"✅ Channel `#{ch.name}` dibuat", mention_author=False)

async def setup(bot): await bot.add_cog(Admin(bot))
