# SR9900 USB-LAN ドライバ インストール手順

M5Stack UnitV2 は USB 接続時に **Corechip SR9900** チップの USB-LAN アダプターとして認識されます。  
OCR を PC 側で実行するには、このドライバのインストールが必要です。

---

## 自動インストール（推奨）

付属のスクリプトを使うと、ドライバの検索・ダウンロード・インストールまで自動で行います。

**PowerShell（管理者）で実行：**
```powershell
.\tools\install_sr9900_driver.ps1
```

スクリプトは以下の順序でインストールを試みます：

1. **Windows Update 自動検索** (`pnputil /scan-devices`)
2. **Microsoft Update Catalog からダウンロード**
3. **最小 INF ファイルによる手動インストール**（フォールバック）

インストール完了後、USB ケーブルを抜き差しして認識を確認します。

---

## 手動インストール手順

自動スクリプトが失敗した場合は以下の手順で手動インストールしてください。

### 方法 1: Microsoft Update Catalog（推奨）

1. ブラウザで以下の URL を開く：  
   https://www.catalog.update.microsoft.com/Search.aspx?q=SR9900

2. 検索結果から **"Corechip - Net - 2.0.5.0"** の Windows 10 版を選択してダウンロード

3. ダウンロードした CAB ファイルを展開：
   ```powershell
   expand.exe sr9900.cab -F:* .\sr9900_driver\
   ```

4. 展開されたフォルダの INF ファイルを指定してインストール：
   ```powershell
   pnputil /add-driver .\sr9900_driver\*.inf /install
   ```

### 方法 2: デバイスマネージャーから手動指定

1. UnitV2 を USB-C ケーブルで接続
2. デバイスマネージャーを開く：
   ```powershell
   devmgmt.msc
   ```
3. 「ネットワーク アダプター」または「その他のデバイス」に `USB 10/100 LAN` を探す
4. 右クリック → **ドライバーの更新** → **コンピューターを参照してドライバーを検索**
5. Catalog からダウンロード・展開したフォルダを指定する

---

## インストール後の確認

### デバイスマネージャーで確認

```powershell
devmgmt.msc
```

「ネットワーク アダプター」内に **"SR9900 USB2.0 Fast Ethernet Adapter"** または  
**"Corechip USB LAN"** が「正常」ステータスで表示されれば OK です。

### IP アドレスの確認

```powershell
Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -match "^10\.254\." }
```

`10.254.239.x` が表示されれば、PC 側の IP が割り当てられています。

### UnitV2 への疎通確認

```powershell
ping 10.254.239.1
```

応答が返れば接続成功です。

---

## トラブルシューティング

### デバイスマネージャーに `USB 10/100 LAN` が表示されない

- UnitV2 の電源が入っているか確認
- USB-C ケーブルがデータ転送対応（充電専用でない）か確認
- 別の USB ポートに差し替え（USB 3.0 ポート推奨）
- UnitV2 を再起動してから再接続

### ドライバインストール後も `10.254.239.1` に ping が届かない

1. デバイスマネージャーで SR9900 が「正常」になっているか確認
2. ネットワーク設定で SR9900 アダプターが有効になっているか確認
3. 付属スクリプトで診断：
   ```powershell
   .\tools\connect_usb.ps1
   ```
4. IP が自動取得されない場合は手動設定：
   ```powershell
   # アダプター名を確認
   Get-NetAdapter | Where-Object { $_.InterfaceDescription -match "SR9900|Corechip|USB.*LAN" }
   # IP を手動設定（<アダプター名> は上記コマンドで確認した名前に置き換え）
   New-NetIPAddress -InterfaceAlias "<アダプター名>" -IPAddress 10.254.239.2 -PrefixLength 24
   ```

### Windows セキュリティがドライバをブロックする

1. ダウンロードしたファイルを右クリック
2. **プロパティ** → **ブロックの解除** にチェック → **適用** → **OK**
3. インストーラーを再実行

---

## 接続情報

| 項目 | 値 |
|---|---|
| UnitV2 IP | `10.254.239.1` |
| PC IP | `10.254.239.124`（DHCP 自動割り当て） |
| デバイス VID/PID | `VID_0FE6 / PID_9900` |
| SSH ユーザー | `m5stack` |
| SSH パスワード | `12345678` |

---

## 次のステップ

ドライバのインストールと接続確認が完了したら、README の手順に戻ってください。

→ [README.md](README.md) — Python パッケージのインストールと OCR の起動方法
