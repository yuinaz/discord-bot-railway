
import asyncio
import logging
import types

log = logging.getLogger(__name__)

class _DummyTree:
    def add_command(self, *a, **k):
        return None
    async def sync(self, *a, **k):
        return []

class DummyBot:
    """
    Minimal async-compatible shim of discord.ext.commands.Bot for offline smoke tests.
    Provides async add_cog/load_extension and basic attributes used by our cogs.
    """
    def __init__(self):
        self._cogs = {}
        self.loop = asyncio.get_event_loop()
        self.tree = _DummyTree()
        self.guilds = []   # offline: empty; cogs should tolerate
        self.user = types.SimpleNamespace(id=0, name="DummyBot")
        self._checks = []
        self._extensions = set()
        # Common attributes some cogs read
        self.latency = 0.0
        self._connection = types.SimpleNamespace(is_bot=True)

    # ---- discord.py-ish bits ----
    async def add_cog(self, cog):
        name = getattr(cog, "__class__", type("X", (), {})).__name__
        self._cogs[name] = cog
        log.debug("[DummyBot] add_cog %s", name)
        return None

    def get_cog(self, name):
        return self._cogs.get(name)

    async def wait_until_ready(self):
        return None

    def add_check(self, func):
        self._checks.append(func)
        return func

    async def load_extension(self, ext_name):
        # In offline mode we just remember it; real loading is handled by the smoke runner via importlib
        self._extensions.add(ext_name)
        log.debug("[DummyBot] load_extension %s", ext_name)
        return None

    # Slash-tree conveniences sometimes accessed
    async def sync_commands(self):
        return await self.tree.sync()

    # Utilities often probed by helpers
    def is_closed(self):
        return False

    def get_channel(self, channel_id):
        # Offline: return a dummy object with minimal API
        return types.SimpleNamespace(id=channel_id, name=f"channel-{channel_id}")

    def dispatch(self, *a, **k):
        # no-op
        return None

    # Some cogs use 'loop.create_task'
    def create_task(self, coro):
        return self.loop.create_task(coro)

class DedupLogHandler(logging.Handler):
    """
    Collapses identical log messages; keeps counters.
    """
    def __init__(self):
        super().__init__()
        self.counts = {}

    def emit(self, record):
        key = (record.name, record.levelno, record.getMessage())
        self.counts[key] = self.counts.get(key, 0) + 1

def install_dedup_logging(level=logging.INFO):
    root = logging.getLogger()
    root.setLevel(level)
    # keep existing console handlers but add dedup aggregator
    agg = DedupLogHandler()
    root.addHandler(agg)
    return agg
