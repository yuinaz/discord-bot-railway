import logging
log = logging.getLogger(__name__)
try:
    from satpambot.bot.utils.embed_scribe import EmbedScribe  # type: ignore
except Exception as e:
    EmbedScribe = None  # type: ignore
    log.exception("[scribe_compat] cannot import EmbedScribe: %s", e)

async def setup(bot):
    if EmbedScribe is None:
        return
    if getattr(EmbedScribe, "upsert", None):
        log.info("[scribe_compat] upsert already exists")
        return
    def _upsert(self, channel, title: str, body: str, **kwargs):
        # Fallback behaviour: just post a new embed (keeps smoke happy)
        return self.post(channel, title, body, **kwargs)
    setattr(EmbedScribe, "upsert", _upsert)
    log.info("[scribe_compat] injecting EmbedScribe.upsert")
