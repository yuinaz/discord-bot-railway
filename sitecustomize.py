# -*- coding: utf-8 -*-
"""
sitecustomize: runtime shims & small boot patches.
This file is auto-loaded by Python if located on sys.path root.

Adds a compatibility shim so legacy cogs that do
`from satpambot.bot.utils.embed_scribe import EmbedScribe`
continue to work even if the module migrated to function-style API.
"""
import importlib

try:
    m = importlib.import_module("satpambot.bot.utils.embed_scribe")
    if not hasattr(m, "EmbedScribe"):
        # Create a light wrapper that delegates to module-level API.
        class EmbedScribe:
            @staticmethod
            async def upsert(bot, channel, embed, key=None, pin=True, thread_name=None, **kwargs):
                # Prefer new API if present
                up = getattr(m, "upsert", None)
                if up:
                    return await up(bot, channel, embed, key=key, pin=pin, thread_name=thread_name, **kwargs)
                # Fallback: try write_embed if provided by older versions
                we = getattr(m, "write_embed", None)
                if we:
                    return await we(bot, channel, embed, key=key, pin=pin, thread_name=thread_name, **kwargs)
                raise RuntimeError("No upsert/write_embed available in embed_scribe")

            # Optional helpers some cogs might call; no-op if absent
            @staticmethod
            async def janitor(channel, key=None, **kwargs):
                j = getattr(m, "janitor", None)
                if j:
                    return await j(channel, key=key, **kwargs)
                return False

        setattr(m, "EmbedScribe", EmbedScribe)
except Exception:
    # Never block boot on shim errors
    pass
