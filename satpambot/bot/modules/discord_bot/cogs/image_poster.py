
from io import BytesIO
from pathlib import Path
from PIL import Image, ImageOps, ImageDraw, ImageFont

def _load_font(size:int, weight:str="regular"):
    # Try DejaVuSans (bundled with Pillow) as a reliable default
    try:
        if weight == "bold":
            return ImageFont.truetype("DejaVuSans-Bold.ttf", size)
        return ImageFont.truetype("DejaVuSans.ttf", size)
    except Exception:
        return ImageFont.load_default()

def find_fibi_asset() -> Path:
    # search common locations relative to this file and cwd
    candidates = [
        Path(__file__).resolve().parent.parent / "assets" / "fibilaugh.png",
        Path(__file__).resolve().parent.parent / "assets" / "fibi.png",
        Path.cwd() / "assets" / "fibilaugh.png",
        Path.cwd() / "assets" / "fibi.png",
    ]
    for p in candidates:
        if p.exists():
            return p
    # fallback: take first png in assets
    assets_dir = Path(__file__).resolve().parent.parent / "assets"
    if assets_dir.exists():
        for p in assets_dir.glob("*.png"):
            return p
    raise FileNotFoundError("Fibi asset not found. Put an image in ./assets/fibilaugh.png")

def build_poster(username:str, mode:str="testban", title_override:str|None=None) -> BytesIO:
    """Return a PNG buffer for the poster with Fibi full background."""
    W, H = 1200, 628
    bg_path = find_fibi_asset()
    img = Image.open(bg_path).convert("RGB")
    canvas = ImageOps.fit(img, (W, H), method=Image.LANCZOS, centering=(0.5, 0.4))
    canvas = canvas.convert("RGBA")
    # darken a bit for readability
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 110))
    canvas = Image.alpha_composite(canvas, overlay)

    draw = ImageDraw.Draw(canvas)
    title_font = _load_font(68, "bold")
    body_font = _load_font(34, "regular")

    title = title_override or ("Simulasi Ban oleh SatpamBot" if mode == "testban" else "Ban oleh SatpamBot")
    body  = f"{username} terdeteksi mengirim pesan mencurigakan."
    note  = "(Pesan ini hanya simulasi untuk pengujian.)" if mode == "testban" else "(Penindakan otomatis oleh SatpamBot.)"
    chip  = "Simulasi testban" if mode == "testban" else "Ban otomatis"

    # chip
    chip_w = int(draw.textlength(chip, font=body_font) + 48)
    chip_h = 56
    draw.rounded_rectangle((40, 40, 40+chip_w, 40+chip_h), radius=18, fill=(34,197,94,230) if mode=="testban" else (239,68,68,230))
    draw.text((40+24, 40+chip_h/2-body_font.size/2), chip, font=body_font, fill="white")

    # title and texts
    draw.text((40, 140), title, font=title_font, fill="white")
    draw.text((40, 140+84), body, font=body_font, fill="white")
    draw.text((40, 140+84+46), note, font=body_font, fill=(235,235,235,255))

    out = BytesIO()
    canvas.convert("RGB").save(out, format="PNG", optimize=True)
    out.seek(0)
    return out


# optional: no-op setup so loader won't warn
from discord.ext import commands as _commands_setup_patch
async def setup(bot: _commands_setup_patch.Bot):
    return
