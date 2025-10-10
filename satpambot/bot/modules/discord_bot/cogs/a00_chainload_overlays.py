# a00_chainload_overlays.py
# Ensure overlay modules are imported early by piggy-backing on the existing tuning overlay import path.
# No setup() needed.
try:
    import satpambot.bot.modules.discord_bot.cogs.a02_balanced_interval_overlay  # noqa: F401
except Exception as e:
    import logging; logging.getLogger(__name__).warning("[chainload] a02_balanced_interval_overlay not loaded: %r", e)
try:
    import satpambot.bot.modules.discord_bot.cogs.a03_public_gate_force_target  # noqa: F401
except Exception as e:
    import logging; logging.getLogger(__name__).warning("[chainload] a03_public_gate_force_target not loaded: %r", e)
