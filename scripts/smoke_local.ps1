# Ensure UTF-8 output to avoid UnicodeEncodeError on CP932/ANSI consoles
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"

# Prefer current 'python', fallback to 'py -3'
$py = "python"
$null = & $py -V 2>$null
if ($LASTEXITCODE -ne 0) { $py = "py -3" }

Write-Host "[+] Using Python via '$py'"
& $py scripts\smoke_env.py
& $py scripts\smoke_local_all.py
