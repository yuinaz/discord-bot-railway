# -*- coding: utf-8 -*-



"""



scripts/migrate_lists.py



Satukan sumber lama → standar:



- data/whitelist_domains.json (list[str])



- data/blacklist_domains.json (list[str])



- data/url_whitelist.json     {"allow":[...]}



- data/url_blocklist.json     {"domains":[...]}



"""







import json
import re
from pathlib import Path


def norm(d: str) -> str:



    d = d.strip().lower().lstrip(".")



    d = re.sub(r"^https?://", "", d)



    d = d.split("/")[0]



    return d if "." in d else ""











def read_any(p: Path):



    if not p.exists():



        return []



    try:



        data = json.loads(p.read_text(encoding="utf-8"))



        if isinstance(data, list):



            return [norm(str(x)) for x in data]



        if isinstance(data, dict):



            out = []



            if "allow" in data and isinstance(data["allow"], list):



                out += [norm(str(x)) for x in data["allow"]]



            if "domains" in data and isinstance(data["domains"], list):



                out += [norm(str(x)) for x in data["domains"]]



            return out



    except Exception:



        pass



    return []











def main():



    data_dir = Path("data")



    data_dir.mkdir(exist_ok=True)



    wl_file = data_dir / "whitelist_domains.json"



    bl_file = data_dir / "blacklist_domains.json"



    url_wl = data_dir / "url_whitelist.json"



    url_bl = data_dir / "url_blocklist.json"







    wl = set(read_any(wl_file)) | set(read_any(url_wl))



    bl = set(read_any(bl_file)) | set(read_any(url_bl))



    bl -= wl  # whitelist menang







    wl_sorted = sorted([d for d in wl if d])



    bl_sorted = sorted([d for d in bl if d])



    wl_file.write_text(json.dumps(wl_sorted, ensure_ascii=False, indent=2), encoding="utf-8")



    bl_file.write_text(json.dumps(bl_sorted, ensure_ascii=False, indent=2), encoding="utf-8")



    url_wl.write_text(json.dumps({"allow": wl_sorted}, ensure_ascii=False, indent=2), encoding="utf-8")



    url_bl.write_text(json.dumps({"domains": bl_sorted}, ensure_ascii=False, indent=2), encoding="utf-8")



    print(f"[OK] WL={len(wl_sorted)} → {wl_file}")



    print(f"[OK] BL={len(bl_sorted)} → {bl_file}")











if __name__ == "__main__":



    main()



