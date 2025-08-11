# Enhanced OCR helper (auto 2025-08-09T12:25:01.102837Z)
import os, io
from PIL import Image, ImageOps, ImageFilter, ImageEnhance
try:
    import pytesseract
except Exception:
    pytesseract = None

DEFAULT_LANG = os.getenv("OCR_LANG", "eng+ind")
def _load_ocr_words():
    # Merge ENV and config file
    words = [kw.strip().lower() for kw in os.getenv('OCR_BLOCKWORDS','').split(',') if kw.strip()]
    try:
        import json
        with open('config/ocr.json','r',encoding='utf-8') as f:
            arr = json.load(f).get('blockwords') or []
            words += [w.strip().lower() for w in arr if isinstance(w,str)]
    except Exception:
        pass
    # unique
    out = []
    for w in words:
        if w and w not in out:
            out.append(w)
    return out

\1
    \"mrbeast\", \"mr beast\", \"$2500\", \"2500\", \"win 2500\", \"usd 2500\", \"nitro free\", \"free nitro\", 
    "bonus", "promo code", "register", "claim", "casino", "slots",
    "usdt", "trx", "withdrawal", "withdraw", "deposit", "airdrop",
    "binance", "okx", "bybit", "kucoin", "gift", "reward", "free reward"
]
USE_SCAM_WORDS = (os.getenv("OCR_SCAM_STRICT","true").lower()=="true")
PROHIBITED_KEYWORDS = _load_ocr_words() + (SCAM_DEFAULT_WORDS if USE_SCAM_WORDS else [])

def _preprocess(img: Image.Image) -> Image.Image:
    g = ImageOps.grayscale(img)
    g = ImageEnhance.Contrast(g).enhance(1.8)
    g = g.filter(ImageFilter.SHARPEN)
    g = g.point(lambda p: 255 if p > 160 else 0)
    return g

def extract_text_from_image(image_bytes: bytes, lang: str = None) -> str:
    try:
        if not pytesseract:
            return ""
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        prep = _preprocess(img)
        text = pytesseract.image_to_string(prep, lang=(lang or DEFAULT_LANG))
        return (text or "").strip()
    except Exception:
        return ""

def _normalize_text(s: str) -> str:
    s = (s or "").lower()
    s = s.replace("\u200b","").replace("\u200c","").replace("\u200d","")
    s = " ".join(s.split())
    for a,b in {"0":"o","1":"i","3":"e","4":"a","5":"s","7":"t","@":"a","$":"s","!":"i"}.items():
        s = s.replace(a,b)
    return s

def contains_prohibited_text(text: str) -> bool:
    if not PROHIBITED_KEYWORDS:
        return False
    low = _normalize_text(text)
    return any(k in low for k in PROHIBITED_KEYWORDS)
