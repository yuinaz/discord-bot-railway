# patched a00_json_repair_guard_overlay.py
from __future__ import annotations
import json as _stdlib_json, logging, types
from discord.ext import commands

LOG = logging.getLogger(__name__)

def _sanitize(text: str) -> str:
    import re
    if text is None:
        return ""
    if not isinstance(text, str):
        try:
            text = text.decode("utf-8", "ignore")
        except Exception:
            text = str(text)
    text = text.replace("\x00", "")
    text = re.sub(r',\s*([}\]])', r'\1', text)
    return text.strip()

def tolerant_loads(text: str, *args, **kwargs):
    try:
        return _stdlib_json.loads(text, **kwargs)
    except Exception:
        try:
            return _stdlib_json.loads(_sanitize(text), **kwargs)
        except Exception:
            return None

class _JsonShim(types.SimpleNamespace):
    def __init__(self, real_json):
        super().__init__()
        self._real = real_json
        self.dumps = real_json.dumps
        self.dump = real_json.dump
        self.JSONDecodeError = real_json.JSONDecodeError
    def loads(self, s, *a, **kw):
        return tolerant_loads(s, *a, **kw)
    def __getattr__(self, name):
        return getattr(self._real, name)

class SelfHealJsonGuardScoped(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        try:
            import importlib
            M = importlib.import_module("satpambot.bot.modules.discord_bot.cogs.selfheal_groq_agent")
        except Exception as e:
            LOG.debug("[selfheal-json-guard-scoped] import fail: %r", e); return
        try:
            setattr(M, "json", _JsonShim(_stdlib_json))
            LOG.info("[selfheal-json-guard-scoped] scoped shim installed")
        except Exception as e:
            LOG.warning("[selfheal-json-guard-scoped] patch fail: %r", e)

async def setup(bot):
    await bot.add_cog(SelfHealJsonGuardScoped(bot))
