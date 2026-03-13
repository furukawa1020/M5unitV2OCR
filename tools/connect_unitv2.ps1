# UnitV2 接続ツール (PowerShell)
#
# 使い方:
#   .\tools\connect_unitv2.ps1 -IPAddress 192.168.1.100

param(
    [Parameter(Mandatory=$false)]
    [string]$IPAddress = "",
    
    [Parameter(Mandatory=$false)]
    [string]$Port = "5555"
)

$ErrorActionPreference = "Stop"

Write-Host "=================================" -ForegroundColor Cyan
Write-Host "UnitV2 Connection Tool" -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan
Write-Host ""

# adbコマンドの確認
try {
    $null = Get-Command adb -ErrorAction Stop
} catch {
    Write-Host "Error: adb not found!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please install Android Platform Tools:" -ForegroundColor Yellow
    Write-Host "https://developer.android.com/tools/releases/platform-tools" -ForegroundColor Yellow
    Write-Host ""
    
    Write-Host "Or install via Chocolatey:" -ForegroundColor Yellow
    Write-Host "  choco install adb" -ForegroundColor Cyan
    Write-Host ""
    exit 1
}

# IPアドレスが指定されていない場合は入力を求める
if ($IPAddress -eq "") {
    Write-Host "Enter UnitV2 IP Address:" -ForegroundColor Yellow
    Write-Host "(You can find it on UnitV2's display or Web UI)" -ForegroundColor Gray
    $IPAddress = Read-Host "IP Address"
    
    if ($IPAddress -eq "") {
        Write-Host "Error: IP address required" -ForegroundColor Red
        exit 1
    }
}

# 接続
Write-Host ""
Write-Host "Connecting to $IPAddress..." -ForegroundColor Yellow

try {
    & adb disconnect | Out-Null  # 既存接続をクリア
    Start-Sleep -Milliseconds 500
    
    $result = & adb connect "${IPAddress}:${Port}" 2>&1
    Write-Host $result -ForegroundColor Green
    
    Start-Sleep -Seconds 2
    
    # 接続確認
    Write-Host ""
    Write-Host "Connected devices:" -ForegroundColor Yellow
    & adb devices -l
    
    Write-Host ""
    Write-Host "=================================" -ForegroundColor Cyan
    Write-Host "Connection successful!" -ForegroundColor Green
    Write-Host "=================================" -ForegroundColor Cyan
    Write-Host ""
    
    Write-Host "Available commands:" -ForegroundColor Yellow
    Write-Host "  adb shell                          - Open shell" -ForegroundColor Cyan
    Write-Host "  adb push <local> <remote>          - Upload file" -ForegroundColor Cyan
    Write-Host "  adb pull <remote> <local>          - Download file" -ForegroundColor Cyan
    Write-Host "  adb shell python3 /root/main.py    - Run program" -ForegroundColor Cyan
    Write-Host "  adb logcat                         - View logs" -ForegroundColor Cyan
    Write-Host "  adb disconnect                     - Disconnect" -ForegroundColor Cyan
    Write-Host ""
    
    # メニュー
    Write-Host "What would you like to do?" -ForegroundColor Yellow
    Write-Host "  1) Open shell" -ForegroundColor Cyan
    Write-Host "  2) Upload program" -ForegroundColor Cyan
    Write-Host "  3) Run program" -ForegroundColor Cyan
    Write-Host "  4) View system info" -ForegroundColor Cyan
    Write-Host "  5) Exit" -ForegroundColor Cyan
    Write-Host ""
    
    $choice = Read-Host "Select (1-5)"
    
    switch ($choice) {
        "1" {
            Write-Host ""
            Write-Host "Opening shell... (type 'exit' to close)" -ForegroundColor Yellow
            & adb shell
        }
        "2" {
            Write-Host ""
            Write-Host "Running upload script..." -ForegroundColor Yellow
            $uploadScript = Join-Path $PSScriptRoot "upload_to_unitv2.ps1"
            if (Test-Path $uploadScript) {
                & $uploadScript -IPAddress $IPAddress
            } else {
                Write-Host "Error: upload_to_unitv2.ps1 not found" -ForegroundColor Red
            }
        }
        "3" {
            Write-Host ""
            Write-Host "Running program... (Press Ctrl+C to stop)" -ForegroundColor Yellow
            & adb shell "python3 /root/main.py"
        }
        "4" {
            Write-Host ""
            Write-Host "=== System Information ===" -ForegroundColor Cyan
            Write-Host ""
            Write-Host "Hostname:" -ForegroundColor Yellow
            & adb shell "hostname"
            Write-Host ""
            Write-Host "IP Address:" -ForegroundColor Yellow
            & adb shell "ifconfig wlan0 | grep 'inet addr'"
            Write-Host ""
            Write-Host "Memory:" -ForegroundColor Yellow
            & adb shell "free -h"
            Write-Host ""
            Write-Host "Disk Usage:" -ForegroundColor Yellow
            & adb shell "df -h /"
            Write-Host ""
            Write-Host "Python Version:" -ForegroundColor Yellow
            & adb shell "python3 --version"
            Write-Host ""
        }
        "5" {
            Write-Host "Exiting..." -ForegroundColor Yellow
        }
        default {
            Write-Host "Invalid choice" -ForegroundColor Red
        }
    }
    
} catch {
    Write-Host ""
    Write-Host "Connection failed!" -ForegroundColor Red
    Write-Host "Error: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "Troubleshooting:" -ForegroundColor Yellow
    Write-Host "  - Check UnitV2 is powered on" -ForegroundColor Gray
    Write-Host "  - Verify WiFi connection" -ForegroundColor Gray
    Write-Host "  - Confirm IP address: $IPAddress" -ForegroundColor Gray
    Write-Host "  - Try ping: ping $IPAddress" -ForegroundColor Gray
    Write-Host ""
    exit 1
}
