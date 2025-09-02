# -*- coding: utf-8 -*-
"""
helpers/github_sync.py
Commit file via GitHub REST API.
ENV:
  GITHUB_TOKEN (required)
  GITHUB_REPO  (owner/repo, required)
  GITHUB_BRANCH (default: main)
"""
from __future__ import annotations
import os, base64, json, urllib.request, urllib.error
from typing import Dict, Optional

GITHUB_API = "https://api.github.com"

def _headers():
    token = os.environ["GITHUB_TOKEN"]
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "satpambot-auto-lists",
    }

def _repo() -> str:
    return os.environ["GITHUB_REPO"]

def _branch() -> str:
    return os.getenv("GITHUB_BRANCH", "main")

def _get_sha_if_exists(path: str) -> Optional[str]:
    url = f"{GITHUB_API}/repos/{_repo()}/contents/{path}?ref={_branch()}"
    req = urllib.request.Request(url, headers=_headers())
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("sha")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise
    except Exception:
        return None

def _put_file(path: str, content_b: bytes, message: str, sha: Optional[str]):
    url = f"{GITHUB_API}/repos/{_repo()}/contents/{path}"
    payload = {"message": message, "content": base64.b64encode(content_b).decode("ascii"), "branch": _branch()}
    if sha:
        payload["sha"] = sha
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=_headers(), method="PUT")
    with urllib.request.urlopen(req, timeout=20) as resp:
        resp.read()

def commit_files(files: Dict[str, bytes], message: str):
    for path, content in files.items():
        sha = _get_sha_if_exists(path)
        _put_file(path, content, message, sha)
