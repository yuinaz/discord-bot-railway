from .ban_embed import build_ban_embed

async def send_ban_poster(channel, target, *, reason=None, simulated=False, **kw):
    return await channel.send(embed=build_ban_embed(target, reason=reason, simulated=simulated))

# Back-compat aliases
async def post_ban_poster(channel, target, **kw): return await send_ban_poster(channel, target, **kw)
async def send_poster(channel, target, **kw):     return await send_ban_poster(channel, target, **kw)
async def post_ban(channel, target, **kw):        return await send_ban_poster(channel, target, **kw)

# No image generation in lightweight mode
def build_poster(*a, **k): return None
def generate_ban_poster(*a, **k): return None
def render_ban_image(*a, **k): return None
def create_poster(*a, **k): return None
