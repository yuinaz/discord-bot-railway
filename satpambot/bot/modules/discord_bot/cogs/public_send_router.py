def _get_conf():
    try:
        from satpambot.config.compat_conf import get_conf
        return get_conf
    except Exception:
        try:
            from satpambot.config.runtime_memory import get_conf
            return get_conf
        except Exception:
            def _f(): return {}
            return _f

import discord
from discord.ext import commands

class PublicSendRouter(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.cfg = _get_conf()()
        self.allow_ids = set()
        for s in str(self.cfg.get("SHADOW_PUBLIC_ALLOWLIST_IDS", "")).split(","):
            s = s.strip()
            if s.isdigit(): self.allow_ids.add(int(s))
        self.log_id = int(str(self.cfg.get("LOG_CHANNEL_ID", "0")) or 0)
        self.thread_name = str(self.cfg.get("ROUTE_DEFAULT_TARGET_THREAD_NAME","neuro-lite progress"))
        self.create_ok = str(self.cfg.get("ROUTE_DEFAULT_TARGET_CREATE","1")) == "1"
        self.force_all = str(self.cfg.get("ROUTE_FORCE_ALL","1")) == "1"
        self._patch()

    def _patch(self):
        orig_send = discord.abc.Messageable.send
        router = self

        async def send_routed(self_msg, *args, **kwargs):
            ch = getattr(self_msg, "channel", None) or self_msg
            ch_id = int(getattr(ch, "id", 0) or 0)
            if (not router.force_all) and (ch_id in router.allow_ids or ch_id == router.log_id):
                return await orig_send(self_msg, *args, **kwargs)

            target = router.bot.get_channel(router.log_id) if router.log_id else None
            if target is None:
                return await orig_send(self_msg, *args, **kwargs)

            if isinstance(target, discord.TextChannel):
                try:
                    for th in target.threads:
                        if str(th.name).strip().lower() == router.thread_name.lower():
                            target = th; break
                    else:
                        if router.create_ok and hasattr(target, "create_thread"):
                            th = await target.create_thread(name=router.thread_name, auto_archive_duration=1440)
                            target = th
                except Exception:
                    pass

            content = kwargs.get("content")
            prefix = f"[routed from #{getattr(ch,'name','?')}] "
            kwargs["content"] = (prefix + content) if isinstance(content, str) else prefix
            return await orig_send(target, *args, **kwargs)

        discord.abc.Messageable.send = send_routed

async def setup(bot: commands.Bot):
    await bot.add_cog(PublicSendRouter(bot))
