import re, tldextract, pytesseract, os, aiohttp
from PIL import Image
from io import BytesIO

# === Konfigurasi keyword phishing dasar
STATIC_KEYWORDS = [
    "mrbeast", "free nitro", "claim nitro", "steam nitro",
    "mr beast", "nitro generator", "airdrop", "event nitro"
]

# === Load domain whitelist/blacklist dari file
def load_list(file):
    try:
        with open(file) as f:
            return [line.strip().lower() for line in f if line.strip()]
    except:
        return []

WHITELISTED_DOMAINS = load_list("whitelist.txt")
BLACKLISTED_KEYWORDS = load_list("blacklist.txt")

# === Deteksi domain utama dari URL
def extract_root_domain(url):
    ext = tldextract.extract(url)
    return f"{ext.domain}.{ext.suffix}"

# === Pola regex pencari URL
url_pattern = re.compile(r'https?://\S+')

# === Cek apakah URL mengandung domain yang dikecualikan
def is_whitelisted(content):
    return any(extract_root_domain(url) in WHITELISTED_DOMAINS for url in url_pattern.findall(content.lower()))

# === Cek gambar yang diupload untuk teks phishing (OCR)
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

# === Google Safe Browsing check
async def check_with_gsb(url):
    api_key = os.getenv("GOOGLE_SAFE_BROWSING_KEY")
    if not api_key: return False
    endpoint = f"https://safebrowsing.googleapis.com/v4/threatMatches:find?key={api_key}"
    payload = {
        "client": {"clientId": "satpambot", "clientVersion": "1.0"},
        "threatInfo": {
            "threatTypes": ["MALWARE", "SOCIAL_ENGINEERING", "POTENTIALLY_HARMFUL_APPLICATION"],
            "platformTypes": ["ANY_PLATFORM"],
            "threatEntryTypes": ["URL"],
            "threatEntries": [{"url": url}]
        }
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(endpoint, json=payload) as r:
                data = await r.json()
                return bool(data.get("matches"))
    except Exception as e:
        print("GSB Error:", e)
        return False

# === VirusTotal URL check
async def check_with_virustotal(url):
    api_key = os.getenv("VIRUSTOTAL_API_KEY")
    if not api_key: return False
    headers = {"x-apikey": api_key}
    vt_url = f"https://www.virustotal.com/api/v3/urls"
    import base64

    try:
        async with aiohttp.ClientSession() as session:
            # Submit URL for analysis
            async with session.post(vt_url, data={"url": url}, headers=headers) as r:
                data = await r.json()
                analysis_id = data.get("data", {}).get("id")
                if not analysis_id: return False

            # Get analysis report
            url_id = base64.urlsafe_b64encode(url.encode()).decode().strip("=")
            async with session.get(f"{vt_url}/{url_id}", headers=headers) as r:
                result = await r.json()
                stats = result.get("data", {}).get("attributes", {}).get("last_analysis_stats", {})
                if stats.get("malicious", 0) > 0 or stats.get("suspicious", 0) > 1:
                    return True
    except Exception as e:
        print("VT Error:", e)
    return False

# === Kombinasi pengecekan URL berbahaya
async def is_malicious_url(url):
    if extract_root_domain(url) in WHITELISTED_DOMAINS:
        return False
    if await check_with_gsb(url): return True
    if await check_with_virustotal(url): return True
    return False
