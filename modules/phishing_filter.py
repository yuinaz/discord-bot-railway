from flask import Blueprint
phishing_filter_bp = Blueprint("phishing_filter", __name__)

import re, tldextract, aiohttp, os
from dotenv import load_dotenv

load_dotenv()

OCR_API_KEY = os.getenv("OCR_API_KEY", "helloworld")  # Ganti dengan key kamu

# === Keyword dan konfigurasi ===
STATIC_KEYWORDS = ["mrbeast", "free nitro", "claim nitro", "steam nitro", "mr beast", "nitro generator", "airdrop", "event nitro"]

def load_list(file):
    try:
        with open(file) as f:
            return [line.strip().lower() for line in f if line.strip()]
    except:
        return []

WHITELISTED_DOMAINS = load_list("whitelist.txt")
BLACKLISTED_KEYWORDS = load_list("blacklist.txt")

def extract_root_domain(url):
    ext = tldextract.extract(url)
    return f"{ext.domain}.{ext.suffix}"

url_pattern = re.compile(r'https?://\S+')

def is_whitelisted(content):
    return any(extract_root_domain(url) in WHITELISTED_DOMAINS for url in url_pattern.findall(content.lower()))

# === Gunakan OCR.space API ===
async def scan_image_for_phishing(message):
    for att in message.attachments:
        if any(att.filename.lower().endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".webp"]):
            try:
                text = await extract_text_from_image(att.url)
                if any(k in text.lower() for k in STATIC_KEYWORDS + BLACKLISTED_KEYWORDS):
                    return True, text
            except Exception as e:
                print("OCR API error:", e)
    return False, ""

async def extract_text_from_image(image_url):
    url = "https://api.ocr.space/parse/image"
    headers = {"apikey": OCR_API_KEY}
    data = {
        "url": image_url,
        "language": "eng",
        "isOverlayRequired": False
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, data=data) as resp:
            result = await resp.json()
            parsed = result.get("ParsedResults", [])
            if parsed and "ParsedText" in parsed[0]:
                return parsed[0]["ParsedText"]
            return ""
