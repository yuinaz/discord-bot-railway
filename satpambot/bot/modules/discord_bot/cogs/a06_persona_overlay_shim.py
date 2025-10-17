
"""
Persona overlay compatibility shim.
- Adds PersonaOverlay.get_active_persona() if missing (back-compat).
Safe to load multiple times; idempotent.
"""
from __future__ import annotations
import logging

log = logging.getLogger(__name__)

async def setup(bot):
    # Attempt to find PersonaOverlay in likely modules
    targets = [
        "satpambot.bot.modules.discord_bot.cogs.a00_persona_overlay",
        "satpambot.bot.modules.discord_bot.cogs.a06_persona_overlay_guard",
        "satpambot.bot.modules.discord_bot.cogs.personality_governor",
    ]
    PersonaOverlay = None
    for mname in targets:
        try:
            mod = __import__(mname, fromlist=["*"])
            PersonaOverlay = getattr(mod, "PersonaOverlay", None) or getattr(mod, "Persona", None)
            if PersonaOverlay:
                break
        except Exception:
            continue

    if not PersonaOverlay:
        log.warning("[persona-shim] PersonaOverlay class not found; skipping")
        return

    if getattr(PersonaOverlay, "__get_active_persona_shim__", False):
        log.info("[persona-shim] already patched")
        return

    def get_active_persona(self):
        # try common attribute names
        return getattr(self, "active_persona", None) or getattr(self, "persona", "default")

    setattr(PersonaOverlay, "get_active_persona", get_active_persona)
    setattr(PersonaOverlay, "__get_active_persona_shim__", True)
    log.info("[persona-shim] PersonaOverlay.get_active_persona added")
