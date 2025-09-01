@echo off
setlocal ENABLEDELAYEDEXPANSION
set "PYPATH=C:\Users\crazy\AppData\Local\Programs\Python\Python310\python.exe"
if not exist "%PYPATH%" (
  echo [ERROR] Python not found at: %PYPATH%
  pause
  exit /b 1
)

set "_TMP=%TEMP%\_sitepkg.txt"
"%PYPATH%" -c "import sysconfig,site; print(sysconfig.get_paths().get('platlib') or sysconfig.get_paths().get('purelib') or site.getusersitepackages())" > "%_TMP%"
set /p SITE=<"%_TMP%"
del "%_TMP%" >nul 2>&1
if not exist "%SITE%" set "SITE=%LocalAppData%\Programs\Python\Python310\Lib\site-packages"
set "NV=%SITE%\nvidia"

echo SITE: %SITE%
echo cuDNN bin: %NV%\cudnn\bin
echo cuBLAS bin: %NV%\cublas\bin

set "_PYS=%TEMP%\verify_cuda_paths.py"
> "%_PYS%" echo import ctypes
>>"%_PYS%" echo from pathlib import Path
>>"%_PYS%" echo sitepkg = r"%SITE%"
>>"%_PYS%" echo base = Path(sitepkg)/"nvidia"
>>"%_PYS%" echo targets = [("cudnn_ops64_9.dll", base/"cudnn/bin/cudnn_ops64_9.dll"), ("cublas64_12.dll", base/"cublas/bin/cublas64_12.dll")]
>>"%_PYS%" echo for name, p in targets:
>>"%_PYS%" echo ^    print(f"{name} exists:", p.exists())
>>"%_PYS%" echo ^    if p.exists():
>>"%_PYS%" echo ^        ctypes.WinDLL(str(p)); print(" -> Load OK")
>>"%_PYS%" echo print("Done")

"%PYPATH%" "%_PYS%"
del "%_PYS%" >nul 2>&1
endlocal
