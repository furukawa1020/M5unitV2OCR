# connect_wifi.ps1 - UnitV2 WiFi AP への接続スクリプト
# 使い方: .\tools\connect_wifi.ps1
# または: .\tools\connect_wifi.ps1 -SSID M5UV2_ABCD

param(
    [string]$SSID     = "",     # 空の場合は自動検索
    [string]$Password = "12345678",
    [int]   $Timeout  = 30       # 接続待機(秒)
)

$IP = "10.254.239.1"

function Write-Status($msg, $level="INFO") {
    $tag = @{INFO="[INFO]"; OK="[ OK ]"; ERR="[ERR ]"; WAIT="[WAIT]"}[$level]
    if (-not $tag) { $tag = "[----]" }
    Write-Host "$tag $msg"
}

# ----- 1. UnitV2 の SSID を特定 -----
Write-Status "UnitV2 の WiFi を検索中..."
$scanResult = netsh wlan show networks mode=bssid 2>&1
$lines = $scanResult -split "`n"

$foundSSIDs = @()
foreach ($line in $lines) {
    if ($line -match "SSID\s+\d+\s*:\s*(M5UV2\S*)") {
        $foundSSIDs += $Matches[1].Trim()
    }
}

if ($SSID -eq "" -and $foundSSIDs.Count -gt 0) {
    $SSID = $foundSSIDs[0]
    Write-Status "SSID 自動検出: $SSID" "OK"
} elseif ($SSID -eq "") {
    Write-Status "M5UV2_* の WiFi が見つかりません" "ERR"
    Write-Host ""
    Write-Host "  UnitV2 の電源が入っているか確認してください"
    Write-Host "  手動で SSID を指定: .\connect_wifi.ps1 -SSID M5UV2_XXXX"
    exit 1
} else {
    Write-Status "指定 SSID: $SSID"
}

# ----- 2. 既存 WiFi プロファイルを作成/更新 -----
Write-Status "WiFi プロファイルを設定中..."

$xmlPath = "$env:TEMP\unitv2_wifi.xml"
$xml = @"
<?xml version="1.0"?>
<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
    <name>$SSID</name>
    <SSIDConfig>
        <SSID><name>$SSID</name></SSID>
    </SSIDConfig>
    <connectionType>ESS</connectionType>
    <connectionMode>manual</connectionMode>
    <MSM>
        <security>
            <authEncryption>
                <authentication>WPA2PSK</authentication>
                <encryption>AES</encryption>
                <useOneX>false</useOneX>
            </authEncryption>
            <sharedKey>
                <keyType>passPhrase</keyType>
                <protected>false</protected>
                <keyMaterial>$Password</keyMaterial>
            </sharedKey>
        </security>
    </MSM>
</WLANProfile>
"@

$xml | Out-File -FilePath $xmlPath -Encoding UTF8 -NoNewline
$addResult = netsh wlan add profile filename="$xmlPath" 2>&1
if ($addResult -match "is added on interface") {
    Write-Status "プロファイル追加OK" "OK"
} else {
    Write-Status "プロファイル更新: $addResult"
}

# ----- 3. 現在の SSID が既に正しければスキップ -----
$current = (netsh wlan show interfaces) -join "`n"
if ($current -match "SSID\s*:\s*$([regex]::Escape($SSID))") {
    Write-Status "既に $SSID に接続済み" "OK"
} else {
    # ----- 4. 接続実行 -----
    Write-Status "$SSID に接続中..."
    $conn = netsh wlan connect name="$SSID" 2>&1
    Write-Status $conn

    # ----- 5. 接続完了まで待機 -----
    $waited = 0
    $connected = $false
    while ($waited -lt $Timeout) {
        Start-Sleep -Seconds 2
        $waited += 2
        $iface = (netsh wlan show interfaces) -join "`n"
        if ($iface -match "SSID\s*:\s*$([regex]::Escape($SSID))") {
            $connected = $true
            break
        }
        Write-Status "待機中... ($waited / $Timeout 秒)" "WAIT"
    }

    if (-not $connected) {
        Write-Status "接続タイムアウト ($Timeout 秒)" "ERR"
        Write-Host ""
        Write-Host "  手順: 設定 → ネットワーク → WiFi → $SSID → 接続"
        Write-Host "        パスワード: $Password"
        exit 1
    }
    Write-Status "WiFi 接続完了: $SSID" "OK"
}

# ----- 6. IP 疎通確認 -----
Write-Status "UnitV2 ($IP) に ping 中..."
$ping = Test-Connection -ComputerName $IP -Count 3 -Quiet
if ($ping) {
    Write-Status "ping OK ($IP)" "OK"
} else {
    Write-Status "ping 失敗 - 少し待ってから再試行します" "WAIT"
    Start-Sleep -Seconds 5
    $ping = Test-Connection -ComputerName $IP -Count 2 -Quiet
    if (-not $ping) {
        Write-Status "UnitV2 から応答なし" "ERR"
        exit 1
    }
}

# ----- 7. SSH 接続テスト -----
Write-Status "SSH 接続テスト..."
$sshResult = echo "y" | ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 `
    m5stack@$IP "echo SSH_OK" 2>&1

if ($sshResult -match "SSH_OK") {
    Write-Status "SSH 接続成功!" "OK"
} else {
    Write-Status "SSH 接続失敗 (後で手動で試してください)" "ERR"
    Write-Host "  コマンド: ssh m5stack@$IP"
    Write-Host "  パスワード: 12345678"
}

Write-Host ""
Write-Status "=== 接続完了 ===" "OK"
Write-Host ""
Write-Host "  SSH:  ssh m5stack@$IP"
Write-Host "  Web:  http://$IP"
Write-Host "  OCR:  python pc_ocr.py"
Write-Host ""
