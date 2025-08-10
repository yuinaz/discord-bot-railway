COGS_LOADED = False

import pkgutil, importlib, asyncio

async def load_all_cogs(bot):
    base = 'modules.discord_bot.cogs'
    for _, modname, _ in pkgutil.iter_modules(__import__(base, fromlist=['']).__path__):
        try:
            await bot.load_extension(f'{base}.{modname}')
        except Exception as e:
            print('[cogs_loader] gagal load', modname, e)


\1
    try:
        bot.load_extension('modules.discord_bot.events.bot_online_announce')
    except Exception as e:
        print('[cogs_loader] failed to load bot_online_announce:', e)
    try:
        bot.load_extension('modules.discord_bot.cogs.moderation_test')
    except Exception as e:
        print('[cogs_loader] failed to load moderation_test:', e)
