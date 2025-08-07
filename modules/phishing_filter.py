from flask import Blueprint
phishing_filter_bp = Blueprint("phishing_filter", __name__)

import re, tldextract, aiohttp, os, asyncio, hashlib
from dotenv import load_dotenv
from collections import defaultdict

load_dotenv()

OCR_API_KEY = os.getenv("OCR_API_KEY", "helloworld")  # Ganti dengan key kamu

# === Keyword dan konfigurasi ===
STATIC_KEYWORDS = [
    "mrbeast", "free nitro", "claim nitro", "steam nitro",
    "mr beast", "nitro generator", "airdrop", "event nitro"
]

def load_list(file):
    try:
        with open(file) as f:
            return [line.strip().lower() for line in f if line.strip()]
    except:
        return []

def load_hashes(file):
    try:
        with open(file) as f:
            return set(line.strip().lower() for line in f if line.strip())
    except:
        return set()

WHITELISTED_DOMAINS = load_list("whitelist.txt")
BLACKLISTED_KEYWORDS = load_list("blacklist.txt")
BLACKLISTED_IMAGE_HASHES = load_hashes("blacklist_image_hashes.txt")

def extract_root_domain(url):
    ext = tldextract.extract(url)
    return f"{ext.domain}.{ext.suffix}"

url_pattern = re.compile(r'https?://\S+')

def is_whitelisted(content):
    return any(extract_root_domain(url) in WHITELISTED_DOMAINS for url in url_pattern.findall(content.lower()))

# === Cache OCR hasil berdasarkan MD5 hash ===
ocr_cache = defaultdict(str)

async def scan_image_for_phishing(message):
    for att in message.attachments:
        if any(att.filename.lower().endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".webp"]):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(att.url) as resp:
                        image_bytes = await resp.read()
                        image_hash = hashlib.md5(image_bytes).hexdigest()

                        # 🔒 Cek apakah hash gambar masuk blacklist
                        if image_hash in BLACKLISTED_IMAGE_HASHES:
                            print(f"[⚠️] Gambar terdeteksi dari blacklist hash: {image_hash}")
                            return True, "[TERDETEKSI HASH PHISHING]"

                        # 📥 Cek OCR cache
                        if image_hash in ocr_cache:
                            text = ocr_cache[image_hash]
                        else:
                            text = await extract_text_from_bytes(image_bytes)
                            ocr_cache[image_hash] = text

                        if not text:
                            continue

                        text = text.lower()
                        if any(k in text for k in STATIC_KEYWORDS + BLACKLISTED_KEYWORDS):
                            return True, text
            except Exception as e:
                print(f"OCR scan failed: {e}")
    return False, ""

async def extract_text_from_bytes(image_bytes):
    url = "https://api.ocr.space/parse/image"
    headers = {"apikey": OCR_API_KEY}
    data = aiohttp.FormData()
    data.add_field("language", "eng")
    data.add_field("isOverlayRequired", "false")
    data.add_field("file", image_bytes, filename="image.jpg", content_type="image/jpeg")

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, data=data) as resp:
            result = await resp.json()
            parsed = result.get("ParsedResults", [])
            if parsed and "ParsedText" in parsed[0]:
                return parsed[0]["ParsedText"]
            return ""
