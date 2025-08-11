PKG_ROOT = __name__.rsplit('.cogs_loader', 1)[0]
COGS_LOADED=False

async def load_cogs(bot):
    global COGS_LOADED
    if COGS_LOADED: return
    COGS_LOADED = True
    import pkgutil, importlib
    base = PKG_ROOT + '.cogs'
    try:
        spec = importlib.util.find_spec(base)
        if spec and spec.submodule_search_locations:
            for _, name, _ in pkgutil.iter_modules(list(spec.submodule_search_locations)):
                mod = base + '.' + name
                try:
                    m = importlib.import_module(mod)
                    if hasattr(m, 'setup'):
                        await bot.load_extension(mod)
                except Exception as e:
                    print('[cogs_loader] failed autoload', mod, e)
    except Exception as e:
        print('[cogs_loader] autoload error', e)

    # ensure critical cogs loaded
    for mod in (base + '.health', base + '.testban_sim', base + '.prefix_guard', base + '.anti_invite_autoban'):
        try:
            await bot.load_extension(mod)
        except Exception as e:
            print('[cogs_loader] force-load failed', mod, e)
