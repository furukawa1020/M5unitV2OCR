# M5UnitV2 OCR - PlatformIO クイックスタート

## 5分で始めるUSB経由ビルド＆インストール

### 準備（初回のみ）

1. **VS Code + PlatformIO をインストール**
   - VS Code: https://code.visualstudio.com/
   - 拡張機能で "PlatformIO IDE" を検索してインストール

2. **M5StackをUSB接続**
   - データ転送対応のUSBケーブルを使用

### ステップ1: 設定を編集（30秒）

[include/config.h](include/config.h) を開いて編集：

```cpp
#define WIFI_SSID "あなたのWiFi名"
#define WIFI_PASSWORD "WiFiパスワード"
#define GOOGLE_API_KEY "GoogleのAPIキー"  // 後でも設定可能
```

### ステップ2: ビルド（1分）

**方法A: キーボードショートカット**
```
Ctrl + Alt + B
```

**方法B: ターミナル**
```powershell
pio run
```

**方法C: PlatformIO UI**
- 左側の PlatformIO アイコン → Build

### ステップ3: アップロード（30秒）

**方法A: キーボードショートカット**
```
Ctrl + Alt + U
```

**方法B: ターミナル**
```powershell
pio run --target upload
```

**方法C: PlatformIO UI**
- 左側の PlatformIO アイコン → Upload

### ステップ4: 動作確認（1分）

**シリアルモニタを開く:**
```powershell
pio device monitor
```

または `Ctrl + Shift + P` → "PlatformIO: Serial Monitor"

**表示例:**
```
=================================
M5Stack UnitV2 OCR System
=================================

WiFi Connected!
IP: 192.168.1.100
System ready!
```

### ステップ5: OCRを実行

1. M5StackのUnitV2カメラを文字に向ける
2. **Aボタン**を押す
3. 画面に認識結果が表示される！

## ボタン操作

- **Aボタン**: 画像キャプチャ & OCR実行
- **Bボタン**: WiFi再接続
- **Cボタン**: システム情報表示

## トラブルシューティング

### ❌ ビルドエラー

```powershell
# ライブラリ再インストール
pio lib install
```

### ❌ アップロードできない

1. USBケーブルを確認（データ転送対応？）
2. 他のシリアルアプリを閉じる
3. M5Stackを再起動
4. ポート指定してリトライ:
   ```powershell
   pio run --target upload --upload-port COM3
   ```

### ❌ WiFi接続失敗

1. config.hのSSID/パスワードを確認
2. 2.4GHz WiFiを使用（5GHzは非対応）

### ❌ UnitV2が応答しない

- 配線確認（PortA: GPIO 16/17）
- UnitV2の電源確認

## ワンコマンド実行

**ビルド→アップロード→モニタを一括実行:**

```powershell
cd c:\Projects\M5unitV2OCR
pio run --target upload && pio device monitor
```

## デバイス選択

複数のM5Stackがある場合：

```powershell
# 利用可能なデバイスを表示
pio device list

# 特定のポートにアップロード
pio run --target upload --upload-port COM5
```

## 設定ファイル早見表

| ファイル | 用途 |
|---------|------|
| [platformio.ini](platformio.ini) | ボード設定、ライブラリ |
| [include/config.h](include/config.h) | WiFi、API設定 |
| [src/main.cpp](src/main.cpp) | メインコード |

## 次のステップ

✅ **WiFi/API設定完了** → OCRを実行！  
📖 **詳細な説明が必要** → [PLATFORMIO_GUIDE.md](PLATFORMIO_GUIDE.md) を参照  
🔧 **カスタマイズしたい** → [src/main.cpp](src/main.cpp) を編集  

---

**困ったら:** [PLATFORMIO_GUIDE.md](PLATFORMIO_GUIDE.md) のトラブルシューティングを確認
