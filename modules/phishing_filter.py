from flask import Blueprint
phishing_filter_bp = Blueprint("phishing_filter", __name__)

import re
import tldextract
import aiohttp
import os
import hashlib
import json
from dotenv import load_dotenv
from collections import defaultdict

# === Load variabel dari .env ===
load_dotenv()
OCR_API_KEY = os.getenv("OCR_API_KEY", "helloworld")  # Ganti sesuai kebutuhan

# === Daftar kata dan konfigurasi ===
STATIC_KEYWORDS = [
    "mrbeast", "free nitro", "claim nitro", "steam nitro",
    "mr beast", "nitro generator", "airdrop", "event nitro"
]

# === Fungsi: Load daftar list/hash ===
def load_list(file):
    try:
        with open(file, encoding="utf-8") as f:
            return [line.strip().lower() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"⚠️ File tidak ditemukan: {file}")
        return []

def load_hashes(file):
    try:
        with open(file, encoding="utf-8") as f:
            return set(line.strip().lower() for line in f if line.strip())
    except FileNotFoundError:
        print(f"⚠️ File tidak ditemukan: {file}")
        return set()

# === Load whitelist & blacklist ===
WHITELISTED_DOMAINS = load_list("whitelist.txt")
BLACKLISTED_KEYWORDS = load_list("blacklist.txt")
BLACKLISTED_IMAGE_HASHES = load_hashes("blacklist_image_hashes.txt")

# === Ekstrak domain dari URL ===
url_pattern = re.compile(r'https?://\S+')

def extract_root_domain(url):
    ext = tldextract.extract(url)
    return f"{ext.domain}.{ext.suffix}"

def is_whitelisted(content):
    return any(extract_root_domain(url) in WHITELISTED_DOMAINS for url in url_pattern.findall(content.lower()))

# === OCR Cache ke file ===
OCR_CACHE_FILE = "ocr_cache.json"

def load_ocr_cache():
    try:
        if os.path.exists(OCR_CACHE_FILE):
            with open(OCR_CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return defaultdict(str, data)
    except Exception as e:
        print(f"❌ Gagal load ocr_cache: {e}")
    return defaultdict(str)

def save_ocr_cache():
    try:
        with open(OCR_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(ocr_cache, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"❌ Gagal simpan ocr_cache: {e}")

# === Cache untuk hasil OCR berdasarkan hash MD5 ===
ocr_cache = load_ocr_cache()

# === Fungsi utama: Deteksi phishing dari gambar ===
async def scan_image_for_phishing(message):
    for att in message.attachments:
        if any(att.filename.lower().endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".webp"]):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(att.url) as resp:
                        image_bytes = await resp.read()
                        image_hash = hashlib.md5(image_bytes).hexdigest()
                        print(f"[🧪] Hash gambar: {image_hash}")

                        # 🔒 Deteksi dari blacklist hash
                        if image_hash in BLACKLISTED_IMAGE_HASHES:
                            print(f"[⚠️] Gambar cocok dengan blacklist hash: {image_hash}")
                            return True, f"[TERDETEKSI HASH BLACKLISTED: {image_hash}]"

                        # 🔁 Gunakan cache OCR
                        if image_hash in ocr_cache:
                            text = ocr_cache[image_hash]
                        else:
                            text = await extract_text_from_bytes(image_bytes)
                            if text:
                                ocr_cache[image_hash] = text
                                save_ocr_cache()

                        if not text:
                            continue

                        text = text.lower()
                        print(f"[🧪] Final OCR Text untuk analisa: {text}")
                        if any(k in text for k in STATIC_KEYWORDS + BLACKLISTED_KEYWORDS):
                            print(f"[⚠️] Keyword phishing ditemukan di OCR gambar.")
                            return True, text

            except Exception as e:
                print(f"[❌] OCR scan gagal: {e}")
    return False, ""

# === Fungsi: Kirim gambar ke ocr.space ===
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

            print("[🧪] OCR API raw response:", result)

            parsed = result.get("ParsedResults", [])
            if parsed and "ParsedText" in parsed[0]:
                text = parsed[0]["ParsedText"]
                print(f"[🧪] OCR Extracted Text:\n{text}")
                return text
            return ""
