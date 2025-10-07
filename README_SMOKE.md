# Local Smoke Commands (Windows-friendly)

## PowerShell (disarankan di Windows)
```powershell
.\scripts\smoke_local.ps1
```

## Git Bash / macOS / Linux
```bash
bash scripts/smoke_local.sh
```

## Manual
```powershell
$env:PYTHONIOENCODING="utf-8"
python scripts\smoke_env.py
python scripts\smoke_local_all.py
```

### Catatan
- Script ini memaksa **UTF-8** untuk mencegah error `UnicodeEncodeError: 'cp932'`.
- `smoke_env.py` memberi timeout 20 detik pada `pip list --outdated` supaya tidak hang di beberapa lingkungan Windows.
