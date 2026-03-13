# M5UnitV2 OCR プロジェクト - クイックスタートガイド

## 5分で始めるOCR

### ステップ 1: Google APIキーの取得

1. [Google Cloud Console](https://console.cloud.google.com/) にアクセス
2. プロジェクトを作成（無料）
3. 「APIとサービス」→「Cloud Vision API」を有効化
4. 「認証情報」→「APIキーを作成」

### ステップ 2: 設定

`config.py` を編集：

```python
GOOGLE_API_KEY = "ここにAPIキーを貼り付け"
```

`utils.py` を編集（WiFi設定）:

```python
WIFI_SSID = "あなたのWiFi名"
WIFI_PASSWORD = "WiFiパスワード"
```

### ステップ 3: テスト

```python
# utils.pyを実行してシステムチェック
import utils
utils.system_check()
```

### ステップ 4: OCR実行

```python
# main.pyを実行
import main
```

Aボタンを押して画像をキャプチャ&OCR実行！

## ファイルの役割

- **main.py** - メインプログラム（フル機能）
- **simple_ocr.py** - シンプル版OCR
- **utils.py** - WiFi接続とシステムテスト
- **config.py** - API設定

## よくある質問

### Q: UnitV2が応答しない
A: 配線を確認（デフォルト: PortA GPIO16/17）

### Q: API エラーが出る
A: 
- APIキーが正しいか確認
- WiFiに接続されているか確認
- Google Cloud で Vision API が有効か確認

### Q: 日本語は認識できる？
A: はい！Google Vision APIは日本語対応

### Q: オフラインで使える？
A: 現在のバージョンはオンライン必須。オフライン版は今後実装予定

## サンプル使用例

### 名刺の認識
```python
import main
ocr = main.UnitV2OCR()
# 名刺にカメラを向けて
# Aボタンを押す
```

### レシートの認識
```python
# レシートの金額を読み取り
# 自動で家計簿に記録、など
```

### 看板・標識の認識
```python
# 外国語の看板を自動翻訳、など
```

## もっと詳しく

詳細は [README.md](README.md) を参照してください。

## サポート

問題がある場合は、`utils.system_check()` を実行して診断してください。
