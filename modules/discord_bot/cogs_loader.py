PKG_ROOT = __name__.rsplit('.cogs_loader', 1)[0]
COGS_LOADED = False

import pkgutil
import importlib
import inspect

async def _maybe_await(x):
    if inspect.iscoroutine(x):
        return await x
    return x

async def load_all_cogs(bot):
    global COGS_LOADED
    if COGS_LOADED:
        return
    COGS_LOADED = True

    base = PKG_ROOT + '.cogs'
    # Auto-load all cogs under cogs/
    try:
        pkg = importlib.import_module(base)
        for _, modname, _ in pkgutil.iter_modules(pkg.__path__):
            ext = f"{base}.{modname}"
            try:
                await _maybe_await(bot.load_extension(ext))
                print('[cogs_loader] loaded', ext)
            except Exception as e:
                print('[cogs_loader] gagal load', modname, e)
    except Exception as e:
        print('[cogs_loader] gagal enumerasi cogs:', e)

    # Explicit must-have extensions (safe if already loaded)
    extras = (
        PKG_ROOT + '.events.bot_online_announce',
        PKG_ROOT + '.cogs.moderation_test',
    )
    for ext in extras:
        try:
            await _maybe_await(bot.load_extension(ext))
            print('[cogs_loader] loaded', ext)
        except Exception as e:
            print('[cogs_loader] failed to load', ext, e)
