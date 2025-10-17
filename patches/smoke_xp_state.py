
import os, asyncio, json, socket
import httpx, sys

BASE = os.getenv("UPSTASH_REDIS_REST_URL", "").rstrip("/")
TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN", "")

async def pipeline(cmds):
    headers = {"Authorization": f"Bearer {TOKEN}"}
    async with httpx.AsyncClient(timeout=30) as cli:
        r = await cli.post(f"{BASE}/pipeline", headers=headers, json={"commands": cmds})
        r.raise_for_status()
        return r.json()

async def main(uid: int):
    host = ""
    try:
        host = BASE.split("//",1)[1].split("/",1)[0]
        socket.gethostbyname(host)
    except Exception as e:
        print(f"ERROR: DNS gagal untuk host '{host}': {e}")
        print("Hint: Periksa apakah UPSTASH_REDIS_REST_URL salah/ber-quote/ada spasi.")
        return

    print(f"[xp-smoke] Base URL : {BASE}")
    print(f"[xp-smoke] Token    : set({len(TOKEN)} chars)")
    cmds = [
        ["GET","xp:store"],
        ["GET","xp:bot:senior_total"],
        ["GET","xp:ladder:TK"],
    ]
    try:
        data = await pipeline(cmds)
        print("[xp-smoke] pipeline OK")
        store = json.loads(data[0]["result"]) if data[0].get("result") else {}
        print("  - xp:store:", json.dumps(store)[:900])
        print(f"  - xp:bot:senior_total: {data[1].get('result')}")
        print(f"  - xp:ladder:TK: {data[2].get('result')}")
    except httpx.HTTPStatusError as e:
        print("HTTP ERROR:", e.response.status_code, e.response.text)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        asyncio.run(main(int(sys.argv[1])))
    else:
        asyncio.run(main(0))
