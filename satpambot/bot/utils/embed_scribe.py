
"""
Safe, minimal embed scribe used for smoke tests and headless envs.
Provides a tiny API compatible with common usages in the repo.
"""
from typing import List, Tuple, Optional

try:
    import discord  # type: ignore
except Exception:  # pragma: no cover
    discord = None  # fallback for environments without discord

class EmbedScribe:
    def __init__(self, title: Optional[str] = None, description: Optional[str] = None):
        self.title = title or ""
        self.description = description or ""
        self._fields: List[Tuple[str, str, bool]] = []
        self._footer: Optional[str] = None

    def set_title(self, title: str):
        self.title = title or ""
        return self

    def set_description(self, description: str):
        self.description = description or ""
        return self

    def add_field(self, name: str, value: str, inline: bool = False):
        # Avoid None values in smoke env
        name = "" if name is None else str(name)
        value = "" if value is None else str(value)
        self._fields.append((name, value, bool(inline)))
        return self

    def set_footer(self, text: str):
        self._footer = text or ""
        return self

    def as_embed(self):
        # If discord.Embed is available, build a real embed.
        if discord is not None:
            emb = discord.Embed(title=self.title or None, description=self.description or None)
            for n, v, inline in self._fields:
                # Discord requires non-empty fields; ensure minimal placeholders
                emb.add_field(name=n or "\u200b", value=v or "\u200b", inline=inline)
            if self._footer:
                emb.set_footer(text=self._footer)
            return emb
        # Fallback: dict-like object for environments without discord
        return {
            "title": self.title,
            "description": self.description,
            "fields": [{"name": n, "value": v, "inline": i} for n, v, i in self._fields],
            "footer": self._footer,
        }

# Convenience helpers that some cogs may import
def make_embed(title: str = "", description: str = ""):
    return EmbedScribe(title, description).as_embed()

def scribe(title: str = "", description: str = "") -> EmbedScribe:
    return EmbedScribe(title, description)
