
from __future__ import annotations
import time
import discord
from discord.ext import commands, tasks
from satpambot.config.runtime import cfg

def _mk_embed(title: str, desc: str, color: int):
    return discord.Embed(title=title, description=desc, color=color)

class CrashGuard(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.window = 600  # 10 minutes
        self.threshold = int(cfg('CRASH_ERR_PER_10M', 12))
        self._errors = []  # list of (ts, where, brief)
        if hasattr(self, 'housekeep'):
            self.housekeep.start()  # type: ignore

    def _prune(self):
        cutoff = time.time() - self.window
        self._errors = [e for e in self._errors if e[0] >= cutoff]

    def _count(self) -> int:
        self._prune(); return len(self._errors)

    @tasks.loop(seconds=60)
    async def housekeep(self):
        try:
            self._prune()
            if self._count() >= self.threshold:
                # Attempt half-power
                try:
                    sm = self.bot.get_cog('SelfMaintenanceManager')
                    if sm and hasattr(sm, 'set_half_power'):
                        await sm.set_half_power()
                except Exception:
                    pass
                # DM owner
                owner = cfg('OWNER_USER_ID')
                if owner:
                    try:
                        user = self.bot.get_user(int(owner)) or await self.bot.fetch_user(int(owner))
                        if user:
                            msg = f"High error rate detected (>{self.threshold}/10m). Switched to half-power."
                            await user.send(embed=_mk_embed('CrashGuard', msg, 0xe74c3c))
                    except Exception:
                        pass
                # reset bucket to avoid spamming
                self._errors.clear()
        except Exception:
            pass

    @commands.Cog.listener()
    async def on_error(self, event_method: str, *args, **kwargs):
        brief = f'Event {event_method} failed'
        self._errors.append((time.time(), event_method, brief))

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, exception: Exception):
        brief = f'Cmd {getattr(ctx.command, "qualified_name", "?")} error: {type(exception).__name__}'
        self._errors.append((time.time(), 'command', brief))

    @commands.Cog.listener()
    async def on_message(self, message: 'discord.Message'):
        if message.author.bot: return
        if not isinstance(message.channel, (discord.DMChannel, discord.GroupChannel)): return
        if str(message.content).strip().lower() in ('errors recent','crash recent'):
            self._prune()
            items = [f"{time.strftime('%H:%M:%S', time.localtime(ts))} — {brief}" for ts,_,brief in self._errors[-15:]]
            desc = '\n'.join(items) if items else 'No recent errors.'
            await message.channel.send(embed=_mk_embed('Recent Errors', desc, 0x95a5a6))

async def setup(bot):
    await bot.add_cog(CrashGuard(bot))
