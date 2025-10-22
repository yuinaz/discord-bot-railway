
# Uses the same loader as cogs
import json
from satpambot.bot.modules.discord_bot.helpers.config_loader import load_qna_config, load_topics

cfg = load_qna_config()
print("[qna] resolved channel_id :", cfg["qna_channel_id"])
print("[qna] provider_order      :", cfg["provider_order"])
print("[qna] ask                 :", cfg["ask"])
print("[qna] answer              :", cfg["answer"])
print("[qna] topics_path         :", cfg.get("topics_path",""))
if cfg.get("topics_path"):
    t = load_topics(cfg["topics_path"])
    print("[qna] topics keys         :", list(t.keys())[:10])
else:
    print("[qna] topics not found")
