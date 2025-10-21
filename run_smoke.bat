@echo off
setlocal enabledelayedexpansion
set PYTHONPATH=%cd%;%PYTHONPATH%
python tests\smoke_imports.py || goto :err
python scripts\xp_test\simulate_senior_progress.py || goto :err
python scripts\xp_test\whatif_label.py --xp 82290 || goto :err
echo All smoke tests passed.
goto :eof
:err
echo Smoke tests failed.
exit /b 1
