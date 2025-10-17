import os, logging

async def setup(bot):
    log = logging.getLogger(__name__)
    try:
        from satpambot.bot.modules.discord_bot.cogs import a00_persona_overlay as m
        PersonaOverlay = getattr(m, 'PersonaOverlay', None)
        if PersonaOverlay and not hasattr(PersonaOverlay, 'get_active_persona'):
            def _get_active_persona(self):
                # fallback jika overlay tidak expose method asli
                return os.getenv('PERSONA_ACTIVE_NAME', 'default')
            setattr(PersonaOverlay, 'get_active_persona', _get_active_persona)
            log.info('[persona-guard] injected PersonaOverlay.get_active_persona()')
        else:
            log.debug('[persona-guard] PersonaOverlay OK or not present')
    except Exception as e:
        log.debug('[persona-guard] skip: %r', e)
