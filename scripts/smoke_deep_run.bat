@echo off
REM Run deep smoke from anywhere (Windows)
setlocal
set PYTHONUTF8=1
python "%~dp0smoke_deep.py" %*
if errorlevel 1 exit /b 1
endlocal
