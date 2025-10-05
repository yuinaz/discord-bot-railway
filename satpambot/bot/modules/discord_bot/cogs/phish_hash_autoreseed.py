import asyncio
import json

import discord
from discord import AllowedMentions
from discord.ext import commands, tasks

from satpambot.bot.modules.discord_bot.helpers import img_hashing, static_cfg

PHASH_DB_TITLE = "SATPAMBOT_PHASH_DB_V1"



IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff", ".heic", ".heif")



INBOX_NAME = getattr(static_cfg, "PHISH_INBOX_THREAD", "imagephising").lower()







NOTIFY_THREAD = getattr(static_cfg, "PHISH_NOTIFY_THREAD", False)



LOG_TTL_SECONDS = int(getattr(static_cfg, "PHISH_LOG_TTL", 0))  # 0 = keep



LIMIT_MSGS = int(getattr(static_cfg, "PHISH_AUTO_RESEED_LIMIT", 2000))











def _render_db(phashes, dhashes=None, tiles=None):



    data = {"phash": phashes or []}



    if dhashes:



        data["dhash"] = dhashes



    if tiles:



        data["tphash"] = tiles



    body = json.dumps(data, ensure_ascii=False, separators=(",", ":"), sort_keys=True)



    return f"{PHASH_DB_TITLE}\n```json\n{body}\n```"











def _extract_hashes_from_json_msg(msg: discord.Message):



    if not msg or not msg.content:



        return [], [], []



    s = msg.content



    i, j = s.find("{"), s.rfind("}")



    if i != -1 and j != -1 and j > i:



        try:



            obj = json.loads(s[i : j + 1])



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











class PhishHashAutoReseed(commands.Cog):



    def __init__(self, bot: commands.Bot) -> None:



        self.bot = bot



        self._ran_guilds = set()



        self.auto_task.start()







    def cog_unload(self):



        try:



            self.auto_task.cancel()



        except Exception:



            pass







    @tasks.loop(count=1)



    async def auto_task(self):



        await self.bot.wait_until_ready()



        await asyncio.sleep(3)



        for g in list(self.bot.guilds):



            if g.id in self._ran_guilds:



                continue



            try:



                await self._process_guild(g)



                self._ran_guilds.add(g.id)



            except Exception:



                continue







    async def _process_guild(self, guild: discord.Guild):



        target_thread = next((th for th in guild.threads if (th.name or "").lower() == INBOX_NAME), None)



        if not target_thread:



            return



        parent = getattr(target_thread, "parent", None)



        if not parent:



            return







        db_msg = None



        async for m in parent.history(limit=50):



            if m.author.id == self.bot.user.id and PHASH_DB_TITLE in (m.content or ""):



                db_msg = m



                break



        if db_msg:



            P, D, T = _extract_hashes_from_json_msg(db_msg)



            if P and D and T:



                # Already complete, but also re-render to normalize format (remove stray \n, spaces)



                try:



                    content = _render_db(P, D, T)



                    await db_msg.edit(content=content)



                except Exception:



                    pass



                return







        all_p, all_d, all_t = [], [], []



        scanned_msgs = scanned_atts = 0



        async for m in target_thread.history(limit=LIMIT_MSGS, oldest_first=True):



            scanned_msgs += 1



            if not m.attachments:



                continue



            for att in m.attachments:



                name = (att.filename or "").lower()



                if not name.endswith(



                    (



                        ".png",



                        ".jpg",



                        ".jpeg",



                        ".webp",



                        ".gif",



                        ".bmp",



                        ".tif",



                        ".tiff",



                        ".heic",



                        ".heif",



                    )



                ):



                    continue



                raw = await att.read()



                if not raw:



                    continue



                scanned_atts += 1







                hs = img_hashing.phash_list_from_bytes(



                    raw,



                    max_frames=getattr(static_cfg, "PHASH_MAX_FRAMES", 6),



                    augment=getattr(static_cfg, "PHASH_AUGMENT_REGISTER", True),



                    augment_per_frame=getattr(static_cfg, "PHASH_AUGMENT_PER_FRAME", 5),



                )



                if hs:



                    all_p.extend(hs)







                dhf = getattr(img_hashing, "dhash_list_from_bytes", None)



                if dhf:



                    ds = dhf(



                        raw,



                        max_frames=getattr(static_cfg, "PHASH_MAX_FRAMES", 6),



                        augment=getattr(static_cfg, "PHASH_AUGMENT_REGISTER", True),



                        augment_per_frame=getattr(static_cfg, "PHASH_AUGMENT_PER_FRAME", 5),



                    )



                    if ds:



                        all_d.extend(ds)







                tfunc = getattr(img_hashing, "tile_phash_list_from_bytes", None)



                if tfunc:



                    ts = tfunc(



                        raw,



                        grid=getattr(static_cfg, "TILE_GRID", 3),



                        max_frames=getattr(static_cfg, "PHASH_MAX_FRAMES", 4),



                        augment=getattr(static_cfg, "PHASH_AUGMENT_REGISTER", True),



                        augment_per_frame=0,



                    )



                    if ts:



                        all_t.extend(ts)







                if (scanned_atts % 25) == 0:



                    await asyncio.sleep(1)







        existing_p, existing_d, existing_t = ([], [], [])



        if db_msg:



            existing_p, existing_d, existing_t = _extract_hashes_from_json_msg(db_msg)







        sp, sd, st = set(existing_p), set(existing_d), set(existing_t)



        for h in all_p:



            if h not in sp:



                existing_p.append(h)



                sp.add(h)



        for h in all_d:



            if h not in sd:



                existing_d.append(h)



                sd.add(h)



        for t in all_t:



            if t not in st:



                existing_t.append(t)



                st.add(t)







        content = _render_db(existing_p, existing_d, existing_t)







        if db_msg:



            try:



                await db_msg.edit(content=content)



            except Exception:



                pass



        else:



            try:



                db_msg = await parent.send(content)



            except Exception:



                db_msg = None







        try:



            emb = discord.Embed(



                title="Auto reseed selesai",



                description=f"Thread: {target_thread.mention}\nScanned: {scanned_msgs} msgs / {scanned_atts} attachments",  # noqa: E501



                colour=0x00B894,



            )



            emb.add_field(name="Total pHash", value=str(len(existing_p)), inline=True)



            emb.add_field(name="Total dHash", value=str(len(existing_d)), inline=True)



            m = await parent.send(embed=emb, allowed_mentions=AllowedMentions.none())



            if LOG_TTL_SECONDS > 0:



                await asyncio.sleep(LOG_TTL_SECONDS)



                await m.delete()



        except Exception:



            pass











async def setup(bot: commands.Bot):



    await bot.add_cog(PhishHashAutoReseed(bot))











def legacy_setup(bot: commands.Bot):



    bot.add_cog(PhishHashAutoReseed(bot))



