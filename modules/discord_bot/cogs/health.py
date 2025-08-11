from discord.ext import commands
import discord, os, platform, socket
from ..helpers.log_utils import upsert_status_embed_in_channel

class Health(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._hb_tasks = {}

    @commands.command(name="sbhealth")
    async def sbhealth(self, ctx: commands.Context):
        intents = self.bot.intents
        perms = ctx.guild.me.guild_permissions if ctx.guild and ctx.guild.me else None
        embed = discord.Embed(title="SatpamBot Health", color=discord.Color.blue())
        embed.add_field(name="Intents", value=f"message_content={getattr(intents,'message_content',None)}, members={getattr(intents,'members',None)}, guilds={getattr(intents,'guilds',None)}", inline=False)
        ptxt = ", ".join([k for k in ['manage_messages','ban_members','moderate_members','administrator'] if getattr(perms,k,False)]) if perms else "-"
        embed.add_field(name="Perms", value=ptxt, inline=False)
        embed.add_field(name="Prefix", value=getattr(self.bot, 'command_prefix', '!'), inline=True)
        await ctx.send(embed=embed)

    @commands.command(name="sbwho")
    async def sbwho(self, ctx: commands.Context):
        exts = sorted(self.bot.extensions.keys())
        cogs = sorted(self.bot.cogs.keys())
        embed = discord.Embed(title="SatpamBot Loaded", color=discord.Color.green())
        embed.add_field(name="Extensions", value=(", ".join(exts) or "-"), inline=False)
        embed.add_field(name="Cogs", value=(", ".join(cogs) or "-"), inline=False)
        await ctx.send(embed=embed)

    @commands.command(name="sbpid")
    async def sbpid(self, ctx: commands.Context):
        host = socket.gethostname()
        await ctx.send(f"Host={host} | PID={os.getpid()} | Python={platform.python_version()}")

    @commands.command(name="sbstatus")
    @commands.has_permissions(manage_guild=True)
    async def sbstatus(self, ctx: commands.Context):
        ok = await upsert_status_embed_in_channel(ctx.channel, "✅ SatpamBot online dan siap berjaga.")
        await ctx.message.add_reaction("✅" if ok else "❌")

    @commands.command(name="sbheartbeat")
    @commands.has_permissions(manage_guild=True)
    async def sbheartbeat(self, ctx: commands.Context, toggle: str = "on"):
        g = ctx.guild
        if not g:
            await ctx.send("Jalankan di dalam server."); return
        key = g.id
        if toggle.lower() == "off":
            t = self._hb_tasks.pop(key, None)
            if t: t.cancel()
            await ctx.send("Heartbeat dimatikan."); return
        ch = ctx.channel
        async def loop():
            import asyncio
            while True:
                try:
                    await upsert_status_embed_in_channel(ch, "✅ SatpamBot online dan siap berjaga.")
                    await asyncio.sleep(600)
                except asyncio.CancelledError: break
                except Exception: await asyncio.sleep(600)
        old = self._hb_tasks.get(key)
        if old:
            try: old.cancel()
            except Exception: pass
        self._hb_tasks[key] = self.bot.loop.create_task(loop())
        await ctx.send("Heartbeat diaktifkan di channel ini.")

async def setup(bot: commands.Bot):
    await bot.add_cog(Health(bot))
