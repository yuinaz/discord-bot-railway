
import os
import logging
from discord.ext import commands

log = logging.getLogger(__name__)
_QNA_ID = int(os.getenv("QNA_CHANNEL_ID", "1426571542627614772"))

class QNAAllowShim(commands.Cog):
    """Force allow messaging in QNA channel even if public gate says otherwise."""
    def __init__(self, bot):
        self.bot = bot
        # monkey patch PublicChatGate check if present
        try:
            from satpambot.bot.modules.discord_bot.cogs.public_chat_gate import PublicChatGate  # type: ignore
            gate = None
            for cog in bot.cogs.values():
                if isinstance(cog, PublicChatGate):
                    gate = cog
                    break
            if gate:
                orig = getattr(gate, "check_message_allowed", None)
                if callable(orig):
                    async def patched(message):
                        ch_id = getattr(message.channel, "id", None)
                        if ch_id == _QNA_ID:
                            return True
                        return await orig(message)
                    setattr(gate, "check_message_allowed", patched)
                    log.info("[qna_allow] public_chat_gate patched for QNA=%s", _QNA_ID)
        except Exception as e:
            log.info("[qna_allow] gate not found or patch failed: %r", e)

async def setup(bot):
    await bot.add_cog(QNAAllowShim(bot))

def setup_legacy(bot):
    bot.add_cog(QNAAllowShim(bot))
