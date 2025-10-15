import inspect

async def safe_add_cog(bot, cog):
    """Await add_cog if the discord.py version makes it a coroutine.
    Idempotent: if add_cog returns a coroutine, await it; otherwise do nothing.
    """
    ret = bot.add_cog(cog)
    if inspect.iscoroutine(ret):
        return await ret
    return ret
