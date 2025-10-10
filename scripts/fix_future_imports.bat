@echo off
REM Quick-fix misplaced __future__ imports and then rescan.
setlocal
set TARGET=%~1
if "%TARGET%"=="" set TARGET=.

python scripts\fix_future_imports_all.py "%TARGET%"
python scripts\scan_future_import_violations.py "%TARGET%"
endlocal
