# a00_json_repair_guard_overlay.py
from __future__ import annotations
import json as _stdlib_json, re, logging, sys, types
from discord.ext import commands
log = logging.getLogger(__name__)

SMART_QUOTES = {"‘": "'", "’": "'", "“": '"', "”": '"', "“": '"', "”": '"', "’": "'", "‘": "'"}
_WS_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")
_CODEFENCE = re.compile(r"```(?:json|JSON)?\s*([\s\S]*?)```", re.M)
_LINE_COMMENTS = re.compile(r"(^|\n)\s*//.*?(?=\n|$)")
_BLOCK_COMMENTS = re.compile(r"/\*[\s\S]*?\*/", re.M)

def _normalize_quotes(s: str) -> str: return "".join(SMART_QUOTES.get(ch, ch) for ch in s)
def _strip_code_fences(s: str) -> str:
    m = _CODEFENCE.search(s);  return m.group(1) if m else s
def _kill_comments(s: str) -> str: return _LINE_COMMENTS.sub("\n", _BLOCK_COMMENTS.sub("", s))
def _strip_ctrl(s: str) -> str: return _WS_CTRL.sub(" ", s)
def _balance_braces(s: str) -> str:
    start = s.find("{");  
    if start == -1: return s
    depth = 0
    for i in range(start, len(s)):
        ch = s[i]
        if ch == "{": depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0: return s[start:i+1]
    return s[start:]
def _fix_trailing_commas(s: str) -> str: return re.sub(r",\s*([}\]])", r"\1", s)
def _escape_newlines_in_strings(s: str) -> str:
    out=[]; in_str=False; esc=False
    for ch in s:
        if esc: out.append(ch); esc=False; continue
        if ch == "\\": out.append(ch); esc=True; continue
        if ch == '"': in_str = not in_str; out.append(ch); continue
        if ch == "\n" and in_str: out.append("\\n"); continue
        out.append(ch)
    if in_str: out.append('"')
    return "".join(out)

def _sanitize(text: str) -> str:
    s = str(text)
    s = _strip_code_fences(s)
    s = _normalize_quotes(s)
    s = _kill_comments(s)
    s = _strip_ctrl(s)
    s = _balance_braces(s)
    s = _escape_newlines_in_strings(s)
    s = _fix_trailing_commas(s)
    return s.strip()

def tolerant_loads(text: str):
    try: return _stdlib_json.loads(text)
    except Exception: pass
    try:
        s = _sanitize(text);  return _stdlib_json.loads(s)
    except Exception:
        try:
            s = _balance_braces(s if 's' in locals() else str(text))
            s = _fix_trailing_commas(_escape_newlines_in_strings(_normalize_quotes(s)))
            return _stdlib_json.loads(s)
        except Exception as e2:
            log.debug("[json-guard+] tolerant_loads failed: %r", e2);  return None

def _install_into_guard_module():
    modname = "satpambot.bot.modules.discord_bot.cogs.a00_selfheal_json_guard_overlay"
    mod = sys.modules.get(modname)
    if isinstance(mod, types.ModuleType):
        try:
            setattr(mod, "tolerant_loads", tolerant_loads)
            setattr(mod, "loads", tolerant_loads)
            log.info("[json-guard+] patched %s.loads -> tolerant_loads", modname)
        except Exception as e:
            log.debug("[json-guard+] patch guard module failed: %r", e)

def _monkeypatch_json_for(module_names):
    for mname in module_names:
        mod = sys.modules.get(mname)
        if not isinstance(mod, types.ModuleType): continue
        try:
            if hasattr(mod, "json"):
                setattr(mod.json, "loads", tolerant_loads)
                log.info("[json-guard+] monkeypatched json.loads in %s", mname)
        except Exception as e:
            log.debug("[json-guard+] json patch failed in %s: %r", mname, e)

TARGETS = ("satpambot.bot.modules.discord_bot.cogs.selfheal_groq_agent",)

class JsonRepairGuard(commands.Cog):
    def __init__(self, bot): self.bot = bot
    @commands.Cog.listener()
    async def on_ready(self):
        _install_into_guard_module()
        _monkeypatch_json_for(TARGETS)
        log.info("[json-guard+] installed tolerant JSON loader")

loads = tolerant_loads
async def setup(bot): await bot.add_cog(JsonRepairGuard(bot))
