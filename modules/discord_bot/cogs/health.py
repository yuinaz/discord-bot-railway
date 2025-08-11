from discord.ext import commands
import discord, os

class Health(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="sbhealth")
    async def sbhealth(self, ctx: commands.Context):
        intents = self.bot.intents
        flags = []
        flags.append(f"message_content={getattr(intents, 'message_content', None)}")
        flags.append(f"members={getattr(intents, 'members', None)}")
        flags.append(f"guilds={getattr(intents, 'guilds', None)}")
        perms = ctx.guild.me.guild_permissions if ctx.guild and ctx.guild.me else None
        ptxt = []
        if perms:
            for k in ["manage_messages","ban_members","moderate_members","administrator"]:
                ptxt.append(f"{k}={getattr(perms,k)}")
        embed = discord.Embed(title="SatpamBot Health", color=discord.Color.blue())
        embed.add_field(name="Intents", value=", ".join(flags) or "-", inline=False)
        embed.add_field(name="Perms", value=", ".join(ptxt) or "-", inline=False)
        embed.add_field(name="Prefix", value=getattr(self.bot, 'command_prefix', '!'), inline=True)
        embed.set_footer(text="Gunakan !tb / !testban untuk simulasi, kirim invite NSFW untuk uji otoban.")
        await ctx.send(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Health(bot))
