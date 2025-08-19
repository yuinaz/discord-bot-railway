import asyncio, logging, discord
from discord.ext import commands
log = logging.getLogger("slash_broadcast")
def _pick_channel(bot: commands.Bot):
    preferred = {"mod-command", "log-botphising", "errorlog-bot"}
    for g in bot.guilds:
        for ch in g.text_channels:
            if ch.name in preferred and ch.permissions_for(g.me).send_messages: return ch
    for g in bot.guilds:
        for ch in g.text_channels:
            if ch.permissions_for(g.me).send_messages: return ch
    return None
class SlashListBroadcast(commands.Cog):
    def __init__(self, bot): self.bot=bot; self.task=self.bot.loop.create_task(self._run())
    async def _run(self):
        await self.bot.wait_until_ready(); await asyncio.sleep(2)
        ch=_pick_channel(self.bot); if not ch: return
        global_cmds=sorted({c.name for c in self.bot.tree.get_commands()})
        lines=["**Slash commands (global)**: "+(', '.join(global_cmds) or '-')]
        for g in self.bot.guilds:
            guild_cmds=sorted({c.name for c in self.bot.tree.get_commands(guild=discord.Object(id=g.id))})
            lines.append(f"**Guild {g.name}**: "+(', '.join(guild_cmds) or '-'))
        try: await ch.send("\n".join(lines))
        except Exception as e: log.exception("post slash list failed: %s", e)
    def cog_unload(self):
        try: self.task.cancel()
        except Exception: pass
async def setup(bot): await bot.add_cog(SlashListBroadcast(bot))
