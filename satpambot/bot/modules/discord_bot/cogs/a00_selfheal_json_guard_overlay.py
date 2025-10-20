
import re, json as _stdlib_json, logging, importlib, types
from discord.ext import commands

LOG = logging.getLogger(__name__)

def _extract_json_block(text: str):
    if not text: return None
    m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.I)
    if m: return m.group(1).strip()
    start = text.find("{")
    if start == -1: return None
    depth = 0
    for i, ch in enumerate(text[start:], start=start):
        if ch == "{": depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start:i+1]
    return None

def _sanitize(s: str) -> str:
    s = re.sub(r"(?m)\b'([A-Za-z0-9_\-]+)'\s*:", r'"\1":', s)
    s = re.sub(r":\s*'([^'\\]*(?:\\.[^'\\]*)*)'", lambda m: ':"%s"' % m.group(1).replace('"','\\"'), s)
    s = re.sub(r",\s*(?=[}\]])", "", s)
    s = re.sub(r"\bTrue\b", "true", s)
    s = re.sub(r"\bFalse\b", "false", s)
    s = re.sub(r"\bNone\b", "null", s)
    return s

def tolerant_loads(text: str):
    try:
        return _stdlib_json.loads(text)
    except Exception:
        pass
    block = _extract_json_block(text)
    if block:
        try:
            return _stdlib_json.loads(block)
        except Exception:
            try:
                return _stdlib_json.loads(_sanitize(block))
            except Exception:
                pass
    return _stdlib_json.loads(_sanitize(text))

class _JsonShim(types.SimpleNamespace):
    def __init__(self, real_json):
        super().__init__()
        self._real = real_json
        self.dumps = real_json.dumps
        self.dump = real_json.dump
        self.JSONDecodeError = real_json.JSONDecodeError
    def loads(self, s, *a, **kw):
        return tolerant_loads(s)
    def __getattr__(self, name):
        return getattr(self._real, name)

class SelfHealJsonGuardScoped(commands.Cog):
    def __init__(self, bot): self.bot = bot
    @commands.Cog.listener()
    async def on_ready(self):
        try:
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
