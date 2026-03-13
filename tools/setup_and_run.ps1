# UnitV2 OCR - 完全自動セットアップ＆実行スクリプト
# すべての設定からアップロード、実行、リアルタイム表示まで一括実行

param(
    [Parameter(Mandatory=$false)]
    [switch]$SkipAdbCheck = $false
)

$ErrorActionPreference = "Continue"

Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "  UnitV2 OCR - 完全セットアップ" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# プロジェクトルートに移動
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptPath
Set-Location $projectRoot

Write-Host "プロジェクトフォルダ: $projectRoot" -ForegroundColor Gray
Write-Host ""

# ========================================
# ステップ 1: adb のインストール確認
# ========================================
Write-Host "[1/6] adb (Android Platform Tools) の確認..." -ForegroundColor Yellow

$adbPath = $null
$adbFound = $false

# adbコマンドを探す
try {
    $adbCmd = Get-Command adb -ErrorAction SilentlyContinue
    if ($adbCmd) {
        $adbPath = $adbCmd.Source
        $adbFound = $true
        Write-Host "  ✓ adb が見つかりました: $adbPath" -ForegroundColor Green
    }
} catch {}

if (-not $adbFound) {
    Write-Host "  ✗ adb が見つかりません" -ForegroundColor Red
    Write-Host ""
    Write-Host "  Android Platform Tools をインストールする必要があります。" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  インストール方法:" -ForegroundColor Cyan
    Write-Host "  1. 自動ダウンロード＆インストール（推奨）" -ForegroundColor White
    Write-Host "  2. 手動でダウンロード" -ForegroundColor White
    Write-Host "  3. スキップ（既にインストール済みの場合）" -ForegroundColor White
    Write-Host ""
    
    $choice = Read-Host "  選択してください (1-3)"
    
    switch ($choice) {
        "1" {
            Write-Host ""
            Write-Host "  Android Platform Tools をダウンロード中..." -ForegroundColor Yellow
            
            $toolsUrl = "https://dl.google.com/android/repository/platform-tools-latest-windows.zip"
            $downloadPath = Join-Path $env:TEMP "platform-tools.zip"
            $extractPath = "C:\platform-tools"
            
            try {
                # ダウンロード
                Write-Host "  ダウンロード: $toolsUrl" -ForegroundColor Gray
                Invoke-WebRequest -Uri $toolsUrl -OutFile $downloadPath -UseBasicParsing
                
                # 解凍
                Write-Host "  解凍中..." -ForegroundColor Gray
                if (Test-Path $extractPath) {
                    Remove-Item $extractPath -Recurse -Force
                }
                Expand-Archive -Path $downloadPath -DestinationPath "C:\" -Force
                
                # 環境変数に追加
                Write-Host "  環境変数に追加中..." -ForegroundColor Gray
                $currentPath = [Environment]::GetEnvironmentVariable("Path", "User")
                if ($currentPath -notlike "*$extractPath*") {
                    [Environment]::SetEnvironmentVariable("Path", "$currentPath;$extractPath", "User")
                }
                
                # セッションのPATHを更新
                $env:Path += ";$extractPath"
                
                Write-Host "  ✓ インストール完了！" -ForegroundColor Green
                $adbPath = Join-Path $extractPath "adb.exe"
                $adbFound = $true
                
                # クリーンアップ
                Remove-Item $downloadPath -Force
                
            } catch {
                Write-Host "  ✗ ダウンロード失敗: $_" -ForegroundColor Red
                Write-Host ""
                Write-Host "  手動でインストールしてください:" -ForegroundColor Yellow
                Write-Host "  https://developer.android.com/tools/releases/platform-tools" -ForegroundColor Cyan
                exit 1
            }
        }
        "2" {
            Write-Host ""
            Write-Host "  以下のURLから Android Platform Tools をダウンロードしてください:" -ForegroundColor Yellow
            Write-Host "  https://developer.android.com/tools/releases/platform-tools" -ForegroundColor Cyan
            Write-Host ""
            Write-Host "  ダウンロード後、解凍して adb.exe のパスを環境変数に追加してください。" -ForegroundColor Yellow
            Write-Host "  完了したら再度このスクリプトを実行してください。" -ForegroundColor Yellow
            Write-Host ""
            exit 0
        }
        "3" {
            Write-Host "  スキップします" -ForegroundColor Yellow
            $adbPath = Read-Host "  adb.exe のフルパスを入力してください"
            if (Test-Path $adbPath) {
                $adbFound = $true
            } else {
                Write-Host "  ✗ パスが見つかりません" -ForegroundColor Red
                exit 1
            }
        }
        default {
            Write-Host "  無効な選択です" -ForegroundColor Red
            exit 1
        }
    }
}

# adbコマンドのエイリアス
if ($adbPath) {
    function adb { & $adbPath $args }
}

Write-Host ""

# ========================================
# ステップ 2: 設定情報の収集
# ========================================
Write-Host "[2/6] 設定情報の収集..." -ForegroundColor Yellow
Write-Host ""

# 設定ファイルを読み込んで既存の値を確認
$configPath = Join-Path $projectRoot "unitv2\config_unitv2.py"
$existingConfig = @{}

if (Test-Path $configPath) {
    $content = Get-Content $configPath -Raw
    if ($content -match 'WIFI_SSID\s*=\s*"([^\"]*)"') { $existingConfig['WIFI_SSID'] = $matches[1] }
    if ($content -match 'WIFI_PASSWORD\s*=\s*"([^\"]*)"') { $existingConfig['WIFI_PASSWORD'] = $matches[1] }
    if ($content -match 'GOOGLE_API_KEY\s*=\s*"([^\"]*)"') { $existingConfig['GOOGLE_API_KEY'] = $matches[1] }
}

Write-Host "  設定を入力してください（Enterで既存値を使用）:" -ForegroundColor Cyan
Write-Host ""

# UnitV2 IPアドレス
Write-Host "  UnitV2 IPアドレス:" -ForegroundColor White
$unitv2IP = Read-Host "  > "
if ([string]::IsNullOrWhiteSpace($unitv2IP)) {
    Write-Host "    ✗ IPアドレスは必須です" -ForegroundColor Red
    exit 1
}

# WiFi SSID
$currentSSID = $existingConfig['WIFI_SSID']
if ($currentSSID -and $currentSSID -ne "your_wifi_ssid") {
    Write-Host "  WiFi SSID (現在: $currentSSID):" -ForegroundColor White
} else {
    Write-Host "  WiFi SSID:" -ForegroundColor White
}
$wifiSSID = Read-Host "  > "
if ([string]::IsNullOrWhiteSpace($wifiSSID)) {
    $wifiSSID = $currentSSID
}

# WiFi Password
$currentPass = $existingConfig['WIFI_PASSWORD']
if ($currentPass -and $currentPass -ne "your_wifi_password") {
    Write-Host "  WiFi パスワード (現在: *****):" -ForegroundColor White
} else {
    Write-Host "  WiFi パスワード:" -ForegroundColor White
}
$wifiPassword = Read-Host "  > "
if ([string]::IsNullOrWhiteSpace($wifiPassword)) {
    $wifiPassword = $currentPass
}

# Google API Key
$currentKey = $existingConfig['GOOGLE_API_KEY']
if ($currentKey -and $currentKey -ne "your_google_api_key_here") {
    Write-Host "  Google API Key (現在: ${currentKey.Substring(0, [Math]::Min(10, $currentKey.Length))}***):" -ForegroundColor White
} else {
    Write-Host "  Google API Key:" -ForegroundColor White
}
$apiKey = Read-Host "  > "
if ([string]::IsNullOrWhiteSpace($apiKey)) {
    $apiKey = $currentKey
}

Write-Host ""
Write-Host "  ✓ 設定を収集しました" -ForegroundColor Green
Write-Host ""

# ========================================
# ステップ 3: 設定ファイルの更新
# ========================================
Write-Host "[3/6] 設定ファイルの更新..." -ForegroundColor Yellow

$newConfig = @"
"""
UnitV2 OCR 設定ファイル
"""

# WiFi設定
WIFI_SSID = "$wifiSSID"
WIFI_PASSWORD = "$wifiPassword"

# Google Cloud Vision API Key
# https://console.cloud.google.com/apis/credentials で取得
GOOGLE_API_KEY = "$apiKey"

# カメラ設定
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480

# OCR設定
AUTO_OCR_INTERVAL = 10  # 秒（自動OCR実行間隔）
OCR_TIMEOUT = 10  # 秒（API タイムアウト）

# デバッグ設定
DEBUG_MODE = True
"@

Set-Content -Path $configPath -Value $newConfig -Encoding UTF8
Write-Host "  ✓ 設定ファイルを更新しました" -ForegroundColor Green
Write-Host ""

# ========================================
# ステップ 4: UnitV2 への接続
# ========================================
Write-Host "[4/6] UnitV2 への接続..." -ForegroundColor Yellow

try {
    # 既存の接続をクリア
    & adb disconnect 2>&1 | Out-Null
    Start-Sleep -Milliseconds 500
    
    # 接続
    Write-Host "  接続中: $unitv2IP..." -ForegroundColor Gray
    $connectResult = & adb connect "${unitv2IP}:5555" 2>&1
    Write-Host "  $connectResult" -ForegroundColor Gray
    
    Start-Sleep -Seconds 2
    
    # 接続確認
    $devices = & adb devices 2>&1 | Out-String
    if ($devices -match $unitv2IP) {
        Write-Host "  ✓ UnitV2 に接続しました！" -ForegroundColor Green
    } else {
        throw "接続確認失敗"
    }
    
} catch {
    Write-Host "  ✗ UnitV2 への接続に失敗しました" -ForegroundColor Red
    Write-Host ""
    Write-Host "  確認事項:" -ForegroundColor Yellow
    Write-Host "  - UnitV2の電源が入っているか" -ForegroundColor Gray
    Write-Host "  - WiFiに接続されているか" -ForegroundColor Gray
    Write-Host "  - IPアドレスが正しいか: $unitv2IP" -ForegroundColor Gray
    Write-Host "  - ファイアウォールがブロックしていないか" -ForegroundColor Gray
    Write-Host ""
    exit 1
}

Write-Host ""

# ========================================
# ステップ 5: プログラムのアップロード
# ========================================
Write-Host "[5/6] プログラムのアップロード..." -ForegroundColor Yellow

$files = @(
    @{Local="unitv2\main.py"; Remote="/root/main.py"; Name="メインプログラム"},
    @{Local="unitv2\config_unitv2.py"; Remote="/root/config_unitv2.py"; Name="設定ファイル"}
)

$uploadSuccess = $true

foreach ($file in $files) {
    $localPath = Join-Path $projectRoot $file.Local
    
    if (Test-Path $localPath) {
        Write-Host "  アップロード: $($file.Name)..." -ForegroundColor Cyan
        try {
            $result = & adb push $localPath $file.Remote 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Host "    ✓ OK" -ForegroundColor Green
            } else {
                Write-Host "    ✗ Failed" -ForegroundColor Red
                $uploadSuccess = $false
            }
        } catch {
            Write-Host "    ✗ Error: $_" -ForegroundColor Red
            $uploadSuccess = $false
        }
    } else {
        Write-Host "  ✗ ファイルが見つかりません: $localPath" -ForegroundColor Red
        $uploadSuccess = $false
    }
}

if (-not $uploadSuccess) {
    Write-Host ""
    Write-Host "  ✗ アップロードに失敗しました" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "  ✓ すべてのファイルをアップロードしました！" -ForegroundColor Green
Write-Host ""

# ========================================
# ステップ 6: OCR プログラムの実行とリアルタイム表示
# ========================================
Write-Host "[6/6] OCR プログラムを実行します..." -ForegroundColor Yellow
Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "  UnitV2 OCR - 実行中" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  プログラムが UnitV2 で実行されています..." -ForegroundColor Green
Write-Host "  認識結果がリアルタイムで表示されます" -ForegroundColor Green
Write-Host ""
Write-Host "  停止するには Ctrl+C を押してください" -ForegroundColor Yellow
Write-Host ""
Write-Host "-----------------------------------------" -ForegroundColor Gray

try {
    # Python プログラムを実行（リアルタイム出力）
    & adb shell "python3 /root/main.py"
} catch {
    Write-Host ""
    Write-Host "  プログラムが停止しました" -ForegroundColor Yellow
} finally {
    Write-Host ""
    Write-Host "-----------------------------------------" -ForegroundColor Gray
    Write-Host ""
    Write-Host "=========================================" -ForegroundColor Cyan
    Write-Host "  完了" -ForegroundColor Cyan
    Write-Host "=========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  プログラムを再実行する場合:" -ForegroundColor Yellow
    Write-Host "  adb shell python3 /root/main.py" -ForegroundColor Cyan
    Write-Host ""
}
