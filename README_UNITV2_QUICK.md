# UnitV2 OCR - クイックスタートガイド

## 🎯 5分で始めるUnitV2 OCR

UnitV2本体で直接OCRを実行します！

---

## 📋 準備（初回のみ）

### 1. Android Platform Toolsのインストール

adbコマンドが必要です：

**方法A: 直接ダウンロード**
1. https://developer.android.com/tools/releases/platform-tools からダウンロード
2. ZIP解凍後、`platform-tools`フォルダを`C:\`に配置
3. 環境変数PATHに追加：`C:\platform-tools`

**方法B: Chocolatey経由（推奨）**
```powershell
# Chocolateyインストール済みの場合
choco install adb

# 確認
adb version
```

### 2. UnitV2のWiFi設定

1. UnitV2の電源を入れる
2. Web UIにアクセスして WiFi設定
3. IPアドレスをメモ（例：`192.168.1.100`）

---

## 🚀 使い方

### ステップ1: 設定ファイルを編集

[unitv2/config_unitv2.py](unitv2/config_unitv2.py) を開いて編集：

```python
WIFI_SSID = "あなたのWiFi名"
WIFI_PASSWORD = "WiFiパスワード"
GOOGLE_API_KEY = "GoogleのAPIキー"
```

### ステップ2: UnitV2に接続

```powershell
# プロジェクトフォルダに移動
cd c:\Projects\M5unitV2OCR

# UnitV2に接続
.\tools\connect_unitv2.ps1 -IPAddress 192.168.1.100
```

メニューが表示されます：
- `1` - シェルを開く
- `2` - プログラムをアップロード ← これを選択
- `3` - プログラムを実行
- `4` - システム情報表示
- `5` - 終了

### ステップ3: プログラムをアップロード＆実行

**方法A: 接続ツール経由（簡単）**
```powershell
.\tools\connect_unitv2.ps1 -IPAddress 192.168.1.100
# メニューで "2" を選択してアップロード
# 次に "3" を選択して実行
```

**方法B: アップロードスクリプト使用**
```powershell
# アップロードのみ
.\tools\upload_to_unitv2.ps1 -IPAddress 192.168.1.100

# アップロード&実行
.\tools\upload_to_unitv2.ps1 -IPAddress 192.168.1.100 -Run
```

**方法C: adbコマンド直接使用**
```powershell
# UnitV2に接続
adb connect 192.168.1.100:5555

# ファイルをアップロード
adb push unitv2\main.py /root/
adb push unitv2\config_unitv2.py /root/

# プログラムを実行
adb shell python3 /root/main.py
```

---

## 📱 UnitV2での動作

プログラムが起動すると：

1. **カメラプレビュー表示** - UnitV2の画面にカメラ映像
2. **自動OCR実行** - 10秒ごとに自動で撮影＆OCR
3. **結果表示** - 認識されたテキストを画面に表示
4. **ログ出力** - シリアル/adb経由でログ確認可能

---

## 🔍 動作確認

### ログを確認

```powershell
# adb logcat で確認
adb connect 192.168.1.100:5555
adb logcat | Select-String "OCR"
```

### シェルで確認

```powershell
adb shell

# UnitV2内で
cd /root
ls -la
python3 main.py
```

---

## 🛠️ トラブルシューティング

### ❌ adbが見つからない

```powershell
# adbのパスを確認
Get-Command adb

# 見つからない場合は再インストール
choco install adb
```

### ❌ UnitV2に接続できない

```powershell
# 1. Ping確認
ping 192.168.1.100

# 2. ポート確認
Test-NetConnection -ComputerName 192.168.1.100 -Port 5555

# 3. UnitV2を再起動
# 4. WiFi設定を確認
```

### ❌ プログラムが動かない

```powershell
# エラーログを確認
adb shell python3 /root/main.py

# または
adb logcat
```

**よくあるエラー:**

1. **ModuleNotFoundError**
   - UnitV2のファームウェアを最新に更新

2. **WiFi connection failed**
   - `config_unitv2.py` の SSID/パスワードを確認
   - 2.4GHz WiFiを使用

3. **API Error 403**
   - Google API Keyを確認
   - Vision APIが有効か確認

---

## 📊 カスタマイズ

### OCR実行間隔の変更

[unitv2/config_unitv2.py](unitv2/config_unitv2.py):
```python
AUTO_OCR_INTERVAL = 5  # 5秒ごとに変更
```

### カメラ解像度の変更

[unitv2/config_unitv2.py](unitv2/config_unitv2.py):
```python
CAMERA_WIDTH = 1280
CAMERA_HEIGHT = 720
```

### 手動トリガーに変更

[unitv2/main.py](unitv2/main.py) の `main()` 関数を編集して、ボタン入力で実行するように変更できます。

---

## 📁 ファイル構成

```
M5unitV2OCR/
├── unitv2/
│   ├── main.py              # UnitV2メインプログラム
│   └── config_unitv2.py     # 設定ファイル
├── tools/
│   ├── upload_to_unitv2.ps1 # アップロードスクリプト
│   └── connect_unitv2.ps1   # 接続ツール
└── README_UNITV2_QUICK.md   # このファイル
```

---

## 🔗 関連ドキュメント

- [README_UNITV2.md](README_UNITV2.md) - 詳細な開発ガイド
- [UnitV2公式ドキュメント](https://docs.m5stack.com/en/unit/unitv2)
- [Android Platform Tools](https://developer.android.com/tools/releases/platform-tools)

---

## 💡 Tips

### 自動起動設定

UnitV2の起動時に自動実行：

```bash
# SSH接続
adb shell

# 自動起動設定
echo "python3 /root/main.py &" > /etc/init.d/S99custom
chmod +x /etc/init.d/S99custom
reboot
```

### Web UIからの実行

1. ブラウザで `http://<UnitV2_IP>` にアクセス
2. Web IDEで `main.py` を開く
3. 実行ボタンをクリック

---

**困ったら:** [README_UNITV2.md](README_UNITV2.md) のトラブルシューティングを参照！
