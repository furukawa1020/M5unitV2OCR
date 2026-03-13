# adb installer
Write-Host "adb check..." -ForegroundColor Yellow
try {
    adb version 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "adb is installed!" -ForegroundColor Green
        exit 0
    }
} catch {}

Write-Host "Installing adb..." -ForegroundColor Yellow
$url = "https://dl.google.com/android/repository/platform-tools-latest-windows.zip"
$zip = "$env:TEMP\platform-tools.zip"
Invoke-WebRequest -Uri $url -OutFile $zip
Expand-Archive -Path $zip -DestinationPath "C:\" - Force
$env:Path += ";C:\platform-tools"
[Environment]::SetEnvironmentVariable("Path", $env:Path, "User")
Write-Host "Done!" -ForegroundColor Green
