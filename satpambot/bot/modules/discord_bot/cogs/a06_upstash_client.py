
import os
import json
import urllib.parse
from typing import Any, Dict, List, Optional

try:
    import httpx  # type: ignore
except Exception:  # pragma: no cover
    httpx = None

DEFAULT_TIMEOUT = 8.0

class UpstashRedis:
    """
    Minimal Upstash REST client (async). Uses /pipeline for safety (POST body),
    falling back to GET endpoints for simple commands.
    """
    def __init__(self, url: str, token: str, timeout: float = DEFAULT_TIMEOUT):
        self.url = url.rstrip("/")
        self.token = token
        self.timeout = timeout

    def ok(self) -> bool:
        return bool(self.url and self.token and httpx is not None)

    async def _post(self, path: str, json_body: Any) -> Any:
        if not self.ok():
            raise RuntimeError("UpstashRedis not initialized or httpx missing")
        headers = {"Authorization": f"Bearer {self.token}"}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.post(self.url + path, headers=headers, json=json_body)
            r.raise_for_status()
            try:
                return r.json()
            except Exception:
                return {"result": r.text}

    async def _get(self, path: str) -> Any:
        if not self.ok():
            raise RuntimeError("UpstashRedis not initialized or httpx missing")
        headers = {"Authorization": f"Bearer {self.token}"}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.get(self.url + path, headers=headers)
            r.raise_for_status()
            try:
                return r.json()
            except Exception:
                return {"result": r.text}

    async def pipeline(self, commands: List[List[str]]) -> Any:
        return await self._post("/pipeline", commands)

    async def get_raw(self, key: str) -> Optional[str]:
        k = urllib.parse.quote(key, safe="")
        data = await self._get(f"/get/{k}")
        return data.get("result")

    async def set_raw(self, key: str, value: str) -> bool:
        # Use pipeline to avoid URL length limits
        resp = await self.pipeline([["SET", key, value]])
        try:
            return (resp and isinstance(resp, list) and resp[0].get("result") == "OK")
        except Exception:
            return False

    async def get_json(self, key: str) -> Optional[dict]:
        raw = await self.get_raw(key)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except Exception:
            return None

    async def set_json(self, key: str, value: dict) -> bool:
        raw = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        return await self.set_raw(key, raw)

def discover_from_env() -> Optional[UpstashRedis]:
    url = os.getenv("UPSTASH_REDIS_REST_URL") or os.getenv("UPSTASH_URL")
    token = os.getenv("UPSTASH_REDIS_REST_TOKEN") or os.getenv("UPSTASH_TOKEN")
    if url and token:
        return UpstashRedis(url=url, token=token)
    return None
