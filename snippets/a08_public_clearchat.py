# Drop-in replacement/snippet for satpambot.bot.modules.discord_bot.cogs.a08_public_clearchat
# Safe purge for public channels with allowlist from local.json

import asyncio
import datetime as dt
from typing import Optional

import discord
from discord.ext import commands

def _cfg_get(bot, path, default=None):
    # minimal shim – adapt if you have a central config helper
    try:
        cfg = getattr(bot, "local_cfg", None) or {}
        for key in path.split("."):
            if key == "$ids":  # support "$ids.X" indirection
                cfg = cfg.get("ids", {})
            else:
                cfg = cfg.get(key, {} if isinstance(cfg, dict) else None)
        return cfg if cfg else default
    except Exception:
        return default

def _resolve_ids(bot, seq):
    out = []
    ids = (_cfg_get(bot, "ids") or {})
    for x in (seq or []):
        if isinstance(x, int):
            out.append(x)
        elif isinstance(x, str) and x.startswith("$ids."):
            out.append(int(ids.get(x.split(".",1)[1], 0)))
        else:
            try:
                out.append(int(x))
            except Exception:
                pass
    return [i for i in out if i]

class ClearChat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command(name="clearchat", description="Delete recent messages (safe mode)")
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True, read_message_history=True)
    async def clearchat(self, ctx: commands.Context,
                        amount: Optional[int] = 100,
                        bots: Optional[bool] = False,
                        since: Optional[str] = None):
        """Purges messages with guardrails:
        - only in channels listed in local.json.clearchat.public.allowed_channel_ids
        - keep pins & stickies
        - default limit = 100 (max 250)
        - optional: bots=true to remove bot messages only
        - optional: since=2h/30m/3d
        """
        if not isinstance(ctx.channel, (discord.TextChannel, discord.Thread)):
            return await ctx.reply("Channel tidak didukung.", ephemeral=True)

        ll = _resolve_ids(self.bot, _cfg_get(self.bot, "clearchat.public.allowed_channel_ids", []))
        if ctx.channel.id not in ll:
            return await ctx.reply("Channel ini tidak diallow untuk /clearchat (cek local.json).", ephemeral=True)

        limit = max(1, min(int(amount or 100), int(_cfg_get(self.bot, "clearchat.public.max_per_run", 250))))
        keep_pins = bool(_cfg_get(self.bot, "clearchat.public.keep_pins", True))
        keep_stickies = bool(_cfg_get(self.bot, "clearchat.public.keep_stickies", True))

        # parse since
        after = None
        if since:
            now = dt.datetime.utcnow()
            try:
                if since.endswith("m"):
                    after = now - dt.timedelta(minutes=int(since[:-1]))
                elif since.endswith("h"):
                    after = now - dt.timedelta(hours=int(since[:-1]))
                elif since.endswith("d"):
                    after = now - dt.timedelta(days=int(since[:-1]))
            except Exception:
                pass

        def _check(msg: discord.Message):
            if keep_pins and getattr(msg, "pinned", False):
                return False
            if keep_stickies and msg.author.id == self.bot.user.id and msg.embeds:
                # heuristic: bot's own sticky-like embeds
                return False
            if bots and msg.author.bot is False:
                return False
            return True

        # read history and delete one-by-one (safer with shims that wrap delete)
        deleted = 0
        async for msg in ctx.channel.history(limit=limit, after=after):
            try:
                if _check(msg):
                    await msg.delete()
                    deleted += 1
                    await asyncio.sleep(0.3)  # avoid 429
            except discord.Forbidden:
                return await ctx.reply("Tidak punya izin Manage Messages di channel ini.", ephemeral=True)
            except Exception:
                pass

        await ctx.reply(f"Selesai. Dihapus: {deleted} pesan (limit={limit}).", ephemeral=True)

async def setup(bot):
    # await if add_cog is awaitable in your lib
    import inspect
    async def maybe_await(x):
        if inspect.isawaitable(x):
            return await x
        return x
    await maybe_await(bot.add_cog(ClearChat(bot)))
