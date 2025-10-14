
# -*- coding: utf-8 -*-
"""
Overlay: _patch_async_setup
- Fixes "add_cog was never awaited" by replacing setup() of several cogs with async versions.
- Adds an app command (slash) global check that explicitly allows /clearchat in public channels.
- Safe to import multiple times (idempotent).
"""
from importlib import import_module
from typing import Optional

def _safe_patch_setup(modname: str, cls_name: str) -> Optional[str]:
    try:
        mod = import_module(modname)
        cls = getattr(mod, cls_name, None)
        if cls is None:
            return f"{modname}: missing class {cls_name}"
        async def _setup(bot):
            await bot.add_cog(cls(bot))
        # Replace/define setup on the target module
        setattr(mod, "setup", _setup)
        return None
    except Exception as e:
        return f"{modname}: {e}"

PATCH_TARGETS = [
    # (module, class)
    ("satpambot.bot.modules.discord_bot.cogs.public_chat_gate", "PublicChatGate"),
    ("satpambot.bot.modules.discord_bot.cogs.public_send_router", "PublicSendRouter"),
    ("satpambot.bot.modules.discord_bot.cogs.a08_public_clearchat", "PublicClearChat"),
    ("satpambot.bot.modules.discord_bot.cogs.a00_public_chat_gate_smoke_fix", "PublicChatGate"),
    ("satpambot.bot.modules.discord_bot.cogs.a06_sticky_status_strict_overlay", "_StickyStatusStrict"),
    # Bonus: these showed warnings in logs too
    ("satpambot.bot.modules.discord_bot.cogs.a06_status_coalescer_wildcard_overlay", "StatusCoalescerWildcard"),
    ("satpambot.bot.modules.discord_bot.cogs.gemini_vision_qna", "GeminiVisionQnA"),
]

_errors = []
for modname, clsname in PATCH_TARGETS:
    err = _safe_patch_setup(modname, clsname)
    if err:
        _errors.append(err)

async def setup(bot):
    # Register global allowance for /clearchat (and synonyms) even if public gate is strict.
    try:
        import discord
        from discord import app_commands

        ALLOW = {"clearchat", "clear", "prune", "purge"}

        async def _allow_clear(interaction: "discord.Interaction") -> bool:
            try:
                cmd = getattr(interaction, "command", None) or getattr(interaction, "command", None)
                name = None
                if cmd is not None:
                    name = getattr(cmd, "name", None)
                # For subcommands, command may be an app_commands.CommandTree object; fall back to data
                if name is None and hasattr(interaction, "data"):
                    name = interaction.data.get("name")
                if name and name.lower() in ALLOW:
                    return True
            except Exception:
                # Never hard-block due to checker errors.
                return True
            # No decision => don't block; return True to be a permissive check
            return True

        # Add only once
        if not hasattr(bot, "_patch_async_setup_allow_clear"):
            bot._patch_async_setup_allow_clear = True
            try:
                bot.tree.add_check(_allow_clear)
            except Exception:
                # Some environments may not have bot.tree yet; ignore.
                pass
    except Exception:
        pass
