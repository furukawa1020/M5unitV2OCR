# UnitV2 OCR アップロード＆実行スクリプト (オフライン版)
# 使い方: .\tools\run_ocr.ps1

$ADB = "C:\platform-tools\adb.exe"
$UNITV2_IP = "10.254.239.1"
$UNITV2_PORT = "5555"
$ADB_TARGET = "${UNITV2_IP}:${UNITV2_PORT}"
$FILES_DIR = "unitv2"

Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  UnitV2 OCR アップロード＆実行" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# adb 確認
if (-not (Test-Path $ADB)) {
    Write-Host "[ERR] adb が見つかりません: $ADB" -ForegroundColor Red
    Write-Host "      C:\platform-tools\adb.exe を確認してください" -ForegroundColor Red
    exit 1
}
Write-Host "[ OK ] adb: $ADB" -ForegroundColor Green

# WiFi確認
Write-Host ""
Write-Host "[INFO] WiFi 接続状態:" -ForegroundColor Yellow
$ssid = (netsh wlan show interfaces | Select-String "^\s+SSID\s+:") -replace ".*:\s*", ""
if ($ssid -match "M5UV2") {
    Write-Host "[ OK ] UnitV2 AP に接続中: $ssid" -ForegroundColor Green
} else {
    Write-Host "[WARN] 現在のWiFi: $ssid" -ForegroundColor Yellow
    Write-Host "[WARN] UnitV2 AP (M5UV2_XXXX / パスワード: 12345678) に接続してください" -ForegroundColor Yellow
    Write-Host ""
    $ans = Read-Host "続けますか？ (y/N)"
    if ($ans -ne "y" -and $ans -ne "Y") { exit 0 }
}

# adb 接続
Write-Host ""
Write-Host "[INFO] UnitV2 に接続中... ($ADB_TARGET)" -ForegroundColor Yellow
& $ADB disconnect | Out-Null
$result = & $ADB connect $ADB_TARGET 2>&1
Write-Host "       $result"
if ($result -notmatch "connected") {
    Write-Host "[ERR] 接続できませんでした" -ForegroundColor Red
    Write-Host "      UnitV2 の電源と WiFi を確認してください" -ForegroundColor Red
    exit 1
}
Write-Host "[ OK ] 接続成功" -ForegroundColor Green

# デバイス確認
$devices = & $ADB devices 2>&1
Write-Host "[INFO] 接続デバイス:"
Write-Host "       $devices"

# ファイルアップロード
Write-Host ""
Write-Host "[INFO] ファイルをアップロード中..." -ForegroundColor Yellow

$uploadFiles = @(
    @{ src = "$FILES_DIR\main.py";              dst = "/root/main.py" },
    @{ src = "$FILES_DIR\config_unitv2.py";     dst = "/root/config_unitv2.py" },
    @{ src = "$FILES_DIR\setup_tesseract.sh";   dst = "/root/setup_tesseract.sh" }
)

foreach ($f in $uploadFiles) {
    if (Test-Path $f.src) {
        $r = & $ADB push $f.src $f.dst 2>&1
        Write-Host "[ OK ] $($f.src) -> $($f.dst)" -ForegroundColor Green
    } else {
        Write-Host "[ERR] ファイルが見つかりません: $($f.src)" -ForegroundColor Red
    }
}

# Tesseract 確認
Write-Host ""
Write-Host "[INFO] Tesseract インストール状態を確認..." -ForegroundColor Yellow
$tessVer = & $ADB shell "tesseract --version 2>&1 | head -1" 2>&1
if ($tessVer -match "tesseract") {
    Write-Host "[ OK ] Tesseract インストール済み: $tessVer" -ForegroundColor Green
} else {
    Write-Host "[WARN] Tesseract が未インストールです" -ForegroundColor Yellow
    $ans = Read-Host "セットアップスクリプトを実行しますか？ (y/N)"
    if ($ans -eq "y" -or $ans -eq "Y") {
        Write-Host "[INFO] setup_tesseract.sh を実行中..." -ForegroundColor Yellow
        & $ADB shell "chmod +x /root/setup_tesseract.sh && sh /root/setup_tesseract.sh"
    } else {
        Write-Host "[INFO] config_unitv2.py の OCR_ENGINE を 'opencv' に変更して続行" -ForegroundColor Yellow
        & $ADB shell "sed -i 's/OCR_ENGINE = .*/OCR_ENGINE = \"opencv\"/' /root/config_unitv2.py"
        Write-Host "[ OK ] OpenCV フォールバックモードに切り替えました" -ForegroundColor Green
    }
}

# OCR 実行
Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  OCR 開始！ (停止: Ctrl+C)" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""
& $ADB shell "cd /root && python3 /root/main.py"