
from __future__ import annotations
import aiohttp, asyncio, base64, logging, os
from typing import Optional, Tuple

log = logging.getLogger(__name__)

class GitHubClient:
    def __init__(self, token: Optional[str] = None, timeout: float = 3.5):
        self.token = (token or os.getenv("GITHUB_TOKEN","")).strip()
        self.timeout = aiohttp.ClientTimeout(total=timeout)

    def _headers(self):
        h = {"Accept": "application/vnd.github+json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    async def _get(self, url: str):
        async with aiohttp.ClientSession(timeout=self.timeout) as s:
            async with s.get(url, headers=self._headers()) as r:
                if r.status == 200:
                    return await r.json()
                return None

    async def _put(self, url: str, json_body: dict):
        async with aiohttp.ClientSession(timeout=self.timeout) as s:
            async with s.put(url, headers=self._headers(), json=json_body) as r:
                if r.status in (200,201):
                    return await r.json()
                txt = await r.text()
                log.debug("GitHub PUT %s -> %s %s", url, r.status, txt[:300])
                return None

    async def put_file(self, repo: str, path: str, content_bytes: bytes, commit_message: str, branch: Optional[str] = None):
        # repo in "owner/name"
        if not repo or "/" not in repo:
            return False, "invalid-repo"
        b64 = base64.b64encode(content_bytes).decode("ascii")
        url = f"https://api.github.com/repos/{repo}/contents/{path.lstrip('/')}"
        sha = None
        try:
            current = await self._get(url + (f"?ref={branch}" if branch else ""))
            if current and isinstance(current, dict) and current.get("sha"):
                sha = current["sha"]
        except Exception:
            pass
        body = {"message": commit_message, "content": b64}
        if branch:
            body["branch"] = branch
        if sha:
            body["sha"] = sha
        data = await self._put(url, body)
        return (data is not None), ("ok" if data else "failed")
