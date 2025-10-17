
# Ensures progress embed never throws 'object NoneType can't be used in await expression'
# Works across restarts by patching at import time AND on_ready.
import inspect, sys, importlib
from discord.ext import commands

TARGETS = [
    "satpambot.bot.modules.discord_bot.helpers.embed_scribe",
    "satpambot.bot.modules.discord_bot.cogs.embed_scribe",
]

def _make_awaitable(value):
    async def _immediate():
        return value
    return _immediate()

def _patch_module(mod):
    EmbedScribe = getattr(mod, "EmbedScribe", None)
    if not EmbedScribe:
        return False
    upsert = getattr(EmbedScribe, "upsert", None)
    if not upsert or getattr(upsert, "__safeawait_patched__", False):
        return False

    orig = upsert

    async def _wrapped(self, *args, **kwargs):
        try:
            res = orig(self, *args, **kwargs)
            if inspect.isawaitable(res):
                return await res
            # Always return an awaitable so caller's `await` is safe
            return await _make_awaitable(res)
        except Exception as e:
            print(f"[progress_embed_bootstrap] upsert error: {e!r}")
            return None

    try:
        _wrapped.__name__ = getattr(orig, "__name__", "_wrapped_upsert")
    except Exception:
        pass
    setattr(_wrapped, "__safeawait_patched__", True)
    setattr(EmbedScribe, "upsert", _wrapped)
    print(f"[progress_embed_bootstrap] patched: {mod.__name__}.EmbedScribe.upsert")
    return True

def patch_now():
    patched_any = False
    # Try already-imported modules
    for name in list(sys.modules.keys()):
        if any(name == t or name.startswith(t + ".") for t in TARGETS):
            try:
                patched_any |= _patch_module(sys.modules[name])
            except Exception as e:
                print(f"[progress_embed_bootstrap] patch scan error for {name}: {e!r}")
    # Try importing targets by name
    for t in TARGETS:
        try:
            mod = importlib.import_module(t)
            patched_any |= _patch_module(mod)
        except Exception:
            continue
    return patched_any

# Patch immediately at import time (before other cogs run if loader uses lexicographic order)
patch_now()

class ProgressEmbedSafeAwaitBootstrap(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        # Re-patch on ready (in case modules loaded after bootstrap import)
        if patch_now():
            print("[progress_embed_bootstrap] re-patched on_ready")

async def setup(bot):
    await bot.add_cog(ProgressEmbedSafeAwaitBootstrap(bot))
    print("[progress_embed_bootstrap] overlay loaded")
