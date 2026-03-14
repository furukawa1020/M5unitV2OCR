# upload_scp.ps1 - SCP で UnitV2 にファイルをアップロード
# 使い方: .\tools\upload_scp.ps1

param(
    [string]$IP       = "10.254.239.1",
    [string]$User     = "m5stack",
    [string]$Password = "12345678",
    [string]$RemoteDir = "/home/m5stack"
)

$SSHOpts = "-o StrictHostKeyChecking=no -o ConnectTimeout=8"

function Write-Status($msg, $level="INFO") {
    $tag = @{INFO="[INFO]"; OK="[ OK ]"; ERR="[ERR ]"}[$level]
    if (-not $tag) { $tag = "[----]" }
    Write-Host "$tag $msg"
}

# アップロード対象ファイル
$files = @(
    "unitv2\main.py",
    "unitv2\config_unitv2.py"
)

$root = Split-Path $PSScriptRoot -Parent

Write-Status "UnitV2 ($IP) に接続確認..."
if (-not (Test-Connection -ComputerName $IP -Count 1 -Quiet)) {
    Write-Status "UnitV2 に到達できません" "ERR"
    Write-Host "  .\tools\connect_wifi.ps1 を先に実行してください"
    exit 1
}
Write-Status "接続OK" "OK"

# sshpass がない場合の代替: SSH_ASKPASS は面倒なので scp に -pw 付きの plink を使う
# Windows 標準の scp.exe はパスワード自動入力不可 → パスワードなしSSH鍵か
# ここでは StrictHostKeyChecking=no + パスワード手入力のガイドを出す

Write-Host ""
Write-Status "ファイルをアップロード中..."
Write-Host "  ※ パスワードの入力を求められたら: $Password"
Write-Host ""

$ok = $true
foreach ($rel in $files) {
    $src = Join-Path $root $rel
    if (-not (Test-Path $src)) {
        Write-Status "$rel が見つかりません (スキップ)" "ERR"
        continue
    }
    Write-Status "アップロード: $rel"
    $scpCmd = "scp -o StrictHostKeyChecking=no -o ConnectTimeout=8 `"$src`" ${User}@${IP}:${RemoteDir}/"
    Write-Host "  $scpCmd" -ForegroundColor DarkGray
    $result = Invoke-Expression $scpCmd
    if ($LASTEXITCODE -eq 0) {
        Write-Status "$rel → OK" "OK"
    } else {
        Write-Status "$rel → 失敗" "ERR"
        $ok = $false
    }
}

if (-not $ok) {
    Write-Host ""
    Write-Host "  失敗した場合は手動でアップロード:"
    Write-Host "  scp unitv2\main.py m5stack@$IP:/home/m5stack/"
    Write-Host "  scp unitv2\config_unitv2.py m5stack@$IP:/home/m5stack/"
    exit 1
}

Write-Host ""
Write-Status "=== アップロード完了 ===" "OK"
Write-Host ""
Write-Host "  確認: ssh m5stack@$IP 'ls -la /home/m5stack/*.py'"
Write-Host ""
