# satpambot/bot/modules/discord_bot/cogs/rules_never_send.py
"""
Hard-deny send to #rules (or any configured channel) without logging or raising.
This cog monkey-patches discord.abc.Messageable.send so ANY attempt to send to
blocked channels is silently skipped. Works alongside existing silencers.
ENV:
  RULES_NEVER_SEND_IDS    = comma separated channel IDs (e.g. "123,456")
  RULES_NEVER_SEND_NAMES  = comma separated names (default: "rules,⛔︲rules")
  RULES_NEVER_SEND_DEBUG  = "1" to log one-line deny messages
"""
from discord.ext import commands
import discord, os, logging

log = logging.getLogger(__name__)

def _parse_ids(s: str):
    out = set()
    for part in (s or "").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            out.add(int(part))
        except ValueError:
            pass
    return out

def _parse_names(s: str):
    names = set()
    for part in (s or "").split(","):
        p = part.strip().lower()
        if p:
            names.add(p)
    return names

class RulesNeverSend(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        ids = _parse_ids(os.getenv("RULES_NEVER_SEND_IDS",""))
        names = _parse_names(os.getenv("RULES_NEVER_SEND_NAMES","rules,⛔︲rules"))
        self.debug = os.getenv("RULES_NEVER_SEND_DEBUG","0") == "1"

        # keep original and install patched
        self._orig_send = discord.abc.Messageable.send

        async def _patched_send(target, *args, **kwargs):
            try:
                cid = getattr(target, "id", None)
                name = getattr(target, "name", "").lower()
                if (cid in ids) or (name in names):
                    if self.debug:
                        log.info("[rules-never-send] drop send on #%s (id=%s)", name or "?", cid)
                    # Silent drop: behave as no-op; return None
                    return None
            except Exception:
                # In any unexpected case, fall back to original behavior
                pass
            return await self._orig_send(target, *args, **kwargs)

        discord.abc.Messageable.send = _patched_send
        log.info("[rules-never-send] installed (ids=%s, names=%s)", sorted(ids) or [], sorted(names) or [])

    def cog_unload(self):
        # restore original
        discord.abc.Messageable.send = self._orig_send
        log.info("[rules-never-send] uninstalled")

async def setup(bot: commands.Bot):
    await bot.add_cog(RulesNeverSend(bot))
