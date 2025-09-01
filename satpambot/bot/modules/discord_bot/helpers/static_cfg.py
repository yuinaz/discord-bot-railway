LOG_CHANNEL_NAME="log-botphising"
LOG_THREAD_NAME="Ban Log"
ERROR_LOG_CHANNEL_NAME="errorlog-bot"
BAN_DELETE_DAYS=7
REQUIRE_MASS_MENTION = False
INVITE_PATTERNS=[r"(?:discord(?:app)?\.com/invite|discord\.gg)/[A-Za-z0-9]+",r"discord\.com/api/webhooks/",r"(?i)(nitro|gift).*(discord|steam)"]
SHORTENER_DOMAINS={"bit.ly","t.co","tinyurl.com","is.gd","buff.ly","cutt.ly","s.id","goo.gl"}
GSB_TIMEOUT=1.2
VT_TIMEOUT=2.0
REPUTATION_CACHE_TTL=3600

PHASH_MAX_DISTANCE = 6
PHASH_MAX_FRAMES = 6
PHASH_AUGMENT_REGISTER = True
PHASH_AUGMENT_PER_FRAME = 5  # base + hflip + rot±7 + center-crop
