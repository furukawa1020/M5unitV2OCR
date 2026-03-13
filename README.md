# M5UnitV2 OCR文字認識

M5Stack UnitV2を使用して、OCR（光学文字認識）を実行するプロジェクトです。

## 概要

このプロジェクトは、M5Stack UnitV2カメラモジュールで画像をキャプチャし、Google Cloud Vision APIを使用して文字認識を行います。

## 3つの実装方法

### 🎯 UnitV2直接実行版（最新・推奨！）
- **特徴**: UnitV2本体で直接OCR実行、M5Stack不要、スタンドアローン動作
- **開発環境**: MaixPy3 (Python)、adb経由でアップロード
- **クイックスタート**: [README_UNITV2_QUICK.md](README_UNITV2_QUICK.md)
- **詳細ガイド**: [README_UNITV2.md](README_UNITV2.md)

### 🔧 PlatformIO版 - M5Stack + UnitV2
- **特徴**: M5StackにUSB経由でビルド・アップロード、C++で高速実行
- **開発環境**: PlatformIO + Arduino
- **クイックスタート**: [QUICKSTART_PLATFORMIO.md](QUICKSTART_PLATFORMIO.md)
- **詳細ガイド**: [PLATFORMIO_GUIDE.md](PLATFORMIO_GUIDE.md)

### 🐍 MicroPython版 - M5Stack + UnitV2
- **特徴**: M5StackにPythonスクリプト実行、簡単プロトタイピング
- **開発環境**: UIFlow2.0
- **クイックスタート**: [QUICKSTART.md](QUICKSTART.md)

## 必要なハードウェア

### UnitV2直接実行版
- **M5Stack UnitV2カメラモジュール**（単体で動作）
- USB Type-Cケーブル（データ転送対応）
- WiFiルーター

### M5Stack連携版
- M5Stack（Core2、Basic、Grayなど）
- M5Stack UnitV2カメラモジュール
- Grove接続ケーブル
- USB Type-Cケーブル（データ転送対応）

## 必要なソフトウェア

### UnitV2直接実行版
- Android Platform Tools (adb)
- Google Cloud アカウント（Vision API用）
- WiFi接続環境

### PlatformIO版（M5Stack）
- Visual Studio Code
- PlatformIO IDE拡張機能
- Google Cloud アカウント（Vision API用）

### MicroPython版（M5Stack）
- UIFlow2.0 または MicroPython環境
- Google Cloud アカウント（Vision API用）

## セットアップ

### 1. ハードウェアの接続

1. M5Stack UnitV2をM5StackのGroveポートに接続します
2. デフォルトではPortA（GPIO 16/17）を使用します

### 2. Google Cloud Vision API の設定

1. [Google Cloud Console](https://console.cloud.google.com/)にアクセス
2. 新しいプロジェクトを作成
3. Cloud Vision APIを有効化
4. 認証情報でAPIキーを作成
5. `config.py`ファイルの`GOOGLE_API_KEY`に取得したAPIキーを設定

```python
GOOGLE_API_KEY = "your_api_key_here"
```

### 3. ファイルのアップロード

1. `main.py`と`config.py`をM5Stackにアップロード
2. M5Stackを再起動

## 使unitv2/                         # UnitV2直接実行版 ⭐NEW
│   ├── main.py                     # UnitV2メインプログラム
│   └── config_unitv2.py            # UnitV2設定ファイル
├── tools/                          # アップロードツール ⭐NEW
│   ├── upload_to_unitv2.ps1        # UnitV2アップロードスクリプト
│   └── connect_unitv2.ps1          # UnitV2接続ツール
├── platformio.ini                  # PlatformIO設定
├── src/
│   └── main.cpp                    # C++メインプログラム（M5Stack版）
├── include/
│   └── config.h                    # C++設定ファイル
├── main.py                         # Pythonメインプログラム（M5Stack版）
├── simple_ocr.py                   # シンプル版OCR（Python）
├── utils.py                        # ユーティリティ（Python）
├── config.py                       # Python設定ファイル
├── README.md                       # このファイル
├── README_UNITV2.md                # UnitV2詳細ガイド ⭐NEW
├── README_UNITV2_QUICK.md          # UnitV2クイックスタート ⭐NEW
├── QUICKSTART_PLATFORMIO.md        # PlatformIO クイックスタート
├── PLATFORMIO_GUIDE.md             # PlatformIO 詳細ガイド
└── QUICKSTART.md    
│   └── main.cpp                # C++メインプログラム（PlatformIO版）
├── include/
│   └── config.h                # C++設定ファイル
├── main.py                     # Pythonメインプログラム（MicroPython版）
├── simple_ocr.py               # シンプル版OCR（Python）
├── utils.py                    # ユーティリティ（Python）
├── config.py                   # Python設定ファイル
├── README.md                   # このファイル
├── QUICKSTART_PLATFORMIO.md    # PlatformIO クイックスタート
├── PLATFORMIO_GUIDE.md         # PlatformIO 詳細ガイド
└── QUICKSTART.md               # MicroPython クイックスタート
```

## 主な機能

### UnitV2OCRクラス

- `__init__()`: UART通信の初期化
- `capture_image()`: UnitV2で画像をキャプチャ
- `ocr_with_google_vision()`: Google Cloud Vision APIでOCR実行
- `display_result()`: 認識結果を表示

## カスタマイズ

### ピン設定の変更

`config.py`または`main.py`の以下の部分を編集：

```python
UART_TX = 17  # 接続に応じて変更
UART_RX = 16  # 接続に応じて変更
```

### 代替OCRソリューション

Google Cloud Vision APIの代わりに、以下のサービスも使用できます：

1. **Azure Computer Vision API**
2. **AWS Rekognition**
3. **Tesseract OCR（ローカルサーバー経由）**

## トラブルシューティング

### UnitV2が応答しない

- 配線を確認してください
- ボーレートが正しいか確認（デフォルト: 115200）
- UnitV2のファームウェアが最新か確認

### API エラー

- APIキーが正しく設定されているか確認
- Google Cloud ConsoleでVision APIが有効になっているか確認
- APIの使用制限を確認

### Wi-Fi接続エラー

- M5StackがWi-Fiに接続されているか確認
- インターネット接続を確認

## 参考リンク

- [M5Stack UnitV2 製品ページ](https://docs.m5stack.com/en/unit/unitv2)
- [Google Cloud Vision API ドキュメント](https://cloud.google.com/vision/docs)
- [M5Stack UIFlow2.0](https://flow.m5stack.com/)

## ライセンス

MIT License

## 注意事項

- Google Cloud Vision APIは有料サービスです（無料枠あり）
- APIキーは公開しないでください
- 個人情報を含む文書の認識には注意してください

## 今後の改善案

- [ ] オフラインOCR対応（UnitV2のAI機能を活用）
- [ ] 複数言語対応
- [ ] テキストの保存機能
- [ ] リアルタイムOCR
- [ ] カメラ設定の調整機能
