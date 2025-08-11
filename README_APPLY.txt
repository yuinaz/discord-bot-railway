HOW TO APPLY (Windows PowerShell):
1) Put 'minimal_patch_kit.zip' in your project root (same level as 'modules' folder).
2) Extract with overwrite:
   Expand-Archive -Path .\minimal_patch_kit.zip -DestinationPath . -Force
3) Commit & push:
   git add .
   git commit -m "apply: minimal patch kit (status embed upsert, sbwho/heartbeat, NSFW autoban, OCR MrBeast/$2500)"
   git push

Linux/macOS:
   unzip -o minimal_patch_kit.zip -d .
