# connect_usb.ps1 - USB経由でUnitV2に接続してOCRを起動
# SR9900ドライバが必要: まず .\tools\install_sr9900_driver.ps1 を実行
# 使い方: .\tools\connect_usb.ps1

param(
    [string]$IP       = "10.254.239.1",
    [string]$User     = "m5stack",
    [string]$Password = "12345678",
    [switch]$UploadFiles,   # -UploadFiles を付けると main.py をアップロード
    [switch]$RunOCR          # -RunOCR を付けると pc_ocr.py を起動
)

function Write-Status($msg, $level = "INFO") {
    $color = @{ INFO = "Cyan"; OK = "Green"; ERR = "Red"; WAIT = "Yellow" }[$level]
    if (-not $color) { $color = "White" }
    Write-Host "[$level] $msg" -ForegroundColor $color
}

$Root = Split-Path $PSScriptRoot -Parent

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  UnitV2 USB-LAN 接続チェッカー"
Write-Host "  SR9900 → $IP"
Write-Host "================================================"
Write-Host ""

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 1. SR9900 ドライバ / アダプタ確認
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Write-Status "SR9900 USB-LAN アダプタを確認中..."
$adapter = Get-PnpDevice -ErrorAction SilentlyContinue | Where-Object {
    ($_.FriendlyName -match "USB 10.100 LAN|SR9900|Corechip") -or
    ($_.InstanceId   -match "VID_0FE6")
} | Select-Object -First 1

if (-not $adapter) {
    Write-Status "SR9900 デバイスが見つかりません" "ERR"
    Write-Host ""
    Write-Host "  確認事項:"
    Write-Host "  1. UnitV2 が USB-C ケーブルで接続されているか"
    Write-Host "  2. UnitV2 の電源が入っているか"
    Write-Host "  3. ドライバがインストールされているか:"
    Write-Host "     -> .\tools\install_sr9900_driver.ps1"
    exit 1
}

if ($adapter.Status -ne "OK") {
    Write-Status "SR9900 が見つかりましたがエラー状態: $($adapter.Status)" "ERR"
    Write-Host "  デバイス: $($adapter.FriendlyName)"
    Write-Host ""
    Write-Host "  ドライバをインストールしてください:"
    Write-Host "  -> .\tools\install_sr9900_driver.ps1"
    
    Write-Host ""
    $ans = Read-Host "  強制続行しますか? (y/N)"
    if ($ans -ne "y") { exit 1 }
} else {
    Write-Status "SR9900 OK: $($adapter.FriendlyName)" "OK"
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 2. ネットワークアダプタに正しいIPが割り当てられているか
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Write-Status "ネットワークアダプタの IP を確認中..."
$netAdapters = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
               Where-Object { $_.IPAddress -match "^10\.254\." }

if ($netAdapters) {
    foreach ($addr in $netAdapters) {
        Write-Status "$($addr.InterfaceAlias): $($addr.IPAddress)" "OK"
    }
} else {
    Write-Status "10.254.x.x アドレスのアダプタが見つかりません" "WAIT"
    Write-Host ""
    Write-Host "  IP が割り当てられていない場合の対処:"
    Write-Host "  1. ネットワーク設定 → SR9900 アダプタ → IPv4 プロパティ"
    Write-Host "     IP:      10.254.239.2  (または自動取得)"
    Write-Host "     Subnet:  255.255.255.0"
    Write-Host "     Gateway: 10.254.239.1"
    Write-Host ""
    Write-Host "  または PowerShell (管理者):"
    Write-Host "  Get-NetAdapter | Where-Object { `$_.InterfaceDescription -match 'SR9900|Corechip|USB.*LAN' }"
    Write-Host "  New-NetIPAddress -InterfaceAlias '<上記の名前>' -IPAddress 10.254.239.2 -PrefixLength 24"
    Write-Host ""
    $ans = Read-Host "  続行しますか? (y/N)"
    if ($ans -ne "y") { exit 1 }
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 3. Ping テスト
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Write-Status "UnitV2 ($IP) に ping 中..."
$pingOk = $false
for ($i = 1; $i -le 5; $i++) {
    if (Test-Connection -ComputerName $IP -Count 1 -Quiet -ErrorAction SilentlyContinue) {
        $pingOk = $true
        break
    }
    Write-Status "試行 $i/5... 待機中" "WAIT"
    Start-Sleep -Seconds 3
}

if (-not $pingOk) {
    Write-Status "ping 失敗 - UnitV2 から応答なし" "ERR"
    Write-Host ""
    Write-Host "  確認:"
    Write-Host "  - UnitV2 の LED が点灯しているか確認"
    Write-Host "  - USB ケーブルがデータ通信対応か (充電専用でないか)"
    Write-Host "  - SR9900 ドライバ状態を再確認"
    exit 1
}
Write-Status "ping OK!" "OK"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 4. SSH 接続テスト
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Write-Status "SSH 接続テスト..."
$sshTestCmd = "ssh -o StrictHostKeyChecking=no -o ConnectTimeout=8 -o PasswordAuthentication=yes ${User}@${IP} echo SSH_CONNECTED"

# sshpass が使えるか確認 (Linux/WSL 由来)
$sshpass = Get-Command sshpass -ErrorAction SilentlyContinue
if ($sshpass) {
    $sshResult = & sshpass -p $Password ssh -o StrictHostKeyChecking=no -o ConnectTimeout=8 `
        "${User}@${IP}" "echo SSH_CONNECTED" 2>&1
} else {
    # パスワードは手入力を促す
    Write-Host ""
    Write-Host "  SSH パスワードを入力してください: $Password" -ForegroundColor Yellow
    Write-Host "  (コピー&ペースト可)" -ForegroundColor Yellow
    Write-Host ""
    $sshResult = & ssh -o StrictHostKeyChecking=no -o ConnectTimeout=8 ${User}@${IP} "echo SSH_CONNECTED" 2>&1
}

if ($sshResult -match "SSH_CONNECTED") {
    Write-Status "SSH 接続成功!" "OK"
} else {
    # 接続自体は可能でもパスワード失敗かもしれない
    Write-Status "SSH の結果: $sshResult" "WAIT"
    Write-Status "SSH で手動接続: ssh ${User}@${IP}  (パスワード: ${Password})" "WAIT"
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 5. ファイルアップロード (オプション)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
if ($UploadFiles) {
    Write-Host ""
    Write-Status "ファイルをアップロード中..."
    Write-Host "  パスワード: $Password" -ForegroundColor Yellow
    Write-Host ""

    $files = @(
        (Join-Path $Root "unitv2\main.py"),
        (Join-Path $Root "unitv2\config_unitv2.py")
    )
    foreach ($f in $files) {
        if (Test-Path $f) {
            $fname = Split-Path $f -Leaf
            Write-Status "SCP: $fname"
            & scp -o StrictHostKeyChecking=no -o ConnectTimeout=8 $f "${User}@${IP}:/home/m5stack/" 2>&1
            if ($LASTEXITCODE -eq 0) {
                Write-Status "$fname アップロード完了" "OK"
            } else {
                Write-Status "$fname アップロード失敗" "ERR"
            }
        }
    }
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 6. 完了メッセージ
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Write-Host ""
Write-Host "================================================" -ForegroundColor Green
Write-Status "USB-LAN 接続完了!" "OK"
Write-Host "================================================"
Write-Host ""
Write-Host "  SSH シェル:"
Write-Host "    ssh ${User}@${IP}"
Write-Host "    パスワード: $Password"
Write-Host ""
Write-Host "  ファイルアップロード:"
Write-Host "    scp unitv2\main.py ${User}@${IP}:/home/m5stack/"
Write-Host ""
Write-Host "  PC側 OCR 起動:"
Write-Host "    python pc_ocr.py"
Write-Host ""

if ($RunOCR) {
    Write-Status "pc_ocr.py を起動します..."
    Push-Location $Root
    python pc_ocr.py
    Pop-Location
}
