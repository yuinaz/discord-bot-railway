PKG_ROOT = __name__.rsplit('.cogs_loader', 1)[0]
COGS_LOADED = False

import pkgutil, importlib, inspect

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

    # Wajib dimuat, tanpa konflik nama
    for ext in (
        PKG_ROOT + '.events.bot_online_announce',
        PKG_ROOT + '.cogs.moderation_extras',
    ):
        try:
            await _maybe_await(bot.load_extension(ext))
            print('[cogs_loader] loaded', ext)
        except Exception as e:
            print('[cogs_loader] failed to load', ext, e)

# ensure testban_sim loaded last
async def _load_testban_sim(bot):
    try:
        await bot.load_extension(__name__.rsplit('.cogs_loader',1)[0] + '.cogs.testban_sim')
    except Exception as e:
        print('[cogs_loader] testban_sim load fail', e)

async def load_all_cogs(bot):
    try:
        await _load_testban_sim(bot)
    except Exception:
        pass
