#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ensure presence override is AUTO to avoid conflicts with PresenceMoodRotator.
Creates/updates data/presence_override.json -> {"mode":"auto"}.
"""
import os, json
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA = os.path.join(ROOT, "data")
os.makedirs(DATA, exist_ok=True)
PATH = os.path.join(DATA, "presence_override.json")
obj = {"mode": "auto"}
with open(PATH, "w", encoding="utf-8") as f:
    json.dump(obj, f, ensure_ascii=False, indent=2)
print("Wrote", PATH, "->", obj)
