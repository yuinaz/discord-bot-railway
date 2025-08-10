COGS_LOADED = False

import pkgutil
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

    base = 'discord_bot.cogs'
    # Auto-load all cogs under cogs/
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

    # Explicit must-have extensions (safe if already loaded)
    for ext in (
        'discord_bot.events.bot_online_announce',
        'discord_bot.cogs.moderation_test',
    ):
        try:
            await _maybe_await(bot.load_extension(ext))
            print('[cogs_loader] loaded', ext)
        except Exception as e:
            print('[cogs_loader] failed to load', ext, e)
