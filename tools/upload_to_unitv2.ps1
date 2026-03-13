# UnitV2 アップロードスクリプト (PowerShell)
# 
# 使い方:
#   .\tools\upload_to_unitv2.ps1 -IPAddress 192.168.1.100
#   .\tools\upload_to_unitv2.ps1 -IPAddress 192.168.1.100 -Run

param(
    [Parameter(Mandatory=$true)]
    [string]$IPAddress,
    
    [Parameter(Mandatory=$false)]
    [switch]$Run = $false,
    
    [Parameter(Mandatory=$false)]
    [string]$Port = "5555"
)

$ErrorActionPreference = "Stop"

Write-Host "=================================" -ForegroundColor Cyan
Write-Host "UnitV2 Upload Tool" -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan
Write-Host ""

# adbコマンドの確認
Write-Host "[1/5] Checking adb..." -ForegroundColor Yellow
try {
    $adbPath = Get-Command adb -ErrorAction SilentlyContinue
    if (!$adbPath) {
        throw "adb not found"
    }
    Write-Host "  adb found: $($adbPath.Source)" -ForegroundColor Green
} catch {
    Write-Host "  Error: adb not found!" -ForegroundColor Red
    Write-Host ""
    Write-Host "  Please install Android Platform Tools:" -ForegroundColor Yellow
    Write-Host "  https://developer.android.com/tools/releases/platform-tools" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

# UnitV2に接続
Write-Host ""
Write-Host "[2/5] Connecting to UnitV2 at $IPAddress..." -ForegroundColor Yellow
try {
    $result = & adb connect "${IPAddress}:${Port}" 2>&1
    Write-Host "  $result" -ForegroundColor Green
    
    # 少し待機
    Start-Sleep -Seconds 2
    
    # 接続確認
    $devices = & adb devices
    if ($devices -notmatch $IPAddress) {
        throw "Connection failed"
    }
    
} catch {
    Write-Host "  Error: Could not connect to UnitV2!" -ForegroundColor Red
    Write-Host "  Make sure:" -ForegroundColor Yellow
    Write-Host "  - UnitV2 is powered on" -ForegroundColor Yellow
    Write-Host "  - WiFi is connected" -ForegroundColor Yellow
    Write-Host "  - IP address is correct: $IPAddress" -ForegroundColor Yellow
    Write-Host ""
    exit 1
}

# ファイルをアップロード
Write-Host ""
Write-Host "[3/5] Uploading files..." -ForegroundColor Yellow

$files = @(
    @{Local="unitv2\main.py"; Remote="/root/main.py"},
    @{Local="unitv2\config_unitv2.py"; Remote="/root/config_unitv2.py"}
)

foreach ($file in $files) {
    $localPath = Join-Path $PSScriptRoot "..\$($file.Local)"
    
    if (Test-Path $localPath) {
        Write-Host "  Uploading $($file.Local)..." -ForegroundColor Cyan
        try {
            & adb push $localPath $file.Remote | Out-Null
            Write-Host "    OK" -ForegroundColor Green
        } catch {
            Write-Host "    Failed: $_" -ForegroundColor Red
        }
    } else {
        Write-Host "  Warning: $localPath not found" -ForegroundColor Yellow
    }
}

# アップロード完了
Write-Host ""
Write-Host "[4/5] Upload complete!" -ForegroundColor Green

# 実行
if ($Run) {
    Write-Host ""
    Write-Host "[5/5] Running program on UnitV2..." -ForegroundColor Yellow
    Write-Host "  Press Ctrl+C to stop" -ForegroundColor Yellow
    Write-Host ""
    
    try {
        & adb shell "python3 /root/main.py"
    } catch {
        Write-Host "  Stopped" -ForegroundColor Yellow
    }
} else {
    Write-Host ""
    Write-Host "[5/5] To run the program:" -ForegroundColor Yellow
    Write-Host "  adb shell python3 /root/main.py" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Or use:" -ForegroundColor Yellow
    Write-Host "  .\tools\upload_to_unitv2.ps1 -IPAddress $IPAddress -Run" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "=================================" -ForegroundColor Cyan
Write-Host "Done!" -ForegroundColor Green
Write-Host "=================================" -ForegroundColor Cyan
