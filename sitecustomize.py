
# SATPAMBOT sitecustomize: Discord intents hardening
# This is loaded automatically by Python at startup (if on sys.path).
import logging
try:
    import discord
    from discord.client import Client as _DClient
    _orig_init = _DClient.__init__

    def _patched_init(self, *args, **kwargs):
        intents = kwargs.get("intents")
        # If intents missing or wrong type, enforce safe defaults.
        if not isinstance(intents, discord.Intents):
            intents = discord.Intents.default()
            # Privileged / recommended flags (must also be enabled on Dev Portal):
            intents.message_content = True
            intents.members = True
            intents.presences = True
            # Commonly used flags in this repo:
            intents.reactions = True
            intents.guilds = True
            intents.messages = True
            intents.dm_messages = True
            # Newer discord.py merges emojis/stickers:
            try:
                intents.emojis_and_stickers = True
            except Exception:
                pass
            kwargs["intents"] = intents
        return _orig_init(self, *args, **kwargs)

    _DClient.__init__ = _patched_init
    logging.getLogger(__name__).info("[sitecustomize:intents] Default Discord intents enforced at Client.__init__")
except Exception as e:
    logging.getLogger(__name__).warning("[sitecustomize:intents] patch skipped: %s", e)
