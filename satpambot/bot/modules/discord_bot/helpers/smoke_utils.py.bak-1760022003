
import logging
from types import SimpleNamespace

log = logging.getLogger(__name__)

class _DummyLoop:
    def create_task(self, coro):
        # swallow in smoke
        log.debug("[smoke] loop.create_task(%s) -> noop", getattr(coro, "__name__", coro))
        return None
    def call_soon(self, *a, **k):
        log.debug("[smoke] loop.call_soon -> noop")
        return None

class AppCmdTreeStub:
    """Minimal stub for discord.app_commands.CommandTree-like API."""
    def __init__(self, bot):
        self.bot = bot
    async def sync(self, *a, **k):
        return []
    def add_command(self, *a, **k):
        return None
    def add_check(self, *a, **k):
        return None
    def remove_check(self, *a, **k):
        return None
    def copy_global_to(self, *a, **k):
        return None
    def clear_commands(self, *a, **k):
        return None

class DummyBot:
    """Lightweight bot stub so cogs with side effects can import/setup in smoke tests.

    Goal: avoid AttributeError for common discord.py APIs. No real network calls.
    """
    def __init__(self):
        self._is_smoke_dummy = True
        self._cogs = {}
        self.loop = _DummyLoop()
        self.tree = AppCmdTreeStub(self)
        self.guilds = []
        self.user = SimpleNamespace(id=0, name="SMOKE", discriminator="0000")
        self._listeners = {}
        self._checks = []
        self._extensions = set()
        log.debug("[smoke] DummyBot ready")

    # --- discord.ext.commands-like APIs (subset) ---
    def add_cog(self, cog):
        name = getattr(cog, "qualified_name", cog.__class__.__name__)
        self._cogs[name] = cog
        if hasattr(cog, "cog_load"):
            try:
                cog.cog_load()
            except Exception as e:
                log.debug("[smoke] cog_load() ignored: %s", e)
        return cog

    def get_cog(self, name):
        return self._cogs.get(name)

    def add_listener(self, func, name=None):
        self._listeners.setdefault(name or func.__name__, []).append(func)

    def remove_listener(self, func, name=None):
        L = self._listeners.get(name or func.__name__, [])
        if func in L:
            L.remove(func)

    def add_check(self, func):
        self._checks.append(func)

    def remove_check(self, func):
        if func in self._checks:
            self._checks.remove(func)

    # extensions
    def load_extension(self, name):
        # no-op in smoke
        self._extensions.add(name)

    def unload_extension(self, name):
        self._extensions.discard(name)

    # misc
    async def wait_until_ready(self):
        return True

    def is_closed(self):
        return False

    def __getattr__(self, item):
        # Prevent AttributeError explosions for occasional attributes.
        # Return a benign callable/no-op for unknown attrs.
        def _noop(*a, **k):
            log.debug("[smoke] bot.%s called -> noop", item)
        return _noop
