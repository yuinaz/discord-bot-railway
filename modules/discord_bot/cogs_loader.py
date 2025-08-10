# modules/discord_bot/cogs_loader.py
COGS_LOADED = False

import pkgutil
import asyncio
import inspect

async def _maybe_await(result):
    if inspect.iscoroutine(result):
        return await result
    return result

async def load_all_cogs(bot):
    """
    Load semua cogs dari modules/discord_bot/cogs dan ekstra extension yang kita butuhkan.
    Idempotent: tidak akan double-load kalau sudah pernah dipanggil.
    """
    global COGS_LOADED
    if COGS_LOADED:
        return
    COGS_LOADED = True

    base = 'modules.discord_bot.cogs'
    # Enumerasi dan load semua cogs di folder cogs/
    try:
        pkg = __import__(base, fromlist=[''])
        for _, modname, _ in pkgutil.iter_modules(pkg.__path__):
            try:
                res = bot.load_extension(f'{base}.{modname}')
                await _maybe_await(res)
            except Exception as e:
                print('[cogs_loader] gagal load', modname, e)
    except Exception as e:
        print('[cogs_loader] gagal enumerasi cogs:', e)

    # Load cog/extension tambahan yang kita butuhkan secara eksplisit
    extras = (
        'modules.discord_bot.events.bot_online_announce',
        'modules.discord_bot.cogs.moderation_test',
    )
    for ext in extras:
        try:
            res = bot.load_extension(ext)
            await _maybe_await(res)
        except Exception as e:
            print(f'[cogs_loader] failed to load {ext}:', e)
