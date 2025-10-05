#!/usr/bin/env python3



from pathlib import Path

print("== contents ==")



for p in Path(".").rglob("*"):



    print(p)



