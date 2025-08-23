# Append ImageHash to requirements.txt if missing
$req = 'requirements.txt'
if (!(Test-Path $req)) { throw "requirements.txt not found" }
$txt = Get-Content $req -Raw
if ($txt -notmatch '(?i)\bimagehash\b') {
  Add-Content -Path $req -Value 'ImageHash>=4.3'
  Write-Output "Added ImageHash>=4.3"
} else {
  Write-Output "ImageHash already present"
}
