@echo off
if not exist ".git\hooks" (echo Jalankan di root repo.& exit /b 1)
copy /Y hooks\pre-commit .git\hooks\pre-commit >NUL
copy /Y hooks\pre-commit.ps1 .git\hooks\pre-commit.ps1 >NUL
echo Hooks terpasang.
