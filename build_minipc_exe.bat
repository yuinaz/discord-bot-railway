@echo off
setlocal

rem --- bersih opsional ---
if exist build rd /s /q build
if exist dist rd /s /q dist

rem --- pastikan pyinstaller terpasang ---
py -m pip install --upgrade pyinstaller

rem --- build onefile ---
py -m PyInstaller ^
  run_minipc.py ^
  --name SatpamMiniPC ^
  --onefile ^
  --clean ^
  --collect-all satpambot ^
  --collect-submodules satpambot.bot.modules.discord_bot.cogs ^
  --copy-metadata discord ^
  --copy-metadata discord.py ^
  --add-data "SatpamBot.env;."

echo.
echo ✅ Build selesai. Jalankan: .\dist\SatpamMiniPC.exe
endlocal
