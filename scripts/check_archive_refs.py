import re, sys
from pathlib import Path
pats = [r"archive[\\/]", r"original_src[\\/]", r"requirements-windows\.txt", r"templates[\\/]+templates[\\/]+"]
text_ext = {".py",".txt",".md",".ini",".cfg",".toml",".yaml",".yml",".json",".html",".htm",".env",".bat",".sh",".ps1",".service",".conf"}
issues=[]
for f in Path(".").rglob("*"):
    if not f.is_file(): continue
    if f.suffix.lower() in text_ext or f.stat().st_size < 512*1024:
        try: s = f.read_text(encoding="utf-8", errors="ignore")
        except Exception: continue
        for pat in pats:
            for m in re.finditer(pat, s, flags=re.I):
                ctx = s[max(0,m.start()-80):m.end()+80].replace("\n"," ")
                issues.append((str(f), pat, ctx))
if issues:
    print("[!] Found suspicious references:")
    for f,pat,ctx in issues:
        print(f"- {f} :: {pat} :: {ctx[:220]}")
    sys.exit(1)
print("[OK] No archive/original_src/nested templates/req-windows references found.")
