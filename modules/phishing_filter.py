import re, tldextract, pytesseract
from PIL import Image
from io import BytesIO

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

async def scan_image_for_phishing(message):
    for att in message.attachments:
        if any(att.filename.lower().endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".webp"]):
            try:
                img = Image.open(BytesIO(await att.read()))
                text = pytesseract.image_to_string(img)
                if any(k in text.lower() for k in STATIC_KEYWORDS + BLACKLISTED_KEYWORDS):
                    return True, text
            except Exception as e:
                print("OCR error:", e)
    return False, ""