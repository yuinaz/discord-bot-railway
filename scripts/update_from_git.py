#!/usr/bin/env python
import os, subprocess, sys
def has_git():
    try:
        subprocess.check_output(['git','--version'])
        return True
    except Exception:
        return False
def main():
    if not os.path.isdir('.git') or not has_git():
        print('[git] repo or git not available, skipping'); return 0
    try:
        before = subprocess.check_output(['git','rev-parse','HEAD'], text=True).strip()
        subprocess.check_call(['git','fetch','--all','--prune'])
        subprocess.check_call(['git','pull','--ff-only'])
        after = subprocess.check_output(['git','rev-parse','HEAD'], text=True).strip()
        if before != after:
            print(f'[git] updated: {before[:7]} -> {after[:7]}'); return 1
        print('[git] no changes'); return 0
    except subprocess.CalledProcessError as e:
        print('[git] error:', e); return 2
if __name__ == '__main__':
    sys.exit(main())
