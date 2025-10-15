param([string]$Target=".")
python scripts/fix_future_imports_all.py $Target
python scripts/scan_future_import_violations.py $Target
