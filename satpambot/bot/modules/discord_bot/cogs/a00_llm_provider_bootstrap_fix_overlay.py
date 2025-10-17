import logging

async def setup(bot):
    log = logging.getLogger(__name__)
    try:
        from satpambot.bot.providers import LLM as _LLM
        bot.llm_ask = _LLM.ask  # prefer facade
        log.info('[llm-fix] bot.llm_ask wired via providers.LLM.ask')
        return
    except Exception as e:
        log.debug('[llm-fix] providers.LLM not available: %r', e)
    try:
        from satpambot.bot.llm_providers import ask as _ask
        bot.llm_ask = _ask
        log.info('[llm-fix] bot.llm_ask wired via llm_providers.ask (fallback)')
    except Exception as e2:
        log.warning('[llm-fix] failed wiring bot.llm_ask: %r', e2)
