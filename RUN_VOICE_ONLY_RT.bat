@echo off
setlocal ENABLEDELAYEDEXPANSION

REM === Absolute Python path (edit if Python ada di lokasi lain) ===
set "PYPATH=C:\Users\crazy\AppData\Local\Programs\Python\Python310\python.exe"
if not exist "%PYPATH%" (
  echo [ERROR] Python not found at: %PYPATH%
  echo Silakan install Python 3.10 di lokasi default ^(untuk user ini^) atau ubah variabel PYPATH di file .bat ini.
  pause
  exit /b 1
)

REM --- resolve site-packages via Python (tanpa here-doc) ---
set "_TMP=%TEMP%\_sitepkg.txt"
"%PYPATH%" -c "import sysconfig,site; print(sysconfig.get_paths().get('platlib') or sysconfig.get_paths().get('purelib') or site.getusersitepackages())" > "%_TMP%"
set /p SITE=<"%_TMP%"
del "%_TMP%" >nul 2>&1
if not exist "%SITE%" set "SITE=%LocalAppData%\Programs\Python\Python310\Lib\site-packages"
set "NV=%SITE%\nvidia"

echo VOICE-ONLY RT (GPU Whisper) - paling ringan, tanpa OCR

REM --- auto install cuDNN/cuBLAS jika folder bin belum ada ---
if not exist "%NV%\cudnn\bin" (
  echo [setup] installing nvidia-cudnn-cu12 ...
  "%PYPATH%" -m pip install -U -q nvidia-cudnn-cu12
)
if not exist "%NV%\cublas\bin" (
  echo [setup] installing nvidia-cublas-cu12 ...
  "%PYPATH%" -m pip install -U -q nvidia-cublas-cu12
)

REM --- tambah ke PATH proses ---
if exist "%NV%\cudnn\bin" set "PATH=%NV%\cudnn\bin;%PATH%"
if exist "%NV%\cublas\bin" set "PATH=%NV%\cublas\bin;%PATH%"

set "OCR_DISABLED=1"
set "ONNXRUNTIME_FORCE_CPU=1"
set "ORT_DISABLE_CUDA=1"
set "HF_HUB_ENABLE_HF_TRANSFER=1"
set "HF_HUB_DISABLE_SYMLINKS=1"
set "PYTHONPATH=%CD%;%CD%\app;%PYTHONPATH%"
set "PYTHONNOUSERSITE=1"

copy /Y configs\config_voice_only.toml config.toml >nul 2>nul
"%PYPATH%" app\main.py --mode voice
endlocal
