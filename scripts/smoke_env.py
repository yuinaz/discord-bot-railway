import sys, platform
from importlib import metadata

def v(pkg, fallback=None):
    try:
        return metadata.version(pkg)
    except Exception as e:
        return f"ERR({e.__class__.__name__})" if fallback is None else fallback

print("=== ENV CHECK ===")
print(f"Python: {platform.python_version()} [{platform.system()}-{platform.version().split('.',1)[0]}]")
print(f"discord.py    : {v('discord.py')}")
print(f"flask         : {v('Flask')}")
print(f"aiohttp       : {v('aiohttp')}")
print(f"httpx         : {v('httpx')}")
print(f"groq          : {v('groq')}")
print(f"numpy         : {v('numpy')}")
print(f"psutil        : {v('psutil')}")
print(f"Pillow        : {v('Pillow')}")
print(f"tzdata        : {v('tzdata', 'bundled')}")
print(f"googletrans-py: {v('googletrans-py')}")
print(f"deep-translator: {v('deep-translator')}")
print(f"langdetect    : {v('langdetect')}")
print("== COMPAT CHECK: OK ==")
