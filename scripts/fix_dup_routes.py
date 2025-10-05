import io
import re

PATH = r"satpambot/dashboard/app.py"







# fungsi-fungsi yang sering dobel



TARGETS = [



    "settings_page",



    "servers_page",



    "__api_live_fallback",



    "dashboard_alias",



    "__debug_templates",



]







with io.open(PATH, "r", encoding="utf-8", errors="ignore") as f:



    src = f.read()







lines = src.splitlines(keepends=True)











def find_blocks(funcname):



    """kembalikan list (start_idx, end_idx_exclusive) untuk tiap blok route def funcname"""



    idxs = []



    i = 0



    while True:



        i = src.find(f"def {funcname}(", i)



        if i == -1:



            break



        # cari baris indeks dari posisi i



        # hitung offset ke indeks baris



        upto = src[:i]



        line_start = upto.rfind("\n") + 1



        # tentukan batas awal blok: mundur ke atas selama baris diawali decorator '@'



        # (dan ikutkan baris kosong/comment di atasnya secukupnya)



        start = line_start



        # scan ke atas baris-per-baris



        j = src.rfind("\n", 0, start - 1)



        while j != -1:



            line_begin = j + 1



            line_text = src[line_begin : src.find("\n", line_begin) if src.find("\n", line_begin) != -1 else len(src)]



            stripped = line_text.lstrip()



            if stripped.startswith("@"):



                start = line_begin



                j = src.rfind("\n", 0, start - 1)



                continue



            break







        # tentukan akhir blok: sampai sebelum decorator berikutnya atau def berikutnya di kolom awal



        k = src.find("\n", i)



        if k == -1:



            k = len(src)



        end = len(src)



        m = re.search(r"\n(@[A-Za-z_]|def\s+[A-Za-z_])", src[i:], flags=re.M)



        if m:



            end = i + m.start()



            # pastikan end >= k



            if end < k:



                end = k



        idxs.append((start, end))



        i = end



    # convert ke indeks list lines



    res = []



    for a, b in idxs:



        # hitung indeks baris



        la = src.count("\n", 0, a)



        lb = src.count("\n", 0, b)



        res.append((la, lb + 1))  # exclusive



    return res











# kumpulkan semua blok untuk tiap fungsi



to_delete = []



for fn in TARGETS:



    blocks = find_blocks(fn)



    if len(blocks) > 1:



        # keep blok pertama, hapus sisanya



        for s, e in blocks[1:]:



            to_delete.append((s, e))







# jika tidak ada yang perlu dihapus, keluar



if not to_delete:



    print("No duplicate route blocks found.")



    raise SystemExit(0)







# gabung & hapus dari akhir agar indeks aman



to_delete.sort()



new_lines = []



cur = 0



for s, e in to_delete:



    # tambahkan bagian sebelum blok



    new_lines.extend(lines[cur:s])



    # lewati blok duplikat



    cur = e



# sisa



new_lines.extend(lines[cur:])







with io.open(PATH, "w", encoding="utf-8", newline="\n") as f:



    f.write("".join(new_lines))







print(f"Removed {len(to_delete)} duplicate route block(s).")



