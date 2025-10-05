import os, json, asyncio, pathlib, datetime as dt, discord
from discord.ext import commands, tasks

WIB = dt.timezone(dt.timedelta(hours=7))
def _now_wib(): return dt.datetime.now(WIB).strftime("%Y-%m-%d %H:%M:%S WIB")

DATA_DIR = pathlib.Path("data")
WL_FILE = DATA_DIR / "whitelist.json"
QUEUE_DIR = DATA_DIR / "ban_queue"
PROC_DIR = QUEUE_DIR / "_processed"

LOG_ENV_KEYS = ("LOG_CHANNEL_ID","ERROR_LOG_CHANNEL_ID","LOG_CHANNEL_ERROR")
FALLBACK_NAMES = ("log-botphising","errorlog-bot","errorlog","log-bot")

def _read_whitelist():
    try:
        d = json.loads(WL_FILE.read_text("utf-8"))
        return set(d.get("list", []))
    except Exception:
        return set()

def _find_log_channel(guild: discord.Guild):
    for k in LOG_ENV_KEYS:
        try:
            raw = os.getenv(k)
            if raw:
                cid = int(raw)
                ch = guild.get_channel(cid) or next((c for c in guild.text_channels if c.id == cid), None)
                if ch and isinstance(ch, discord.TextChannel):
                    return ch
        except Exception:
            pass
    for name in FALLBACK_NAMES:
        ch = discord.utils.get(guild.text_channels, name=name)
        if ch:
            return ch
    return None

class BanQueueWatcher(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.task = self.process_queue.start()

    def cog_unload(self):
        try: self.process_queue.cancel()
        except Exception: pass

    @tasks.loop(seconds=10.0)
    async def process_queue(self):
        QUEUE_DIR.mkdir(parents=True, exist_ok=True)
        PROC_DIR.mkdir(parents=True, exist_ok=True)
        wl = _read_whitelist()

        for p in sorted(QUEUE_DIR.glob("*.json")):
            try:
                item = json.loads(p.read_text("utf-8"))
                uid = str(item.get("user_id") or "").strip()
                if not uid:
                    p.unlink(missing_ok=True); continue
                if uid in wl:
                    p.rename(PROC_DIR / p.name)
                    continue
                reason = item.get("reason") or "phishing evidence"
                proof = item.get("proof") or None

                if not self.bot.guilds:
                    continue
                guild = self.bot.guilds[0]
                ch_log = _find_log_channel(guild)

                target = None
                try:
                    target = await guild.fetch_member(int(uid))
                except Exception:
                    pass

                try:
                    if target is not None:
                        await guild.ban(target, reason=reason, delete_message_days=0)
                    else:
                        await guild.ban(discord.Object(id=int(uid)), reason=reason, delete_message_days=0)
                except Exception as e:
                    if ch_log:
                        embed = discord.Embed(title="❌ Auto-ban gagal", color=discord.Color.red())
                        embed.add_field(name="User ID", value=uid, inline=True)
                        embed.add_field(name="Reason", value=reason, inline=True)
                        embed.description = f"`{e}`"
                        embed.set_footer(text=f"SatpamBot • {_now_wib()}")
                        await ch_log.send(embed=embed)
                    p.rename(PROC_DIR / p.name)
                    continue

                if ch_log:
                    e = discord.Embed(title="✅ Auto-ban phishing", color=discord.Color.green())
                    e.add_field(name="User ID", value=uid, inline=True)
                    e.add_field(name="Reason", value=reason, inline=True)
                    if proof and os.path.exists(proof):
                        try:
                            file = discord.File(proof, filename=os.path.basename(proof))
                            e.set_footer(text=f"SatpamBot • {_now_wib()}")
                            await ch_log.send(embed=e, file=file)
                        except Exception:
                            e.set_footer(text=f"SatpamBot • {_now_wib()}")
                            await ch_log.send(embed=e)
                    else:
                        e.set_footer(text=f"SatpamBot • {_now_wib()}")
                        await ch_log.send(embed=e)

                p.rename(PROC_DIR / p.name)
            except Exception:
                try: p.rename(PROC_DIR / p.name)
                except Exception: pass

    @process_queue.before_loop
    async def before_loop(self):
        await self.bot.wait_until_ready()

async def setup(bot: commands.Bot):
    await bot.add_cog(BanQueueWatcher(bot))
