import os, json, asyncio

class UpstashClient:
    def __init__(self):
        self.base = os.getenv("UPSTASH_REDIS_REST_URL","").rstrip("/")
        self.token = os.getenv("UPSTASH_REDIS_REST_TOKEN","")
        self.enabled = bool(self.base and self.token and os.getenv("KV_BACKEND","").lower()=="upstash_rest")

    async def get(self, session, key: str):
        if not self.enabled: return None
        import aiohttp
        headers = {"Authorization": f"Bearer {self.token}"}
        try:
            async with session.get(f"{self.base}/get/{key}", headers=headers, timeout=15) as r:
                r.raise_for_status()
                j = await r.json()
                return j.get("result")
        except Exception:
            return None

    async def pipeline(self, session, commands):
        if not self.enabled: return None
        import aiohttp
        headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
        try:
            async with session.post(f"{self.base}/pipeline", headers=headers, json=commands, timeout=15) as r:
                r.raise_for_status()
                try:
                    return await r.json()
                except Exception:
                    return True
        except Exception:
            return None
