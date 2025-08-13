# Image classifier guard (auto)
import os, logging, discord
from modules.discord_bot.helpers.image_classifier import classify_image
from modules.discord_bot.helpers.permissions import is_exempt_user, is_whitelisted_channel  # permissions import
from modules.discord_bot.helpers.db import log_action
from modules.discord_bot.helpers.log_utils import find_text_channel

async def handle_image_classifier(message: discord.Message):
    if is_whitelisted_channel(getattr(message,'channel',None)) or is_exempt_user(getattr(message,'author',None)): return
    try:
        if not message.attachments:
            return
        for att in message.attachments:
            if not (att.content_type or "").startswith("image"):
                continue
            img_bytes = await att.read()
            res = classify_image(img_bytes)
            if not res.get("enabled"):
                continue
            if res.get("verdict") == "black":
                # always delete
                try: await message.delete()
                except Exception: pass
                # log
                try:
                    ch = find_text_channel(message.guild, "log-satpam-chat") if message.guild else None
                    if ch:
                        await ch.send(f"🛡️ Deteksi gambar scam (no text) dari {message.author.mention}. score={res.get('score'):.3f} (≥ {res.get('threshold')}). Action={res.get('action')}")
                except Exception: pass
                # punitive action per config
                act = (res.get("action") or "delete").lower()
                if message.guild and act in ("ban","kick"):
                    try:
                        if act=="ban" and message.guild.me.guild_permissions.ban_members:
                            await message.guild.ban(message.author, reason="Image scam classifier", delete_message_days=1)
                        elif act=="kick" and message.guild.me.guild_permissions.kick_members:
                            await message.guild.kick(message.author, reason="Image scam classifier")
                    except Exception:
                        pass
                # Once one image is flagged, stop scanning others in this message
                return
    except Exception as e:
        logging.debug(f"[image_classifier_guard] error: {e}")
