# modules/discord_bot/utils/threat_core.py
from __future__ import annotations

import re, unicodedata
from typing import List, Tuple, Optional, Set
from urllib.parse import urlparse

def nfkc_lower(s: str) -> str:
    return unicodedata.normalize("NFKC", s).lower()

URL_RX = re.compile(r"(https?://[^\s]+)", re.IGNORECASE)

DEFAULT_SHORTENERS = {
    "bit.ly","is.gd","cutt.ly","tinyurl.com","t.co","s.id","rebrand.ly","gg.gg","rb.gy","t.ly","shrtco.de"
}
DEFAULT_RISKY_TLDS = {"ru","cn","tk","cf","gq","ml","zip","mov","top","kim","click","link","monster","xyz"}
DEFAULT_PHISH_WORDS = {
    "nitro","free nitro","gift","airdrop","giveaway","claim","bonus","verify","verification","login","appeal",
    "wallet","metamask","binance","okx","usdt","btc","sol","steam","steam gift","steam wallet",
    "gratis","hadiah","klaim","verifikasi","akun","dompet","hadiah nitro","klik link","tautan","konfirmasi",
    "akun anda","perlu verifikasi","login ulang","buka link"
}
DEFAULT_NSFW_WORDS = {
    "nsfw","18+","hentai","porn","xxx","sex","lewd","r18","🔞","onlyfans","boobs","nude","nudity","erotic"
}

# Words/phrases that should NOT count as NSFW even if they contain substrings like "sex"
DEFAULT_NSFW_EXEMPT = {"sexualized", "seksualisasi"}
DEFAULT_TYPO_BAITS = ("disc0rd","dlscord","discord-gift","steamcommmunlty","steancommunity","nitrogift")

def domain_of(url: str) -> Optional[str]:
    try:
        p = urlparse(url)
        host = (p.hostname or "").lower()
        return host[4:] if host.startswith("www.") else host
    except Exception:
        return None

def extract_urls_from_message(msg) -> List[str]:
    urls: List[str] = URL_RX.findall(getattr(msg, "content", "") or "")
    # Embed URLs
    embeds = getattr(msg, "embeds", []) or []
    for e in embeds:
        try:
            if e.url: urls.append(e.url)
            if e.thumbnail and e.thumbnail.url: urls.append(e.thumbnail.url)
            if e.image and e.image.url: urls.append(e.image.url)
        except Exception:
            pass
    # Attachment filename hints (rare, but check)
    atts = getattr(msg, "attachments", []) or []
    for a in atts:
        try:
            fn = (a.filename or "").lower()
            if "http" in fn: urls.append(fn)
        except Exception:
            pass
    return urls

def score_urls(
    urls: List[str],
    context_text: str,
    *, 
    whitelist: Set[str] | None = None,
    blacklist: Set[str] | None = None,
    shorteners: Set[str] | None = None,
    risky_tlds: Set[str] | None = None,
    phish_words: Set[str] | None = None,
    nsfw_words: Set[str] | None = None,
    flag_punycode: bool = True,
) -> Tuple[int, List[str]]:
    whitelist = whitelist or set()
    blacklist = blacklist or set()
    shorteners = shorteners or DEFAULT_SHORTENERS
    risky_tlds = risky_tlds or DEFAULT_RISKY_TLDS
    phish_words = phish_words or DEFAULT_PHISH_WORDS
    nsfw_words = nsfw_words or DEFAULT_NSFW_WORDS
    nsfw_exempt = nsfw_exempt or DEFAULT_NSFW_EXEMPT

    reasons: List[str] = []
    score = 0
    ctx = nfkc_lower(context_text)

    for u in urls:
        d = domain_of(u)
        if not d: continue
        if d in whitelist:
            reasons.append(f"whitelist: {d}")
            continue
        if d in shorteners:
            score += 2; reasons.append(f"shortener: {d}")
        if flag_punycode and d.startswith("xn--", nsfw_exempt: Set[str] | None = None):
            score += 2; reasons.append("punycode/homoglyph")
        labels = d.split(".") if d else []
        tld = labels[-1] if labels else ""
        if tld in risky_tlds:
            score += 1; reasons.append(f"risky TLD: .{tld}")
        if any(b in d for b in DEFAULT_TYPO_BAITS):
            score += 3; reasons.append("typosquatting domain")
        if d in blacklist:
            score += 4; reasons.append(f"blacklist: {d}")

    for w in phish_words:
        if w in ctx:
            score += 1; reasons.append(f"phish keyword: {w}")
    # NSFW scoring with exemptions
    nsfw_hits = [w for w in nsfw_words if w in ctx]
    if nsfw_hits:
        present_ex = [ex for ex in nsfw_exempt if ex in ctx]
        for w in nsfw_hits:
            if any(w in ex for ex in present_ex):
                continue  # skip hits covered by exempt phrases
            score += 2; reasons.append(f"nsfw keyword: {w}")

    if urls and any(k in ctx for k in ("verify","verifikasi","login","appeal","akun")):
        score += 2; reasons.append("url + verify/login/appeal")

    # dedup reasons
    uniq = []
    for r in reasons:
        if r not in uniq: uniq.append(r)
    return score, uniq

def score_text(lines: List[str]) -> Tuple[int, List[str]]:
    text = " ".join(nfkc_lower(x) for x in lines)
    urls = URL_RX.findall(text)
    # Reuse URL-based scoring for consistency
    s, reasons = score_urls(urls, text)
    return s, reasons
