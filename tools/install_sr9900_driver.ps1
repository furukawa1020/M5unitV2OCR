# install_sr9900_driver.ps1
# UnitV2 USB接続用 SR9900 USB-LANドライバをインストールする
# 管理者権限が必要 → スクリプト自体で昇格を要求します
# 使い方: .\tools\install_sr9900_driver.ps1

#Requires -Version 5.1

# ---- 管理者権限チェック / 自動昇格 ----
if (-not ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
        [Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Host "[INFO] 管理者権限で再起動します..." -ForegroundColor Yellow
    $args = "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`""
    Start-Process powershell.exe -ArgumentList $args -Verb RunAs
    exit
}

$ErrorActionPreference = "Stop"
$TmpDir = "$env:TEMP\sr9900_driver"

function Write-Status($msg, $level = "INFO") {
    $color = @{ INFO = "Cyan"; OK = "Green"; ERR = "Red"; WAIT = "Yellow" }[$level]
    if (-not $color) { $color = "White" }
    Write-Host "[$level] $msg" -ForegroundColor $color
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 1. デバイス確認
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  SR9900 USB-LAN ドライバ インストーラー"
Write-Host "  (UnitV2 USB接続用)"
Write-Host "================================================"
Write-Host ""

Write-Status "デバイスマネージャーで SR9900 / USB-LAN を検索中..."
$device = Get-PnpDevice -ErrorAction SilentlyContinue | Where-Object {
    $_.FriendlyName -match "USB 10.100 LAN|SR9900|sr9900" -or
    $_.InstanceId   -match "VID_0FE6"
}

if ($device) {
    Write-Status "デバイスを検出: $($device.FriendlyName)  [$($device.Status)]" "OK"
    Write-Status "InstanceID: $($device.InstanceId)"
} else {
    Write-Status "SR9900 デバイスが見つかりません" "ERR"
    Write-Host ""
    Write-Host "  確認事項:"
    Write-Host "  ・UnitV2 が USB-C ケーブルで PC に接続されているか"
    Write-Host "  ・UnitV2 の電源が入っているか"
    Write-Host "  ・デバイスマネージャーに 'USB 10/100 LAN' が表示されているか"
    Write-Host ""
    Read-Host "  Enter で終了"
    exit 1
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 2. まず Windows Update 自動検索を試みる
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Write-Host ""
Write-Status "方法 1: pnputil で Windows Update からドライバを検索中..."
$pnpResult = pnputil /scan-devices 2>&1
Write-Status "pnputil 完了"

# 少し待ってステータス確認
Start-Sleep -Seconds 10
$deviceAfter = Get-PnpDevice -InstanceId $device.InstanceId -ErrorAction SilentlyContinue
if ($deviceAfter -and $deviceAfter.Status -eq "OK") {
    Write-Status "Windows Update でドライバが適用されました!" "OK"
    goto :DONE
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 3. Microsoft Update Catalog から直接ダウンロード
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Write-Host ""
Write-Status "方法 2: Microsoft Update Catalog から直接ダウンロード中..."

# Catalog API でダウンロードURLを取得する関数
function Get-CatalogDownloadUrl {
    param([string]$SearchQuery)
    
    $searchUrl = "https://www.catalog.update.microsoft.com/Search.aspx?q=$([Uri]::EscapeDataString($SearchQuery))"
    $headers = @{ "User-Agent" = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)" }
    
    try {
        $resp = Invoke-WebRequest -Uri $searchUrl -Headers $headers -UseBasicParsing -TimeoutSec 30
        $content = $resp.Content
    } catch {
        return $null, "Catalog 検索失敗: $_"
    }
    
    # UpdateID を HTML から抽出 (catalog の固有形式)
    $updateIds = [regex]::Matches($content, "goToDetails\(['""]([a-f0-9\-]{36})['""]") | ForEach-Object { $_.Groups[1].Value }
    if (-not $updateIds) {
        return $null, "UpdateID が見つかりません"
    }
    
    # 最初の UpdateID でダウンロードURLを取得
    $updateId = $updateIds[0]
    Write-Status "UpdateID: $updateId"
    
    $dialogUrl = "https://www.catalog.update.microsoft.com/DownloadDialog.aspx"
    $body = "updateIDs=[{%22size%22:0,%22languages%22:%22%22,%22uidInfo%22:%22$updateId%22,%22updateID%22:%22$updateId%22}]&updateIDsBlockedForImport=&wsusApiPresent=&contentImport=&jectFilter=&cmdlineArgs=&ClientName=&btnExport.x=&btnExport.y="
    
    try {
        $dlResp = Invoke-WebRequest -Uri $dialogUrl -Method Post -Body $body -Headers $headers -UseBasicParsing -TimeoutSec 30
        $dlContent = $dlResp.Content
    } catch {
        return $null, "DownloadDialog 失敗: $_"
    }
    
    # 実際のURLを抽出
    $dlUrls = [regex]::Matches($dlContent, "https://[^'`"]+\.cab") | ForEach-Object { $_.Value }
    if (-not $dlUrls) {
        $dlUrls = [regex]::Matches($dlContent, "https://catalog\.s\.download\.windowsupdate\.com[^'`"]+") | ForEach-Object { $_.Value }
    }
    if ($dlUrls) {
        return $dlUrls[0], $null
    }
    return $null, "ダウンロードURL が見つかりません"
}

# Catalog から SR9900 ドライバを検索
$downloadUrl, $dlErr = Get-CatalogDownloadUrl -SearchQuery "Corechip SR9900 Windows 10"
if (-not $downloadUrl) {
    # 検索語を変えて再試行
    $downloadUrl, $dlErr = Get-CatalogDownloadUrl -SearchQuery "Corechip Net 2.0.5.0"
}

if ($downloadUrl) {
    Write-Status "ダウンロードURL: $downloadUrl" "OK"
    
    New-Item -ItemType Directory -Force -Path $TmpDir | Out-Null
    $cabPath = "$TmpDir\sr9900.cab"
    
    Write-Status "ダウンロード中..."
    try {
        Invoke-WebRequest -Uri $downloadUrl -OutFile $cabPath -UseBasicParsing -TimeoutSec 60
        Write-Status "ダウンロード完了: $cabPath" "OK"
    } catch {
        Write-Status "ダウンロード失敗: $_" "ERR"
        $downloadUrl = $null
    }
    
    if ($downloadUrl -and (Test-Path $cabPath)) {
        # CAB を展開
        $extractDir = "$TmpDir\extracted"
        New-Item -ItemType Directory -Force -Path $extractDir | Out-Null
        Write-Status "CAB ファイルを展開中..."
        $expandResult = & expand.exe $cabPath -F:* $extractDir 2>&1
        
        # INF ファイルを検索してインストール
        $infFiles = Get-ChildItem -Path $extractDir -Filter "*.inf" -Recurse | Select-Object -First 5
        if ($infFiles) {
            foreach ($inf in $infFiles) {
                Write-Status "ドライバをインストール: $($inf.Name)"
                $pnpAdd = pnputil /add-driver "$($inf.FullName)" /install 2>&1
                Write-Status $pnpAdd
                if ($LASTEXITCODE -eq 0) {
                    Write-Status "ドライバ追加成功!" "OK"
                    break
                }
            }
        } else {
            Write-Status "INF ファイルが展開できませんでした" "ERR"
            $downloadUrl = $null
        }
    }
} else {
    Write-Status "Catalog からのダウンロードに失敗: $dlErr" "ERR"
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 4. 手動 INF 方式 (フォールバック)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
if (-not $downloadUrl) {
    Write-Host ""
    Write-Status "方法 3: 手動 INF ドライバをインストール中..." "WAIT"
    Write-Host "  (VID_0FE6 / Corechip SR9900 の最小 INF を作成します)"
    
    New-Item -ItemType Directory -Force -Path $TmpDir | Out-Null
    $infContent = @'
; SR9900 USB to LAN - Minimal driver INF
; Uses Windows built-in USB CDC-ECM or custom INF

[Version]
Signature   = "$Windows NT$"
Class       = Net
ClassGUID   = {4d36e972-e325-11ce-bfc1-08002be10318}
Provider    = %Corechip%
DriverVer   = 10/13/2019,2.0.5.0
CatalogFile = sr9900.cat

[Manufacturer]
%Corechip% = Corechip,NTamd64,NTx86

[Corechip.NTamd64]
%USB\VID_0FE6&PID_9900.DeviceDesc% = RNDIS.ndi, USB\VID_0FE6&PID_9900

[Corechip.NTx86]
%USB\VID_0FE6&PID_9900.DeviceDesc% = RNDIS.ndi, USB\VID_0FE6&PID_9900

[RNDIS.ndi]
Characteristics = 0x84
BusType         = 15
AddReg          = RNDIS.reg, RNDIS.ndi.reg
CopyFiles       = FunctionDriver
*IfType         = 6
*MediaType      = 0
*PhysicalMediaType = 0

[RNDIS.reg]
HKR, Ndi,            Service,    0, "usb8023"
HKR, Ndi\Interfaces, UpperRange, 0, "ndis5"
HKR, Ndi\Interfaces, LowerRange, 0, "ethernet"

[RNDIS.ndi.reg]
HKR,,                    DeviceVendorPhysicalAddressMask, 0x00010001, 0xFF,0xFF,0xFF,0x00,0x00,0x00

[FunctionDriver]

[DestinationDirs]
DefaultDestDir = 12
FunctionDriver = 12

[SourceDisksNames]
1 = %DiskName%,,,

[SourceDisksFiles]

[Strings]
Corechip = "CoreChip Technology"
USB\VID_0FE6&PID_9900.DeviceDesc = "SR9900 USB2.0 Fast Ethernet Adapter"
DiskName = "SR9900 Driver Disk"
'@
    
    $infPath = "$TmpDir\sr9900_minimal.inf"
    $infContent | Out-File -FilePath $infPath -Encoding ASCII
    
    $addResult = pnputil /add-driver "$infPath" /install 2>&1
    Write-Status "手動INF結果: $addResult"
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 5. デバイスを再起動して確認
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Write-Host ""
Write-Status "デバイスをリセット中..."
if ($device) {
    try {
        Disable-PnpDevice -InstanceId $device.InstanceId -Confirm:$false -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
        Enable-PnpDevice  -InstanceId $device.InstanceId -Confirm:$false -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 5
    } catch {}
}

$deviceFinal = Get-PnpDevice | Where-Object {
    $_.FriendlyName -match "USB 10.100 LAN|SR9900|Corechip|LAN.*USB" -or
    $_.InstanceId   -match "VID_0FE6"
} | Select-Object -First 1

Write-Host ""
Write-Host "================================================"
if ($deviceFinal -and $deviceFinal.Status -eq "OK") {
    Write-Status "ドライバインストール成功!" "OK"
    Write-Status "デバイス: $($deviceFinal.FriendlyName)  [$($deviceFinal.Status)]" "OK"
    Write-Host ""
    Write-Host "  次のステップ:"
    Write-Host "  1. ネットワーク設定を確認:"
    Write-Host "     10.254.239.x のアダプタが有効になっているはずです"
    Write-Host ""
    Write-Host "  2. SSH 接続テスト (別のターミナルで):"
    Write-Host "     ssh m5stack@10.254.239.1"
    Write-Host "     パスワード: 12345678"
    Write-Host ""
    Write-Host "  3. OCR 実行:"
    Write-Host "     python pc_ocr.py"
} else {
    Write-Status "自動インストールに失敗しました" "ERR"
    Write-Host ""
    Write-Host "  ■ 手動でドライバをインストールしてください:"
    Write-Host ""
    Write-Host "  [手順]"
    Write-Host "  1. デバイスマネージャーを開く"
    Write-Host "     (Win+X → デバイスマネージャー)"
    Write-Host ""
    Write-Host "  2. 'USB 10/100 LAN' を右クリック"
    Write-Host "     → ドライバーの更新"
    Write-Host "     → コンピューターを参照してドライバーを検索"
    Write-Host "     → 次の場所: $TmpDir"
    Write-Host ""
    Write-Host "  3. または Microsoft Update Catalog から手動DL:"
    Write-Host "     https://www.catalog.update.microsoft.com/Search.aspx?q=SR9900"
    Write-Host "     → 'Corechip - Net - 2.0.5.0' の Windows 10 版をダウンロード"
    Write-Host ""
    Write-Host "  [作成した最小 INF の場所]"
    Write-Host "  $TmpDir\sr9900_minimal.inf"
}

Write-Host "================================================"
Write-Host ""
Read-Host "Enter で閉じる"
