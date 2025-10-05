# -*- coding: utf-8 -*-



"""



Freeze & Commit Requirements



----------------------------



Usage (on Render build command, after `pip install`):



    python scripts/freeze_and_commit_requirements.py --freeze-to requirements.lock.txt --also-copy-as requirements.txt







Requires ENV:



  - GITHUB_TOKEN (repo scope)



  - GITHUB_REPO  (owner/repo, e.g. yuinaz/discord-bot-railway)



  - GITHUB_BRANCH (default: main)



"""







import base64
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request


def freeze() -> str:



    out = subprocess.check_output([sys.executable, "-m", "pip", "freeze"], text=True)



    # Normalize ordering for reproducibility



    lines = [l.strip() for l in out.splitlines() if l.strip()]



    lines.sort(key=str.lower)



    return "\n".join(lines) + "\n"











def write_file(path: str, content: str):



    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)



    with open(path, "w", encoding="utf-8") as f:



        f.write(content)











def commit_file(path: str, content: str, message: str):



    token = os.environ["GITHUB_TOKEN"]



    repo = os.environ["GITHUB_REPO"]



    branch = os.getenv("GITHUB_BRANCH", "main")



    api = f"https://api.github.com/repos/{repo}/contents/{path}"







    # get sha if exists



    sha = None



    try:



        with urllib.request.urlopen(



            urllib.request.Request(



                f"{api}?ref={branch}",



                headers={



                    "Authorization": f"Bearer {token}",



                    "Accept": "application/vnd.github+json",



                    "User-Agent": "satpambot-freezer",



                },



            )



        ) as resp:



            data = json.loads(resp.read().decode("utf-8"))



            sha = data.get("sha")



    except urllib.error.HTTPError as e:



        if e.code != 404:



            raise



    # put file



    payload = {



        "message": message,



        "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),



        "branch": branch,



    }



    if sha:



        payload["sha"] = sha



    req = urllib.request.Request(



        api,



        data=json.dumps(payload).encode("utf-8"),



        method="PUT",



        headers={



            "Authorization": f"Bearer {token}",



            "Accept": "application/vnd.github+json",



            "User-Agent": "satpambot-freezer",



        },



    )



    with urllib.request.urlopen(req) as resp:



        resp.read()











def main(argv):



    # parse args



    freeze_to = "requirements.lock.txt"



    also_to = None



    for i, a in enumerate(argv):



        if a == "--freeze-to" and i + 1 < len(argv):



            freeze_to = argv[i + 1]



        if a == "--also-copy-as" and i + 1 < len(argv):



            also_to = argv[i + 1]







    content = freeze()



    write_file(freeze_to, content)



    if also_to:



        write_file(also_to, content)







    # commit back to repo



    commit_msg = f"chore(requirements): freeze {os.path.basename(freeze_to)}"



    commit_file(freeze_to, content, commit_msg)



    if also_to:



        commit_file(also_to, content, f"chore(requirements): update {os.path.basename(also_to)}")











if __name__ == "__main__":



    main(sys.argv[1:])



