from discord.ext import commands
import discord
class Health(commands.Cog):
    def __init__(self, bot): self.bot=bot
    @commands.command(name="sbhealth")
    async def sbhealth(self, ctx):
        intents=self.bot.intents
        perms = ctx.guild.me.guild_permissions if ctx.guild and ctx.guild.me else None
        info = f"message_content={getattr(intents,'message_content',None)}, members={getattr(intents,'members',None)}, guilds={getattr(intents,'guilds',None)}"
        p = ", ".join([k for k in ['manage_messages','ban_members','moderate_members'] if getattr(perms,k,False)]) if perms else "-"
        emb = discord.Embed(title="SatpamBot Health", color=discord.Color.blue())
        emb.add_field(name="Intents", value=info, inline=False)
        emb.add_field(name="Perms (key)", value=p, inline=False)
        emb.add_field(name="Prefix", value=getattr(self.bot,'command_prefix','!'), inline=True)
        await ctx.send(embed=emb)
async def setup(bot): await bot.add_cog(Health(bot))
