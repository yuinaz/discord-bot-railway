# Embed-only replacement for heavy image poster
import os
from discord import Embed, Colour
from .ban_embed import build_ban_embed

# Common entry points (alias ke embed sender):
async def send_ban_poster(channel, target, *, reason=None, simulated=False, **kwargs):
    return await channel.send(embed=build_ban_embed(target, reason=reason, simulated=simulated))
async def post_ban_poster(channel, target, **kw): return await send_ban_poster(channel, target, **kw)
async def send_poster(channel, target, **kw):     return await send_ban_poster(channel, target, **kw)
async def post_ban(channel, target, **kw):        return await send_ban_poster(channel, target, **kw)

# If any code tries to "generate image", return None to keep flow safe
def build_poster(*a, **k): return None
def generate_ban_poster(*a, **k): return None
def render_ban_image(*a, **k): return None
def create_poster(*a, **k): return None
