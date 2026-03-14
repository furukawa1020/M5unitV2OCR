# setup_pc.ps1 - PC 環境セットアップ (Tesseract + Python パッケージ)
# 使い方: .\tools\setup_pc.ps1

Write-Host "=======================================" -ForegroundColor Cyan
Write-Host "  UnitV2 OCR - PC セットアップ"
Write-Host "======================================="
Write-Host ""

# ----- 1. Python 確認 -----
Write-Host "[1/4] Python 確認..." -ForegroundColor Yellow
$python = (Get-Command python -ErrorAction SilentlyContinue)?.Source
if (-not $python) {
    $python = (Get-Command python3 -ErrorAction SilentlyContinue)?.Source
}
if ($python) {
    $ver = & $python --version 2>&1
    Write-Host "[ OK ] Python: $ver" -ForegroundColor Green
} else {
    Write-Host "[ERR ] Python が見つかりません" -ForegroundColor Red
    Write-Host "  https://www.python.org/downloads/ からインストールしてください"
    exit 1
}

# ----- 2. pip パッケージ -----
Write-Host ""
Write-Host "[2/4] Python パッケージ確認..." -ForegroundColor Yellow
$packages = @("requests", "opencv-python", "Pillow")
foreach ($pkg in $packages) {
    $check = & $python -c "import $($pkg -replace '-','_'); print('ok')" 2>&1
    if ($check -eq "ok") {
        Write-Host "[ OK ] $pkg" -ForegroundColor Green
    } else {
        Write-Host "[INFO] $pkg インストール中..."
        & $python -m pip install $pkg --quiet
        if ($LASTEXITCODE -eq 0) {
            Write-Host "[ OK ] $pkg インストール完了" -ForegroundColor Green
        } else {
            Write-Host "[ERR ] $pkg インストール失敗" -ForegroundColor Red
        }
    }
}

# pytesseract (Tesseractが無くても pip は入れておく)
$check = & $python -c "import pytesseract; print('ok')" 2>&1
if ($check -eq "ok") {
    Write-Host "[ OK ] pytesseract" -ForegroundColor Green
} else {
    Write-Host "[INFO] pytesseract インストール中..."
    & $python -m pip install pytesseract --quiet
}

# ----- 3. Tesseract 本体 -----
Write-Host ""
Write-Host "[3/4] Tesseract OCR 確認..." -ForegroundColor Yellow

$tessPath = $null
$candidates = @(
    "tesseract",
    "C:\Program Files\Tesseract-OCR\tesseract.exe",
    "C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"
)
foreach ($c in $candidates) {
    try {
        $v = & $c --version 2>&1
        if ($v -match "tesseract") {
            $tessPath = $c
            Write-Host "[ OK ] Tesseract: $($v[0])" -ForegroundColor Green
            break
        }
    } catch {}
}

if (-not $tessPath) {
    Write-Host "[INFO] Tesseract が見つかりません"
    Write-Host "  winget でインストールを試みます..."
    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if ($winget) {
        winget install --id UB-Mannheim.TesseractOCR -e --accept-package-agreements --accept-source-agreements
        if ($LASTEXITCODE -eq 0) {
            Write-Host "[ OK ] Tesseract インストール完了" -ForegroundColor Green
            Write-Host "       新しいターミナルを開いて再実行してください"
        } else {
            Write-Host "[ERR ] winget インストール失敗" -ForegroundColor Red
        }
    } else {
        Write-Host ""
        Write-Host "  手動インストール方法:"
        Write-Host "  1. 以下の URL を開いてインストーラーをダウンロード:"
        Write-Host "     https://github.com/UB-Mannheim/tesseract/wiki"
        Write-Host "  2. インストール中に [Additional language data] で"
        Write-Host "     [Japanese] にチェックを入れる"
        Write-Host "  3. インストール後にこのスクリプトを再実行"
    }
}

# ----- 4. 日本語言語データ確認 -----
Write-Host ""
Write-Host "[4/4] Tesseract 日本語データ確認..." -ForegroundColor Yellow

$tessDataDirs = @(
    "C:\Program Files\Tesseract-OCR\tessdata",
    "C:\Program Files (x86)\Tesseract-OCR\tessdata"
)
$jpnFound = $false
foreach ($dir in $tessDataDirs) {
    if (Test-Path "$dir\jpn.traineddata") {
        Write-Host "[ OK ] jpn.traineddata: $dir" -ForegroundColor Green
        $jpnFound = $true
        break
    }
}

if (-not $jpnFound) {
    Write-Host "[INFO] jpn.traineddata が見つかりません"
    
    # ダウンロードを試みる
    $tessdata = $tessDataDirs | Where-Object { Test-Path $_ } | Select-Object -First 1
    if ($tessdata) {
        Write-Host "  日本語データをダウンロード中..."
        $jpnUrl = "https://github.com/tesseract-ocr/tessdata/raw/main/jpn.traineddata"
        try {
            Invoke-WebRequest -Uri $jpnUrl -OutFile "$tessdata\jpn.traineddata" -UseBasicParsing
            Write-Host "[ OK ] jpn.traineddata をダウンロードしました" -ForegroundColor Green
        } catch {
            Write-Host "[ERR ] ダウンロード失敗: $_" -ForegroundColor Red
            Write-Host ""
            Write-Host "  手動でダウンロードしてください:"
            Write-Host "  URL: $jpnUrl"
            Write-Host "  保存先: $tessdata\"
        }
    } else {
        Write-Host "[INFO] Tesseract インストール先が不明 - インストール後に再実行"
    }
}

# ----- 完了 -----
Write-Host ""
Write-Host "======================================="
Write-Host "  セットアップ完了"
Write-Host "======================================="
Write-Host ""
Write-Host "  次のステップ:"
Write-Host "  1. UnitV2 の WiFi に接続:"
Write-Host "     .\tools\connect_wifi.ps1"
Write-Host ""
Write-Host "  2. OCR を実行:"
Write-Host "     python pc_ocr.py"
Write-Host ""
Write-Host "  または USB で直接接続 → SR9900 ドライバについては README を参照"
Write-Host ""
