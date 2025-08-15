
from __future__ import annotations
"""
ban_poster.py — async & cached poster generator for SatpamBot
- Full poster rendering done in a background thread (asyncio.to_thread)
- Fonts and asset path cached globally
- Small icon mode for ultra-lightweight embeds
ENV:
  POSTER_ENABLED=1                 # 0 to disable any poster/icon
  POSTER_SIMPLE=0                  # 1 to skip rendering, send static image
  POSTER_ICON_MODE=0               # 1 to send small icon (thumbnail) instead of big poster
  POSTER_IMAGE_NAME=fibilaugh.png  # file under ./assets for big poster
  POSTER_ICON_NAME=fibi_icon.png   # file under ./assets for small icon (png)
"""
import os
from functools import lru_cache
from io import BytesIO
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter
    PIL_OK = True
except Exception:
    PIL_OK = False

DEFAULT_POSTER = "fibilaugh.png"
DEFAULT_ICON   = "fibi_icon.png"

@lru_cache(maxsize=None)
def poster_enabled() -> bool:
    return os.getenv("POSTER_ENABLED", "1") != "0"

@lru_cache(maxsize=None)
def poster_simple() -> bool:
    return os.getenv("POSTER_SIMPLE", "0") != "0"

@lru_cache(maxsize=None)
def poster_icon_mode() -> bool:
    return os.getenv("POSTER_ICON_MODE", "0") != "0"

@lru_cache(maxsize=None)
def _font(size: int, bold: bool=False):
    try:
        return ImageFont.truetype("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf", size)
    except Exception:
        return ImageFont.load_default()

def _find_under_assets(name: str) -> Path | None:
    roots = [Path.cwd()]
    here = Path(__file__).resolve()
    for i in range(1,7):
        roots.append(here.parents[i-1])
    for r in roots:
        cand = r / "assets" / name
        if cand.exists():
            return cand
    return None

@lru_cache(maxsize=None)
def _poster_path() -> Path | None:
    return _find_under_assets(os.getenv("POSTER_IMAGE_NAME", DEFAULT_POSTER))

@lru_cache(maxsize=None)
def _icon_path() -> Path | None:
    # prefer explicit icon name, fallback to poster if present
    p = _find_under_assets(os.getenv("POSTER_ICON_NAME", DEFAULT_ICON))
    if p:
        return p
    return _poster_path()

def _render_sync(username: str, mode: str="ban") -> BytesIO | None:
    if not PIL_OK:
        return None
    src = _poster_path()
    if not src or not src.exists():
        return None
    W, H = 1200, 628
    img = Image.open(src).convert("RGB")
    bg = ImageOps.fit(img, (W, H), method=Image.LANCZOS).filter(ImageFilter.GaussianBlur(18)).convert("RGBA")
    bg.alpha_composite(Image.new("RGBA", (W, H), (0,0,0,90)))
    iw, ih = img.size; sc = min(W/iw, H/ih)
    fg = img.resize((max(1,int(iw*sc)), max(1,int(ih*sc))), Image.LANCZOS)
    card = bg.copy(); card.paste(fg, ((W-fg.width)//2, (H-fg.height)//2))
    draw = ImageDraw.Draw(card)
    tF, bF, nF = _font(68, True), _font(36), _font(30)
    title = "Ban oleh SatpamBot" if mode=="ban" else "Simulasi Ban oleh SatpamBot"
    body  = f"{username} terdeteksi mengirim pesan mencurigakan."
    note  = "(Penindakan otomatis oleh SatpamBot.)" if mode=="ban" else "(Pesan ini hanya simulasi.)"
    chip = "Ban otomatis" if mode=="ban" else "Simulasi testban"
    tw = int(draw.textlength(chip, font=bF) + 48)
    draw.rounded_rectangle((40,40,40+tw,96), radius=18, fill=(239,68,68,230) if mode=="ban" else (34,197,94,230))
    draw.text((64,56-bF.size/2), chip, font=bF, fill="white")
    def wrap(t, f, maxw):
        words, line, out = t.split(), "", []
        for w in words:
            test = (line+" "+w).strip()
            if draw.textlength(test, font=f) <= maxw or not line: line = test
            else: out.append(line); line = w
        if line: out.append(line)
        return out or [""]
    x, y, maxw = 40, 140, W-80
    for ln in wrap(title, tF, maxw):
        draw.text((x,y), ln, font=tF, fill="white", stroke_width=3, stroke_fill=(0,0,0,180)); y += tF.size+10
    for ln in wrap(body, bF, maxw):
        draw.text((x,y), ln, font=bF, fill="white", stroke_width=2, stroke_fill=(0,0,0,160)); y += bF.size+8
    for ln in wrap(note, nF, maxw):
        draw.text((x,y), ln, font=nF, fill=(235,235,235,255), stroke_width=2, stroke_fill=(0,0,0,140)); y += nF.size+6
    buf = BytesIO(); card.convert("RGB").save(buf, "PNG", optimize=True); buf.seek(0)
    return buf

async def render_to_buffer_async(username: str, mode: str="ban"):
    import asyncio
    if not poster_enabled() or poster_icon_mode():
        return None
    if poster_simple():
        # return the raw static image file if exists
        p = _poster_path()
        if p and p.exists():
            with open(p, "rb") as f:
                data = f.read()
            return BytesIO(data)
        return None
    return await asyncio.to_thread(_render_sync, username, mode)

def load_icon_bytes(size: int = 192) -> BytesIO | None:
    """Return small square PNG for thumbnail mode."""
    if not poster_enabled() or not poster_icon_mode() or not PIL_OK:
        return None
    p = _icon_path()
    if not p or not p.exists():
        return None
    im = Image.open(p).convert("RGBA")
    im = ImageOps.contain(im, (size, size), Image.LANCZOS)
    buf = BytesIO()
    im.save(buf, "PNG", optimize=True)
    buf.seek(0)
    return buf
