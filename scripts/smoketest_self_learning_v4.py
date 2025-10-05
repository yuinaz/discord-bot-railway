# smoke import v4



import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))







try:



    print("OK   : self-learning v4 import")



except Exception as e:



    print("FAILED self-learning v4:", e)



    raise SystemExit(1)



