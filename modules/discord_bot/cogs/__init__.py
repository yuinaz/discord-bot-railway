# modules/discord_bot/cogs_loader.py
COGS_LOADED = False

import pkgutil
import inspect

async def _maybe_await(x):
    if inspect.iscoroutine(x):
        return await x
    return x

async def load_all_cogs(bot):
    """
    Load semua cogs di modules/discord_bot/cogs + extension ekstra.
    Idempotent: tidak double-load.
    """
    global COGS_LOADED
    if COGS_LOADED:
        return
    COGS_LOADED = True

    base = 'modules.discord_bot.cogs'
    # ENUMERASI SEMUA COG DI FOLDER COGS/
    try:
        pkg = __import__(base, fromlist=[''])
        for _, modname, _ in pkgutil.iter_modules(pkg.__path__):
            try:
                await _maybe_await(bot.load_extension(f'{base}.{modname}'))
                print('[cogs_loader] loaded', f'{base}.{modname}')
            except Exception as e:
                print('[cogs_loader] gagal load', modname, e)
    except Exception as e:
        print('[cogs_loader] gagal enumerasi cogs:', e)

    # MUAT EKSTRA YANG KITA BUTUH
    for ext in (
        'modules.discord_bot.events.bot_online_announce',
        'modules.discord_bot.cogs.moderation_test',
    ):
        try:
            await _maybe_await(bot.load_extension(ext))
            print('[cogs_loader] loaded', ext)
        except Exception as e:
            print('[cogs_loader] failed to load', ext, e)
