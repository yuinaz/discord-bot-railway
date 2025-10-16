
# a01_autolearn_config_listener_overlay.py (v8.0a)

import os, logging, inspect, asyncio
try:
    from discord.ext import commands
except Exception:  # fallback stub if import fails in smoke env
    class _Dummy: pass
    class commands:
        Cog = _Dummy
log = logging.getLogger(__name__)

async def _safe_add_cog(bot, cog):
    try:
        # discord.py 2.x style: add_cog is sync, but setup() is awaited by loader
        bot.add_cog(cog)
        return True
    except TypeError:
        # some wrappers expect awaitable
        try:
            res = getattr(bot, "add_cog")(cog)
            if inspect.isawaitable(res):
                await res
            return True
        except Exception as e:
            log.info("[listener:setup] add_cog failed: %r", e)
            return False
    except Exception as e:
        log.info("[listener:setup] add_cog error: %r", e)
        return False

def _install_sync(bot, cog_cls):
    try:
        # schedule async add if loop running
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(_safe_add_cog(bot, cog_cls(bot)))
            return True
        else:
            loop.run_until_complete(_safe_add_cog(bot, cog_cls(bot)))
            return True
    except Exception as e:
        # last resort: plain sync add
        try:
            bot.add_cog(cog_cls(bot))
            return True
        except Exception as e2:
            log.info("[listener:setup] sync fallback failed: %r / %r", e, e2)
            return False


def _boolenv(v, default=False):
    if v is None: return default
    s = str(v).strip().lower()
    return s in ("1","true","yes","on")

async def _maybe_call(obj, name, *args, **kwargs):
    fn = getattr(obj, name, None)
    if not fn: return False
    try:
        res = fn(*args, **kwargs)
        if inspect.isawaitable(res):
            await res
        return True
    except Exception as e:
        log.info("[config-apply] %s.%s failed: %r", obj.__class__.__name__, name, e)
        return False

class AutoLearnConfigListener(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _snapshot(self):
        return {
            "enabled": _boolenv(os.getenv("AUTOLEARN_ENABLED","1"), True),
            "embed": _boolenv(os.getenv("AUTOLEARN_EMBED","1"), True),
            "persona_file": os.getenv("PERSONA_FILE"),
            "provider": os.getenv("LLM_PROVIDER"),
            "groq_model": os.getenv("LLM_GROQ_MODEL"),
            "gemini_model": os.getenv("LLM_GEMINI_MODEL"),
            "temperature": os.getenv("LLM_TEMPERATURE"),
        }

    async def _apply_to_cog(self, cog, snap):
        if await _maybe_call(cog, "on_config_changed", "autolearn", snap): return True
        if await _maybe_call(cog, "reload_from_env"): return True
        # Fallback attributes
        for k,v in [
            ("enabled", snap["enabled"]),
            ("embed", snap["embed"]),
            ("answer_embed", snap["embed"]),
            ("embed_enabled", snap["embed"]),
            ("use_embed", snap["embed"]),
            ("persona_file", snap["persona_file"]),
        ]:
            try:
                if hasattr(cog, k):
                    setattr(cog, k, v)
            except Exception: pass
        return True

    def _match_cog(self, name, cog):
        n = (name or "").lower()
        if "autolearn" in n or "qna" in n:
            return True
        for marker in ("autolearn", "answer_embed", "embed_enabled"):
            if hasattr(cog, marker): return True
        return False

    async def _apply_all(self, name):
        snap = self._snapshot()
        applied = 0
        for cname, cog in list(self.bot.cogs.items()):
            try:
                if self._match_cog(cname, cog):
                    ok = await self._apply_to_cog(cog, snap)
                    if ok: applied += 1
            except Exception as e:
                log.info("[config-apply] autolearn apply err: %r", e)
        log.info("[config-apply] autolearn applied=%s snapshot=%s", applied, snap)

    @property
    def ready(self): return True

    async def on_config_reloaded(self, name, payload):
        if name not in ("autolearn.yaml", "persona.md", "ai.yaml"):
            return
        await self._apply_all(name)

# Flexible setup (works on sync/async loaders)
async def setup(bot):
    await _safe_add_cog(bot, AutoLearnConfigListener(bot))

def setup(bot):
    _install_sync(bot, AutoLearnConfigListener)
