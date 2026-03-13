# PlatformIO による M5UnitV2 OCR ビルド＆インストール手順

## 前提条件

- Visual Studio Code がインストール済み
- PlatformIO IDE 拡張機能がインストール済み
- M5StackとPCをUSBケーブルで接続

## 1. PlatformIOのインストール

### VS Codeに拡張機能をインストール

1. VS Codeを開く
2. 左側の拡張機能アイコンをクリック（Ctrl + Shift + X）
3. "PlatformIO IDE" を検索
4. "Install" をクリック
5. VS Codeを再起動

## 2. プロジェクトの設定

### WiFiとAPI設定

`include/config.h` を編集：

```cpp
#define WIFI_SSID "あなたのWiFi名"
#define WIFI_PASSWORD "WiFiパスワード"
#define GOOGLE_API_KEY "GoogleAPIキー"
```

### ボード選択

`platformio.ini` でお使いのM5Stackモデルに対応するセクションを確認：

- **M5Stack Core2**: `[env:m5stack-core2]`
- **M5Stack Basic**: `[env:m5stack-basic]`
- **M5Stack Gray**: `[env:m5stack-gray]`

## 3. ビルド方法

### コマンドパレットから

1. `Ctrl + Shift + P` でコマンドパレットを開く
2. "PlatformIO: Build" を選択
3. または `Ctrl + Alt + B`

### ターミナルから

```powershell
# プロジェクトディレクトリに移動
cd c:\Projects\M5unitV2OCR

# ビルド実行
pio run

# 特定の環境でビルド
pio run -e m5stack-core2
```

### PlatformIOサイドバーから

1. 左側の PlatformIO アイコンをクリック
2. "PROJECT TASKS" → ボード名 → "General" → "Build"

## 4. アップロード（書き込み）方法

### USB接続の確認

1. M5StackをUSBケーブルでPCに接続
2. デバイスマネージャーでCOMポートを確認（例：COM3）

### コマンドパレットから

1. `Ctrl + Shift + P` でコマンドパレットを開く
2. "PlatformIO: Upload" を選択
3. または `Ctrl + Alt + U`

### ターミナルから

```powershell
# アップロード実行
pio run --target upload

# 特定の環境でアップロード
pio run -e m5stack-core2 --target upload

# ポートを指定してアップロード
pio run --target upload --upload-port COM3
```

### PlatformIOサイドバーから

1. 左側の PlatformIO アイコンをクリック
2. "PROJECT TASKS" → ボード名 → "General" → "Upload"

## 5. シリアルモニタで動作確認

### モニタを開く

```powershell
# シリアルモニタ起動
pio device monitor

# ボーレート指定
pio device monitor -b 115200
```

### コマンドパレットから

1. `Ctrl + Shift + P` → "PlatformIO: Serial Monitor"

### 表示される情報

```
=================================
M5Stack UnitV2 OCR System
=================================

UnitV2 UART initialized
WiFi connecting...
WiFi Connected!
IP: 192.168.1.100

System ready!
Press A button to capture and perform OCR
```

## 6. ビルド＆アップロード＆モニタ（一括実行）

```powershell
# ビルド、アップロード、モニタを連続実行
pio run --target upload && pio device monitor
```

## 7. トラブルシューティング

### エラー: "No upload port found"

**解決策:**
1. USBケーブルが接続されているか確認
2. デバイスドライバがインストールされているか確認
3. 他のシリアルアプリ（Arduino IDEなど）を閉じる
4. M5Stackを再起動

手動でポート指定：
```powershell
pio run --target upload --upload-port COM3
```

### エラー: "Failed to connect to ESP32"

**解決策:**
1. M5Stackの電源を入れる
2. アップロード時にM5Stackのリセットボタンを押す
3. USBケーブルを変える（データ転送対応のもの）

### ビルドエラー: "Library not found"

**解決策:**
```powershell
# ライブラリを手動インストール
pio lib install "M5Stack"
pio lib install "ArduinoJson"
```

### WiFi接続失敗

**解決策:**
1. `config.h` のSSID/パスワードを確認
2. 2.4GHz WiFiに接続（5GHzは非対応）
3. シリアルモニタでエラーメッセージを確認

## 8. よく使うPlatformIOコマンド

```powershell
# プロジェクト情報表示
pio project config

# ライブラリ一覧
pio lib list

# ライブラリ検索
pio lib search M5Stack

# クリーン（ビルドファイル削除）
pio run --target clean

# 完全クリーン
pio run --target cleanall

# テスト実行
pio test

# 依存関係のアップデート
pio lib update
```

## 9. VS Code タスク設定（オプション）

`.vscode/tasks.json` を作成（高速アクセス用）：

```json
{
    "version": "2.0.0",
    "tasks": [
        {
            "label": "PIO Build",
            "type": "shell",
            "command": "pio run",
            "group": "build"
        },
        {
            "label": "PIO Upload",
            "type": "shell",
            "command": "pio run --target upload",
            "group": "build"
        },
        {
            "label": "PIO Build & Upload",
            "type": "shell",
            "command": "pio run --target upload",
            "group": {
                "kind": "build",
                "isDefault": true
            }
        }
    ]
}
```

`Ctrl + Shift + B` で直接ビルド＆アップロード可能！

## 10. デバッグ方法

### シリアル出力デバッグ

```cpp
Serial.println("Debug message");
Serial.printf("Value: %d\n", value);
```

### リアルタイムモニタリング

```powershell
# フィルター付きモニタ
pio device monitor --filter colorize
pio device monitor --filter time
```

## プロジェクト構造

```
M5unitV2OCR/
├── platformio.ini       # PlatformIO設定
├── src/
│   └── main.cpp         # メインコード
├── include/
│   └── config.h         # 設定ファイル
├── lib/                 # ローカルライブラリ（必要に応じて）
└── test/                # テストコード
```

## 参考リンク

- [PlatformIO公式ドキュメント](https://docs.platformio.org/)
- [PlatformIO CLI リファレンス](https://docs.platformio.org/en/latest/core/userguide/index.html)
- [M5Stack公式](https://docs.m5stack.com/)

## クイックリファレンス

| 操作 | コマンド | ショートカット |
|------|----------|----------------|
| ビルド | `pio run` | `Ctrl + Alt + B` |
| アップロード | `pio run --target upload` | `Ctrl + Alt + U` |
| モニタ | `pio device monitor` | - |
| クリーン | `pio run --target clean` | - |

---

**次のステップ:** [QUICKSTART_PLATFORMIO.md](QUICKSTART_PLATFORMIO.md) で5分で始める手順を確認！
