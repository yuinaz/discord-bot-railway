#!/usr/bin/env bash
set -e
[ -d .git/hooks ] || { echo 'Jalankan di root repo.'; exit 1; }
cp -f hooks/pre-commit .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit
cp -f hooks/pre-commit.ps1 .git/hooks/pre-commit.ps1
echo 'Hooks terpasang.'
