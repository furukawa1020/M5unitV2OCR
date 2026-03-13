# M5Stack USB ドライバインストール手順

## 問題: デバイスが認識されない

COMポートが表示されない場合、USBドライバが必要です。

## ドライバのダウンロード＆インストール

### 方法1: CP210x ドライバ（推奨）

M5Stack Core2 / Basic / Gray は通常 CP210x を使用

1. **ドライバダウンロード:**
   https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers

2. **Windows版を選択:**
   - "CP210x Windows Drivers" をダウンロード
   - ZIP解凍後、`CP210xVCPInstaller_x64.exe` を実行

3. **インストール:**
   - 管理者権限で実行
   - 画面の指示に従ってインストール

4. **PCを再起動**

5. **デバイスマネージャーで確認:**
   ```powershell
   devmgmt.msc
   ```
   - 「ポート (COM と LPT)」に「Silicon Labs CP210x USB to UART Bridge (COMx)」が表示されるか確認

### 方法2: CH340 ドライバ（古いモデル用）

一部の M5Stack は CH340 チップを使用

1. **ドライバダウンロード:**
   http://www.wch.cn/downloads/CH341SER_ZIP.html

2. **インストール:**
   - ZIP解凍後、`SETUP.EXE` を実行
   - 管理者権限で実行

3. **PCを再起動**

### 方法3: 自動ドライバインストール（PlatformIO経由）

```powershell
# PlatformIO のシリアルドライバをインストール
& "$env:USERPROFILE\.platformio\penv\Scripts\platformio.exe" device install drivers
```

## インストール後の確認

```powershell
# COMポート確認
[System.IO.Ports.SerialPort]::getportnames()

# または
mode
```

COMポート（例：COM3, COM5など）が表示されればOK！

## トラブルシューティング

### デバイスマネージャーに「不明なデバイス」と表示される

1. デバイスマネージャーを開く: `devmgmt.msc`
2. 「不明なデバイス」を右クリック → 「ドライバーの更新」
3. 「コンピューターを参照してドライバーを検索」
4. ダウンロードしたドライバフォルダを指定

### ドライバインストール後もCOMポートが表示されない

1. **別のUSBケーブル**を試す（データ転送対応のもの）
2. **別のUSBポート**を試す（USB 2.0推奨）
3. M5Stackを**再起動**
4. PCを**再起動**

### Windows セキュリティがブロックする場合

1. ダウンロードしたファイルを右クリック
2. 「プロパティ」→「ブロックの解除」にチェック
3. 「適用」→「OK」
4. インストーラーを再実行

## 次のステップ

COMポートが認識されたら：

```powershell
# ポートを確認
[System.IO.Ports.SerialPort]::getportnames()
# 例: COM3 が表示される

# ポート指定してアップロード
cd c:\Projects\M5unitV2OCR
& "$env:USERPROFILE\.platformio\penv\Scripts\platformio.exe" run --target upload --upload-port COM3
```

## 参考リンク

- [Silicon Labs CP210x ドライバ](https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers)
- [CH340 ドライバ](http://www.wch.cn/downloads/CH341SER_ZIP.html)
- [M5Stack公式ドキュメント](https://docs.m5stack.com/en/quick_start/core2/arduino)
