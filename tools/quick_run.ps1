# UnitV2 OCR - クイック実行スクリプト
# 設定、アップロード、実行を一括で行います

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "=================================" -ForegroundColor Cyan
Write-Host " UnitV2 OCR - クイック実行" -ForegroundColor Cyan
Write-Host "=================================" -ForegroundColor Cyan
Write-Host ""

# プロジェクトルートに移動
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir
Set-Location $projectRoot

# ========================================
# ステップ 1: 設定情報を入力
# ========================================
Write-Host "[1/4] 設定情報の入力" -ForegroundColor Yellow
Write-Host ""

$unitv2IP = Read-Host "UnitV2 IPアドレス (例: 192.168.1.100)"
$wifiSSID = Read-Host "WiFi SSID"
$wifiPassword = Read-Host "WiFi パスワード"
$apiKey = Read-Host "Google API Key"

Write-Host ""

# ========================================
# ステップ 2: 設定ファイルの更新
# ========================================
Write-Host "[2/4] 設定ファイルの更新..." -ForegroundColor Yellow

$configContent = @"
"""
UnitV2 OCR 設定ファイル
"""

# WiFi設定
WIFI_SSID = "$wifiSSID"
WIFI_PASSWORD = "$wifiPassword"

# Google Cloud Vision API Key
GOOGLE_API_KEY = "$apiKey"

# カメラ設定
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480

# OCR設定
AUTO_OCR_INTERVAL = 10
OCR_TIMEOUT = 10

# デバッグ設定
DEBUG_MODE = True
"@

$configPath = Join-Path $projectRoot "unitv2\config_unitv2.py"
Set-Content -Path $configPath -Value $configContent -Encoding UTF8
Write-Host "  ✓ 設定ファイルを更新しました" -ForegroundColor Green
Write-Host ""

# ========================================
# ステップ 3: UnitV2 接続とアップロード
# ========================================
Write-Host "[3/4] UnitV2 接続とアップロード..." -ForegroundColor Yellow

try {
    # adb接続
    Write-Host "  接続中..." -ForegroundColor Gray
    adb disconnect 2>&1 | Out-Null
    adb connect "${unitv2IP}:5555" | Out-Null
    Start-Sleep -Seconds 2
    
    # ファイルアップロード
    Write-Host "  main.py をアップロード..." -ForegroundColor Cyan
    adb push "unitv2\main.py" "/root/main.py" | Out-Null
    
    Write-Host "  config_unitv2.py をアップロード..." -ForegroundColor Cyan
    adb push "unitv2\config_unitv2.py" "/root/config_unitv2.py" | Out-Null
    
    Write-Host "  ✓ アップロード完了！" -ForegroundColor Green
    Write-Host ""
    
} catch {
    Write-Host "  ✗ エラー: $_" -ForegroundColor Red
    Write-Host ""
    Write-Host "確認事項:" -ForegroundColor Yellow
    Write-Host "- adb がインストールされているか" -ForegroundColor Gray
    Write-Host "- UnitV2 の電源が入っているか" -ForegroundColor Gray
    Write-Host "- WiFi に接続されているか" -ForegroundColor Gray
    Write-Host "- IP アドレスが正しいか" -ForegroundColor Gray
    Write-Host ""
    exit 1
}

# ========================================
# ステップ 4: OCR実行とリアルタイム表示
# ========================================
Write-Host "[4/4] OCR プログラム実行中..." -ForegroundColor Yellow
Write-Host ""
Write-Host "=================================" -ForegroundColor Green
Write-Host " リアルタイム出力" -ForegroundColor Green
Write-Host "=================================" -ForegroundColor Green
Write-Host ""
Write-Host "停止: Ctrl+C" -ForegroundColor Yellow
Write-Host ""

try {
    adb shell "python3 /root/main.py"
} catch {
    Write-Host ""
} finally {
    Write-Host ""
    Write-Host "=================================" -ForegroundColor Cyan
    Write-Host " 完了" -ForegroundColor Cyan  
    Write-Host "=================================" -ForegroundColor Cyan
    Write-Host ""
}
