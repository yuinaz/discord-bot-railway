@echo off
setlocal
set "PYPATH=C:\Users\crazy\AppData\Local\Programs\Python\Python310\python.exe"
if not exist "%PYPATH%" (
  echo [ERROR] Python not found at: %PYPATH%
  pause
  exit /b 1
)
"%PYPATH%" -m pip install -U faster-whisper "huggingface_hub[hf_transfer]" nvidia-cudnn-cu12 nvidia-cublas-cu12

set "_TMP=%TEMP%\_sitepkg.txt"
"%PYPATH%" -c "import sysconfig,site; print(sysconfig.get_paths().get('platlib') or sysconfig.get_paths().get('purelib') or site.getusersitepackages())" > "%_TMP%"
set /p SITE=<"%_TMP%"
del "%_TMP%" >nul 2>&1
set "NV=%SITE%\nvidia"

if exist "%NV%\cudnn\bin" setx PATH "%PATH%;%NV%\cudnn\bin" >nul
if exist "%NV%\cublas\bin" setx PATH "%PATH%;%NV%\cublas\bin" >nul
echo Done. Close ^& reopen terminal, then run scripts\verify_cuda_sitepkg.bat
endlocal
