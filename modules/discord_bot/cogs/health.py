from discord.ext import commands
import discord
from ..helpers.log_utils import upsert_status_embed, LOG_PHISH_NAME
import os

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


    @commands.command(name="sbwho")
    async def sbwho(self, ctx: commands.Context):
        try:
            exts = sorted(self.bot.extensions.keys())
            cogs = sorted(self.bot.cogs.keys())
            embed = discord.Embed(title="SatpamBot Loaded", color=discord.Color.green())
            embed.add_field(name="Extensions", value=(", ".join(exts) or "-"), inline=False)
            embed.add_field(name="Cogs", value=(", ".join(cogs) or "-"), inline=False)
            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f"diag err: {e}")


    _hb_tasks = {}
    @commands.command(name="sbheartbeat")
    @commands.has_permissions(manage_guild=True)
    async def sbheartbeat(self, ctx: commands.Context, toggle: str = "on"):
        guild = ctx.guild
        if not guild:
            await ctx.send("Jalankan di dalam server."); return
        if toggle.lower() not in ("on","off"):
            await ctx.send("Gunakan: !sbheartbeat on|off"); return
        if toggle.lower()=="off":
            t = _hb_tasks.pop(guild.id, None)
            if t: t.cancel()
            await ctx.send("Heartbeat dimatikan."); return
        ch = ctx.channel
        async def loop():
            import asyncio
            while True:
                try:
                    await upsert_status_embed(guild, "✅ SatpamBot online dan siap berjaga.", channel_name=LOG_PHISH_NAME)
                    await asyncio.sleep(600)
                except asyncio.CancelledError: break
                except Exception: await asyncio.sleep(600)
        task = self.bot.loop.create_task(loop())
        _hb_tasks[guild.id] = task
        await ctx.send("Heartbeat diaktifkan di channel ini.")

async def setup(bot: commands.Bot):
    await bot.add_cog(Health(bot))
