import asyncio
import json
import discord
from discord.ext import commands
from discord import AllowedMentions

from satpambot.bot.modules.discord_bot.helpers import img_hashing, static_cfg

PHASH_DB_TITLE = "SATPAMBOT_PHASH_DB_V1"
TARGET_THREAD_NAME = getattr(static_cfg, "PHISH_INBOX_THREAD", "imagephising").lower()
IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff", ".heic", ".heif")

# toggles (respect existing config; do not change values)
NOTIFY_THREAD = getattr(static_cfg, "PHISH_NOTIFY_THREAD", False)
LOG_TTL_SECONDS = int(getattr(static_cfg, "PHISH_LOG_TTL", 0))  # 0 = keep forever

async def _autodelete(msg: discord.Message, delay: int):
    try:
        if delay and delay > 0:
            await asyncio.sleep(delay)
            await msg.delete()
    except Exception:
        pass

def _render_db(phashes, dhashes=None, tiles=None):
    data = {"phash": phashes}
    if dhashes:
        data["dhash"] = dhashes
    if tiles:
        data["tphash"] = tiles
    # Use real newlines for Discord code block
    return f"{PHASH_DB_TITLE}\n```json\n{json.dumps(data, ensure_ascii=False)}\n```"

def _extract_hashes_from_json_msg(msg: discord.Message):
    if not msg or not msg.content:
        return [], [], []
    s = msg.content
    i, j = s.find("{"), s.rfind("}")
    if i != -1 and j != -1 and j > i:
        try:
            obj = json.loads(s[i:j+1])
            arr_p = obj.get("phash", []) or []
            arr_d = obj.get("dhash", []) or []
            arr_t = obj.get("tphash", []) or []
            P = [str(x).strip() for x in arr_p if str(x).strip()]
            D = [str(x).strip() for x in arr_d if str(x).strip()]
            T = [str(x).strip() for x in arr_t if str(x).strip()]
            return P, D, T
        except Exception:
            return [], [], []
    return [], [], []

class PhishHashInbox(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener("on_message")
    async def on_message_inbox(self, message: discord.Message):
        # Defensive: never raise from listener
        try:
            # Only in target thread
            ch = message.channel
            if not isinstance(ch, discord.Thread):
                return
            if (ch.name or "").lower() != TARGET_THREAD_NAME:
                return

            # Ignore bots / no attachments
            if getattr(message.author, "bot", False):
                return
            if not message.attachments:
                return

            # Compute hashes
            all_p, all_d, all_t, filenames = [], [], [], []
            for att in message.attachments:
                name = (att.filename or "").lower()
                if not any(name.endswith(ext) for ext in IMAGE_EXTS):
                    continue

                try:
                    raw = await att.read()
                except Exception:
                    continue
                if not raw:
                    continue

                filenames.append(att.filename or "unknown")

                # pHash
                hs = img_hashing.phash_list_from_bytes(
                    raw,
                    max_frames=getattr(static_cfg, "PHASH_MAX_FRAMES", 6),
                    augment=getattr(static_cfg, "PHASH_AUGMENT_REGISTER", True),
                    augment_per_frame=getattr(static_cfg, "PHASH_AUGMENT_PER_FRAME", 5),
                )
                if hs:
                    all_p.extend(hs)

                # dHash (if helper available)
                dh_func = getattr(img_hashing, "dhash_list_from_bytes", None)
                if dh_func:
                    ds = dh_func(
                        raw,
                        max_frames=getattr(static_cfg, "PHASH_MAX_FRAMES", 6),
                        augment=getattr(static_cfg, "PHASH_AUGMENT_REGISTER", True),
                        augment_per_frame=getattr(static_cfg, "PHASH_AUGMENT_PER_FRAME", 5),
                    )
                    if ds:
                        all_d.extend(ds)

                # Tile pHash (if helper available)
                t_func = getattr(img_hashing, "tile_phash_list_from_bytes", None)
                if t_func:
                    ts = t_func(
                        raw,
                        grid=getattr(static_cfg, "TILE_GRID", 3),
                        max_frames=getattr(static_cfg, "PHASH_MAX_FRAMES", 4),
                        augment=getattr(static_cfg, "PHASH_AUGMENT_REGISTER", True),
                        augment_per_frame=3,
                    )
                    if ts:
                        all_t.extend(ts)

            if not (all_p or all_d or all_t):
                return

            parent = ch.parent if hasattr(ch, "parent") else None

            # Find existing DB message
            db_msg = None
            if parent:
                try:
                    async for m in parent.history(limit=50):
                        if m.author.id == self.bot.user.id and PHASH_DB_TITLE in (m.content or ""):
                            db_msg = m
                            break
                except Exception:
                    db_msg = None

            existing_p, existing_d, existing_t = ([], [], [])
            if db_msg:
                try:
                    existing_p, existing_d, existing_t = _extract_hashes_from_json_msg(db_msg)
                except Exception:
                    existing_p, existing_d, existing_t = ([], [], [])

            # Merge unique
            sp, sd, st = set(existing_p), set(existing_d), set(existing_t)
            added_p, added_d, added_t = [], [], []

            for h in all_p:
                if h not in sp:
                    existing_p.append(h); sp.add(h); added_p.append(h)
            for h in all_d:
                if h not in sd:
                    existing_d.append(h); sd.add(h); added_d.append(h)
            for t in all_t:
                if t not in st:
                    existing_t.append(t); st.add(t); added_t.append(t)

            content = _render_db(existing_p, existing_d, existing_t)

            # Update/create DB message
            if db_msg:
                try:
                    await db_msg.edit(content=content)
                except Exception:
                    pass
            else:
                if parent:
                    try:
                        db_msg = await parent.send(content)
                    except Exception:
                        db_msg = None

            # Notify & cleanup per config
            # (Reply in thread only if enabled)
            if NOTIFY_THREAD:
                try:
                    e = discord.Embed(
                        title="pHash update",
                        description=f"Files: {', '.join(filenames)[:1800]}",
                        colour=0xFF8C00,
                    )
                    e.add_field(name="Hashes added", value=str(len(added_p) + len(added_d) + len(added_t)), inline=True)
                    e.add_field(name="pHash total", value=str(len(existing_p)), inline=True)
                    e.add_field(name="dHash total", value=str(len(existing_d)), inline=True)
                    await message.reply(embed=e, mention_author=False, allowed_mentions=AllowedMentions.none())
                except Exception:
                    pass

            # Always log to parent if different; auto-delete obeying TTL
            if parent and parent != ch:
                try:
                    e2 = discord.Embed(
                        title="pHash update",
                        description=f"Files: {', '.join(filenames)[:1800]}",
                        colour=0xFF8C00,
                    )
                    e2.add_field(name="Hashes added", value=str(len(added_p) + len(added_d) + len(added_t)), inline=True)
                    e2.add_field(name="pHash total", value=str(len(existing_p)), inline=True)
                    e2.add_field(name="dHash total", value=str(len(existing_d)), inline=True)
                    sent = await parent.send(embed=e2, allowed_mentions=AllowedMentions.none())
                    if LOG_TTL_SECONDS > 0:
                        asyncio.create_task(_autodelete(sent, LOG_TTL_SECONDS))
                except Exception:
                    pass

        except Exception:
            # Never crash the bot due to inbox listener
            return

async def setup(bot: commands.Bot):
    await bot.add_cog(PhishHashInbox(bot))

def legacy_setup(bot: commands.Bot):
    bot.add_cog(PhishHashInbox(bot))
