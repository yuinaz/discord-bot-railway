COGS_LOADED = False

import pkgutil, importlib, asyncio

async def load_all_cogs(bot):
    base = 'modules.discord_bot.cogs'
    for _, modname, _ in pkgutil.iter_modules(__import__(base, fromlist=['']).__path__):
        try:
            await bot.load_extension(f'{base}.{modname}')
        except Exception as e:
            print('[cogs_loader] gagal load', modname, e)
