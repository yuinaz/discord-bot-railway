#!/usr/bin/env python3
from __future__ import annotations







# -*- coding: utf-8 -*-







"""







Apply Self-Learning v4 patch (folderless) for SatpamBot.







Run this script from the **root** of your repo (same level as `satpambot/`).















What it does:







- Writes/updates files under satpambot/ml and cogs







- Adds scripts/smoke_all.py and scripts/smoketest_self_learning_v4.py







- Adds patches/auto_inject_guard_hooks.py







- Adds requirements-optional.txt







Idempotent: safe to run multiple times.







"""















import os

FILES = {







    "satpambot/ml/online_nb.py": r"""from __future__ import annotations







import math







from collections import defaultdict







from typing import Dict, Iterable















class OnlineNB:







    def __init__(self, alpha: float = 1.0):







        self.alpha = alpha







        self.pos_counts = defaultdict(int)







        self.neg_counts = defaultdict(int)







        self.pos_total = 0







        self.neg_total = 0







        self.pos_docs = 0







        self.neg_docs = 0







        self.vocab = set()















    def _update_vocab(self, tokens: Iterable[str]):







        for t in tokens:







            if t:







                self.vocab.add(t)















    def learn(self, tokens: Iterable[str], label: str):







        tokens = [t for t in tokens if t]







        if not tokens:







            return







        self._update_vocab(tokens)







        if label == "phish":







            for t in tokens:







                self.pos_counts[t] += 1







                self.pos_total += 1







            self.pos_docs += 1







        else:







            for t in tokens:







                self.neg_counts[t] += 1







                self.neg_total += 1







            self.neg_docs += 1















    def _log_prob(self, tokens: Iterable[str], label: str) -> float:







        total_docs = self.pos_docs + self.neg_docs







        prior = 0.5 if total_docs == 0 else ((self.pos_docs if label=='phish' else self.neg_docs) / total_docs)







        counts, total = (self.pos_counts, self.pos_total) if label=='phish' else (self.neg_counts, self.neg_total)







        V = max(1, len(self.vocab))







        a = self.alpha







        logp = math.log(prior if prior>0 else 1e-9)







        for t in tokens:







            c = counts.get(t, 0)







            logp += math.log((c + a) / (total + a * V))







        return logp















    def predict_proba(self, tokens: Iterable[str]) -> Dict[str, float]:







        tokens = [t for t in tokens if t]







        if not tokens:







            return {'phish': 0.5, 'safe': 0.5}







        lp_pos = self._log_prob(tokens, 'phish')







        lp_neg = self._log_prob(tokens, 'safe')







        m = max(lp_pos, lp_neg)







        p_pos = math.exp(lp_pos - m)







        p_neg = math.exp(lp_neg - m)







        Z = p_pos + p_neg







        return {'phish': p_pos / Z, 'safe': p_neg / Z}







""",







    "satpambot/ml/feature_extractor.py": r"""from __future__ import annotations







import re, io, hashlib







from typing import List, Optional







try:







    from PIL import Image







except Exception:







    Image = None















PHISHY_TLDS = {"ru","tk","ml","ga","cf","gq","top","icu","click","xyz","cn","rest"}







SEED_WORDS = {"nitro","giveaway","gratis","free","gift","steam","genshin","mihoyo","topup","claim","verif","verify","hadiah"}  # noqa: E501















def tokenize_text(s: str) -> List[str]:







    s = (s or "").lower()







    tokens = re.findall(r"[a-z0-9]+(?:\.[a-z0-9]+)*|[a-z0-9]+", s)







    out = []







    for t in tokens:







        if len(t) <= 2:







            continue







        out.append(t)







        if "." in t:







            parts = t.split(".")







            out.extend(parts)







            tld = parts[-1]







            out.append("tld:"+tld)







            if tld in PHISHY_TLDS:







                out.append("tld_phishy")







    for w in SEED_WORDS:







        if w in s:







            out.append("seed:"+w)







    return out















def dhash64(b: bytes) -> Optional[str]:







    if Image is None:







        return None







    try:







        with Image.open(io.BytesIO(b)) as im:







            im = im.convert("L").resize((9,8))







            px = list(im.getdata())







            rows = [px[i*9:(i+1)*9] for i in range(8)]







            bits = 0







            for r in range(8):







                for c in range(8):







                    left = rows[r][c]







                    right = rows[r][c+1]







                    bits = (bits<<1) | (1 if left > right else 0)







            return f"{bits:016x}"







    except Exception:







        return None















def sha1k(b: bytes, k: int=12288) -> str:







    return hashlib.sha1(b[:k]).hexdigest()















def extract_tokens(message_content: str, ocr_text: Optional[str]=None) -> List[str]:







    tokens = []







    tokens += tokenize_text(message_content or "")







    if ocr_text:







        tokens += tokenize_text(ocr_text)







    return tokens







""",







    "satpambot/ml/phash_reconcile.py": r"""from __future__ import annotations







import json, re







from typing import Set, Tuple, Optional







import discord







from .feature_extractor import dhash64















PAT_MAGIC = "SATPAMBOT_PHASH_DB_V1"















def _hex_ok(s: str) -> bool:







    if not s:







        return False







    s = s.strip().lower()







    return re.fullmatch(r"[0-9a-f]{16,64}", s) is not None















def hamming_hex(a: str, b: str) -> Optional[int]:







    try:







        xa = int(a, 16)







        xb = int(b, 16)







        return (xa ^ xb).bit_count()







    except Exception:







        return None















async def collect_phash_from_log(channel: discord.TextChannel, limit_msgs: int = 400) -> Set[str]:







    found: Set[str] = set()







    async for msg in channel.history(limit=limit_msgs, oldest_first=False):







        text = (msg.content or "")







        if PAT_MAGIC in text:







            blocks = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.S) or re.findall(r"(\{.*\})", text, flags=re.S)  # noqa: E501







            for blob in blocks:







                try:







                    d = json.loads(blob)







                except Exception:







                    continue







                arr = d.get("dhash") or d.get("phash") or []







                if isinstance(arr, list):







                    for it in arr:







                        if isinstance(it, str) and _hex_ok(it):







                            found.add(it.lower())







    return found















async def collect_image_hashes_from_thread(th: discord.Thread, limit_msgs: int = 250) -> Set[str]:







    seen: Set[str] = set()







    async for msg in th.history(limit=limit_msgs, oldest_first=True):







        for a in msg.attachments[:







            2]:







            if a.content_type and a.content_type.startswith("image/"):







                try:







                    b = await a.read()







                except Exception:







                    continue







                h = dhash64(b)







                if h:







                    seen.add(h.lower())







    return seen















def split_false_positives(log_hashes: Set[str], phish_hashes: Set[str], ham_thr: int = 6) -> Tuple[Set[str], Set[str]]:







    tps: Set[str] = set()







    fps: Set[str] = set()







    for h in log_hashes:







        matched = False







        for p in phish_hashes:







            dv = hamming_hex(h, p)







            if dv is not None and dv <= ham_thr:







                matched = True







                break







        (tps if matched else fps).add(h)







    return tps, fps







""",







    "satpambot/ml/state_store_discord.py": r"""from __future__ import annotations







import asyncio, io, gzip, json, datetime







from typing import Optional, Dict, Any, List







import discord















SNAPSHOT_PREFIX = "mlsnap_"







MAX_MESSAGES_SCAN = 250







MAX_ATTACH_PER_MSG = 2















CHAN_CANDIDATES = ["log-botphising","log-botphishing","log-satpam","log-satpam-bot"]







THREAD_PHISH = ["imagephising","image-phising","imagephishing","image-phishing"]







THREAD_WL = ["whitelist","white-list","wl-"]







THREAD_BANLOG = ["ban-log","log-ban","banlog"]







THREAD_BLACKLIST = ["blacklist","black-list"]







THREAD_STATE = ["ml-state"]















class CombinedState:







    def __init__(self):







        self.model_dict: Dict[str, Any] = {}







        self.whitelist = {"dhash64": [], "sha1k": []}







        self.exempt = {"threads": [], "channels": []}















    def to_json_bytes(self) -> bytes:







        data = {"version": 4, "model": self.model_dict, "whitelist": self.whitelist, "exempt": self.exempt}







        js = json.dumps(data).encode("utf-8")







        return gzip.compress(js)















    @classmethod







    def from_json_bytes(cls, b: bytes) -> "CombinedState":







        d = json.loads(gzip.decompress(b).decode("utf-8"))







        cs = cls()







        cs.model_dict = d.get("model", {})







        cs.whitelist = d.get("whitelist", {"dhash64": [], "sha1k": []})







        cs.exempt = d.get("exempt", {"threads": [], "channels": []})







        return cs















class MLState:







    def __init__(self, bot: discord.Client):







        self.bot = bot







        self.parent_channel_id: Optional[int] = None







        self.thread_id: Optional[int] = None







        self.combined = CombinedState()







        self.model = None  # OnlineNB















    def _name_has_any(self, name: str, keys: List[str]) -> bool:







        n = (name or "").lower()







        return any(k in n for k in keys)















    def find_log_channel(self) -> Optional[discord.TextChannel]:







        for ch in self.bot.get_all_channels():







            if isinstance(ch, discord.TextChannel):







                if self._name_has_any(ch.name, CHAN_CANDIDATES):







                    return ch







        return None















    def all_active_threads(self) -> List[discord.Thread]:







        ths = []







        for ch in self.bot.get_all_channels():







            if isinstance(ch, discord.TextChannel):







                try:







                    ths.extend(getattr(ch, "threads", []))







                except Exception:







                    pass







        return ths















    def classify_threads(self):







        phish = []







        wl = []







        banlog = []







        bl = []







        state = []







        for th in self.all_active_threads():







            n = (th.name or "").lower()







            if self._name_has_any(n, THREAD_STATE):







                state.append(th)







            if self._name_has_any(n, THREAD_PHISH):







                phish.append(th)







            if self._name_has_any(n, THREAD_WL):







                wl.append(th)







            if self._name_has_any(n, THREAD_BANLOG):







                banlog.append(th)







            if self._name_has_any(n, THREAD_BLACKLIST):







                bl.append(th)







        return phish, wl, banlog, bl, state















    async def _ensure_thread(self) -> Optional[discord.Thread]:







        parent = None







        if self.parent_channel_id:







            ch = self.bot.get_channel(self.parent_channel_id)







            if isinstance(ch, discord.TextChannel):







                parent = ch







        if parent is None:







            parent = self.find_log_channel()







        if parent is None:







            return None















        if self.thread_id:







            t = self.bot.get_channel(self.thread_id)







            if isinstance(t, discord.Thread):







                return t







        for th in getattr(parent, "threads", []):







            if (th.name or "").lower() == "ml-state":







                self.thread_id = th.id







                return th







        try:







            th = await parent.create_thread(name="ml-state", type=discord.ChannelType.public_thread)







            self.thread_id = th.id







            return th







        except Exception:







            return None















    async def load_latest(self) -> bool:







        from .online_nb import OnlineNB







        th = await self._ensure_thread()







        if th is None:







            self.model = OnlineNB()







            return False







        try:







            async for msg in th.history(limit=50, oldest_first=False):







                for a in msg.attachments:







                    if a.filename.startswith(SNAPSHOT_PREFIX) and a.filename.endswith(".json.gz"):







                        b = await a.read()







                        cs = CombinedState.from_json_bytes(b)







                        self.combined = cs







                        self.model = OnlineNB.from_dict(cs.model_dict) if cs.model_dict else OnlineNB()







                        return True







        except Exception:







            pass







        self.model = OnlineNB()







        return False















    async def save_snapshot(self) -> bool:







        if self.model is None:







            return False







        from .online_nb import OnlineNB







        self.combined.model_dict = self.model.to_dict()







        th = await self._ensure_thread()







        if th is None:







            return False







        ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")







        fname = f"{SNAPSHOT_PREFIX}{ts}.json.gz"







        b = self.combined.to_json_bytes()







        file = discord.File(io.BytesIO(b), filename=fname)







        await th.send(content="ML combined snapshot", file=file)







        return True







""",







    "satpambot/ml/guard_hooks.py": r"""from __future__ import annotations







import discord







from .state_store_discord import MLState







from .feature_extractor import extract_tokens, dhash64, sha1k















class GuardAdvisor:







    def __init__(self, bot: discord.Client):







        self.bot = bot







        self._state = MLState(bot)







        self._loaded = False















    async def _ensure_loaded(self):







        if not self._loaded:







            try:







                await self._state.load_latest()







            except Exception:







                pass







            self._loaded = True















    def is_exempt(self, message: discord.Message) -> bool:







        if isinstance(message.channel, discord.Thread):  # Global Thread Exempt







            return True







        ex = self._state.combined.exempt







        if message.channel.id in ex.get("channels", []):







            return True







        if isinstance(message.channel, discord.Thread) and message.channel.id in ex.get("threads", []):







            return True







        return False















    async def any_image_whitelisted_async(self, message: discord.Message) -> bool:







        await self._ensure_loaded()







        wl = self._state.combined.whitelist







        if not wl:







            return False







        for a in message.attachments[:







            3]:







            if a.content_type and a.content_type.startswith("image/"):







                try:







                    b = await a.read()







                except Exception:







                    continue







                h1 = dhash64(b)







                if h1 and h1 in set(wl.get("dhash64", [])):







                    return True







                if sha1k(b) in set(wl.get("sha1k", [])):







                    return True







        return False















    async def risk_score_from_content(self, message: discord.Message) -> float:







        await self._ensure_loaded()







        tokens = extract_tokens(message.content or "", None)







        if self._state.model is None:







            return 0.5







        return float(self._state.model.predict_proba(tokens)["phish"])







""",







    "satpambot/bot/modules/discord_bot/cogs/self_learning_guard.py": r"""from __future__ import annotations







import asyncio







from typing import Optional, List, Set







import discord







from discord.ext import commands















from satpambot.ml.online_nb import OnlineNB







from satpambot.ml.feature_extractor import extract_tokens, dhash64, sha1k







from satpambot.ml.state_store_discord import MLState, MAX_MESSAGES_SCAN, MAX_ATTACH_PER_MSG







from satpambot.ml.state_store_discord import THREAD_PHISH, THREAD_WL, THREAD_BANLOG, THREAD_BLACKLIST







from satpambot.ml.phash_reconcile import collect_phash_from_log, collect_image_hashes_from_thread, split_false_positives















AUTO_BOOT = True







PHASH_HAMMING_THR = 6















class SelfLearningGuard(commands.Cog):







    def __init__(self, bot: commands.Bot):







        self.bot = bot







        self.state = MLState(bot)







        self._ready = asyncio.Event()















    @commands.Cog.listener()







    async def on_ready(self):







        if self._ready.is_set():







            return







        await self.state.load_latest()







        if AUTO_BOOT:







            await self._auto_bootstrap()







        self._ready.set()















    async def _scan_thread_tokens(self, th: discord.Thread, label: str) -> int:







        if self.state.model is None:







            self.state.model = OnlineNB()







        n = 0







        async for msg in th.history(limit=MAX_MESSAGES_SCAN, oldest_first=True):







            tokens = extract_tokens(msg.content or "", None)







            if msg.attachments:







                tokens.append("has_image")







            if tokens:







                self.state.model.learn(tokens, label)







                n += 1







        return n















    async def _scan_thread_wl(self, th: discord.Thread) -> int:







        cnt = 0







        async for msg in th.history(limit=MAX_MESSAGES_SCAN, oldest_first=True):







            for a in msg.attachments[:







                MAX_ATTACH_PER_MSG]:







                if a.content_type and a.content_type.startswith("image/"):







                    try:







                        b = await a.read()







                    except Exception:







                        continue







                    h1 = dhash64(b)







                    h2 = sha1k(b)







                    if h1 and h1 not in self.state.combined.whitelist["dhash64"]:







                        self.state.combined.whitelist["dhash64"].append(h1)







                    if h2 and h2 not in self.state.combined.whitelist["sha1k"]:







                        self.state.combined.whitelist["sha1k"].append(h2)







                    cnt += 1







        return cnt















    async def _phash_reconcile(self, log_ch: Optional[discord.TextChannel], phish_threads: List[discord.Thread]) -> int:







        if log_ch is None or not phish_threads:







            return 0







        log_hashes = await collect_phash_from_log(log_ch, limit_msgs=400)







        if not log_hashes:







            return 0







        phish_hashes: Set[str] = set()







        for th in phish_threads[:







            2]:







            phish_hashes |= await collect_image_hashes_from_thread(th, limit_msgs=250)







        tps, fps = split_false_positives(log_hashes, phish_hashes, ham_thr=PHASH_HAMMING_THR)







        wl = self.state.combined.whitelist["dhash64"]







        changed = 0







        for h in fps:







            if h not in wl:







                wl.append(h)







                changed += 1







        return changed















    async def _auto_bootstrap(self):







        parent = self.state.find_log_channel()







        if parent:







            self.state.parent_channel_id = parent.id















        phish_threads, wl_threads, banlog_threads, blacklist_threads, state_threads = self.state.classify_threads()















        for th in set(self.state.all_active_threads()):







            if th.id not in self.state.combined.exempt["threads"]:







                self.state.combined.exempt["threads"].append(th.id)







        if parent and parent.id not in self.state.combined.exempt["channels"]:







            self.state.combined.exempt["channels"].append(parent.id)















        empty_model = (self.state.model.pos_docs + self.state.model.neg_docs) == 0 if self.state.model else True







        if empty_model and phish_threads:







            await self._scan_thread_tokens(phish_threads[0], "phish")







        if empty_model and blacklist_threads:







            await self._scan_thread_tokens(blacklist_threads[0], "safe")















        if wl_threads and not (self.state.combined.whitelist["dhash64"] or self.state.combined.whitelist["sha1k"]):







            await self._scan_thread_wl(wl_threads[0])















        changed = await self._phash_reconcile(parent, phish_threads)







        if changed:







            try:







                th = await self.state._ensure_thread()







                if th:







                    await th.send(f"🧩 pHash reconcile: {changed} hash di‑whitelist (anti false positive).")







            except Exception:







                pass















        await self.state.save_snapshot()















    @commands.command(name="ml", help="Status self-learning (autoboot aktif)")







    async def ml_cmd(self, ctx: commands.Context, sub: Optional[str]=None):







        if not isinstance(ctx.author, discord.Member):







            return







        if sub in ("info","stats",None):







            m = self.state.model or OnlineNB()







            wl = self.state.combined.whitelist







            ex = self.state.combined.exempt







            await ctx.reply(f"Docs phish: {m.pos_docs}, safe: {m.neg_docs}, vocab: {len(m.vocab)}\n"







                            f"Whitelist: dhash64={len(wl['dhash64'])}, sha1k={len(wl['sha1k'])}\n"







                            f"Exempt: threads={len(ex['threads'])}, channels={len(ex['channels'])}", mention_author=False)  # noqa: E501







        elif sub == "export":







            ok = await self.state.save_snapshot()







            await ctx.reply("✅ Snapshot disimpan." if ok else "❌ Gagal simpan snapshot.", mention_author=False)















async def setup_cog(bot: commands.Bot):







    await bot.add_cog(SelfLearningGuard(bot))















def setup(bot: commands.Bot):
# moved to setup()
""",







    "scripts/smoketest_self_learning_v4.py": r"""# smoke import v4







try:







    from satpambot.bot.modules.discord_bot.cogs.self_learning_guard import SelfLearningGuard







    from satpambot.ml.guard_hooks import GuardAdvisor







    from satpambot.ml.online_nb import OnlineNB







    from satpambot.ml.state_store_discord import MLState







    from satpambot.ml.phash_reconcile import hamming_hex







    print("OK   : self-learning v4 import")







except Exception as e:







    print("FAILED self-learning v4:", e)







    raise SystemExit(1)







""",







    "scripts/smoke_all.py": r"""#!/usr/bin/env python3







# -*- coding: utf-8 -*-














import os, sys, subprocess, importlib















ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))







SCRIPTS = os.path.join(ROOT, "scripts")







PATCHES = os.path.join(ROOT, "patches")















def run_cmd(args):







    print(f"$ {' '.join(args)}")







    p = subprocess.run(args, capture_output=True, text=True)







    if p.stdout:







        print(p.stdout.rstrip())







    if p.stderr:







        print(p.stderr.rstrip(), file=sys.stderr)







    return p.returncode == 0















def try_import(modname):







    try:







        importlib.invalidate_caches()







        importlib.import_module(modname)







        print(f"OK   : import {modname}")







        return True







    except Exception as e:







        print(f"FAILED import {modname}: {e}")







        return False















def main():







    py = sys.executable







    ok = True







    print("== Smoke: all ==")







    sc = os.path.join(SCRIPTS, "smoke_cogs.py")







    if os.path.exists(sc):







        ok = run_cmd([py, sc]) and ok







    else:







        print("SKIP : scripts/smoke_cogs.py tidak ditemukan")







    cand = [







        "smoketest_self_learning_v4.py",







        "smoketest_self_learning_v3.py",







        "smoketest_self_learning_v2.py",







        "smoketest_self_learning.py",







    ]







    chosen = None







    for c in cand:







        p = os.path.join(SCRIPTS, c)







        if os.path.exists(p):







            chosen = p







            break







    if chosen:







        print(f"== self-learning :: {os.path.basename(chosen)} ==")







        ok = run_cmd([py, chosen]) and ok







    else:







        print("SKIP : smoketest_self_learning_* tidak ditemukan")







    if "--inject" in sys.argv:







        inj = os.path.join(PATCHES, "auto_inject_guard_hooks.py")







        if os.path.exists(inj):







            print("== auto-inject guard hooks ==")







            ok = run_cmd([py, inj]) and ok







        else:







            print("SKIP : patches/auto_inject_guard_hooks.py tidak ditemukan")







    print("== import checks ==")







    ok = try_import("satpambot.ml.guard_hooks") and ok







    ok = try_import("satpambot.bot.modules.discord_bot.cogs.self_learning_guard") and ok







    print("\\n== Summary ==")







    print("PASS" if ok else "FAIL")







    sys.exit(0 if ok else 1)







if __name__ == "__main__":







    main()







""",







    "patches/auto_inject_guard_hooks.py": r"""# -*- coding: utf-8 -*-







import os, re, sys















ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))







COGS = os.path.join(ROOT, "satpambot", "bot", "modules", "discord_bot", "cogs")















IMPORT_SNIP = "from satpambot.ml.guard_hooks import GuardAdvisor  # auto-injected"







PRECHECK_SNIP = (







"        # auto-injected precheck (global thread exempt + whitelist)\\n"







"        try:\\n"







"            _gadv = getattr(self, '_guard_advisor', None)\\n"







"            if _gadv is None:\\n"







"                self._guard_advisor = GuardAdvisor(self.bot)\\n"







"                _gadv = self._guard_advisor\\n"







"            from inspect import iscoroutinefunction\\n"







"            if _gadv.is_exempt(message):\\n"







"                return\\n"







"            if iscoroutinefunction(_gadv.any_image_whitelisted_async):\\n"







"                if await _gadv.any_image_whitelisted_async(message):\\n"







"                    return\\n"







"        except Exception:\\n"







"            pass\\n"







)















def looks_like_guard(path, text):







    name = os.path.basename(path).lower()







    if "self_learning_guard" in name:







        return False







    keys = ["phish","phishing","image","guard","blocklist","score"]







    if any(k in name for k in keys):







        return True







    if re.search(r"(phish|pHash|image|guard|blocklist)", text, re.I):







        return True







    return False















def already_injected(text):







    return "auto-injected precheck" in text















def inject_into_on_message(text):







    import re







    pat = re.compile(r"async\\s+def\\s+on_message\\s*\\(\\s*self\\s*,\\s*message\\s*:\\s*discord\\.Message\\s*\\)\\s*:\\s*\\n", re.I)  # noqa: E501







    m = pat.search(text)







    if not m:







        return None







    insert_at = m.end()







    return text[:insert_at] + PRECHECK_SNIP + text[insert_at:]















def ensure_import(text):







    if IMPORT_SNIP in text:







        return text







    lines = text.splitlines(True)







    for i,ln in enumerate(lines[:







        50]):







        if ln.startswith("from discord") or ln.startswith("import discord"):







            lines.insert(i+1, IMPORT_SNIP + "\\n")







            return "".join(lines)







    return IMPORT_SNIP + "\\n" + text















def main():







    if not os.path.isdir(COGS):







        print("COGS folder tidak ditemukan:", COGS)







        return 0







    changed = 0







    for fn in os.listdir(COGS):







        if not fn.endswith(".py"):







            continue







        path = os.path.join(COGS, fn)







        try:







            with open(path, "r", encoding="utf-8") as f:







                txt = f.read()







        except Exception:







            continue







        if not looks_like_guard(path, txt):







            continue







        if already_injected(txt):







            continue







        new_txt = ensure_import(txt)







        inj = inject_into_on_message(new_txt)







        if inj is None:







            continue







        with open(path, "w", encoding="utf-8") as f:







            f.write(inj)







        changed += 1







        print("Injected:", fn)







    print(f"Done. Files injected: {changed}")







    return 0















if __name__ == "__main__":







    sys.exit(main())







""",







    "requirements-optional.txt": "Pillow>=10.0.0\n",







    "README_APPLY.txt": r"""Cara pakai (tanpa zip):







1) Simpan file ini di root repo (sejajar dengan folder `satpambot/`). Nama file: apply_satpambot_patch_v4.py







2) Jalankan:







   python apply_satpambot_patch_v4.py







3) (opsional) install Pillow untuk dHash64:







   pip install Pillow







4) Jalankan smoke + inject:







   python scripts/smoke_all.py --inject







5) Jalankan bot — auto-bootstrap & pHash reconcile aktif, semua thread bebas ban.







""",







}























def write(path, content):







    os.makedirs(os.path.dirname(path), exist_ok=True)







    with open(path, "w", encoding="utf-8") as f:







        f.write(content)























def main():







    root = os.getcwd()







    created = []







    for rel, content in FILES.items():







        p = os.path.join(root, rel)







        write(p, content)







        created.append(rel)







    print("Wrote files:")







    for c in created:







        print(" -", c)







    print("\\nDone. You can now run:")







    print("  pip install -r requirements-optional.txt  # optional")







    print("  python scripts/smoke_all.py --inject")























if __name__ == "__main__":







    main()










from discord.ext import commands
async def setup(bot: commands.Bot):
    # auto-register Cog classes defined in this module
    for _name, _obj in globals().items():
        try:
            if isinstance(_obj, type) and issubclass(_obj, commands.Cog):
                await bot.add_cog(_obj(bot))
        except Exception:
            continue
