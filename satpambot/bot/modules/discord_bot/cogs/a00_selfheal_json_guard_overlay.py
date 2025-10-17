
import re, json, logging, importlib
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
    s = re.sub(r"\b'([A-Za-z0-9_\-]+)'\s*:", r'"\1":', s)
    s = re.sub(r":\s*'([^'\\]*(?:\\.[^'\\]*)*)'", lambda m: ':"%s"' % m.group(1).replace('"','\\"'), s)
    s = re.sub(r",\s*(?=[}\]])", "", s)
    s = re.sub(r"\bTrue\b", "true", s); s = re.sub(r"\bFalse\b", "false", s); s = re.sub(r"\bNone\b", "null", s)
    return s

def tolerant_loads(text: str):
    try:
        return json.loads(text)
    except Exception:
        pass
    block = _extract_json_block(text)
    if block:
        try:
            return json.loads(block)
        except Exception:
            try:
                return json.loads(_sanitize(block))
            except Exception:
                pass
    try:
        return json.loads(_sanitize(text))
    except Exception:
        raise

class SelfHealJsonGuard(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        try:
            M = importlib.import_module("satpambot.bot.modules.discord_bot.cogs.selfheal_groq_agent")
        except Exception as e:
            LOG.warning("[selfheal-json-guard] import fail: %r", e); 
            return
        try:
            # monkeypatch only inside that module
            M.json.loads = tolerant_loads
            LOG.info("[selfheal-json-guard] patched json.loads in selfheal_groq_agent")
        except Exception as e:
            LOG.warning("[selfheal-json-guard] patch fail: %r", e)

async def setup(bot):
    await bot.add_cog(SelfHealJsonGuard(bot))
