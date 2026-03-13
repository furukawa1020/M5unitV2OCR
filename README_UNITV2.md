# M5Stack UnitV2 OCR - UnitV2直接プログラミング版

## UnitV2について

### ハードウェア仕様
- **チップ**: Allwinner V831 (ARM Cortex-A7 800MHz)
- **メモリ**: 64MB DDR2
- **ストレージ**: microSDカード対応
- **カメラ**: GC2145 (2MP)
- **画面**: 1.14インチ TFT (240x135)
- **接続**: USB-C + UART (Grove)
- **AI機能**: NPU搭載（画像認識、物体検出など）

### 開発環境

UnitV2は以下の方法でプログラミング可能：

1. **MaixPy3** (Python) - 推奨
2. **Web UI** - ビジュアルプログラミング
3. **Linux環境** - 直接ファームウェア開発

## MaixPy3による開発

### 必要なもの
- UnitV2本体
- USB-Cケーブル（データ転送対応）
- microSDカード（オプション、プログラム保存用）
- PC（Windows/Mac/Linux）

### 開発手順

#### 1. ファームウェアの確認・更新

UnitV2は出荷時からMaixPy3ファームウェアが搭載されています。

**ファームウェアダウンロード:**
- M5Stack公式: https://docs.m5stack.com/en/unit/unitv2
- GitHub: https://github.com/m5stack/UnitV2_Firmware

#### 2. 開発環境のセットアップ

##### 方法A: Web IDE（最も簡単）

1. UnitV2をUSB接続
2. WiFi設定を行う
3. UnitV2のIPアドレスにブラウザでアクセス
4. Web IDEでコード編集・実行

##### 方法B: Python + adb/ssh

```bash
# Python環境準備
pip install maixpy3-dev

# UnitV2に接続（adb経由）
adb connect <UnitV2_IP>:5555

# または SSH経由
ssh root@<UnitV2_IP>
# パスワード: root
```

##### 方法C: VS Code + Remote SSH

1. VS Codeに「Remote - SSH」拡張機能をインストール
2. UnitV2にSSH接続
3. リモート環境でコード編集

#### 3. OCRの実装方法

##### オプション1: UnitV2内蔵のOCR機能を使用

UnitV2はファームウェアに組み込まれたOCR機能を持っています。

```python
# UnitV2のMaixPy3コード例
from maix import camera, display, image
import time

# カメラ初期化
cam = camera.Camera(640, 480)

# ディスプレイ初期化  
disp = display.Display()

while True:
    # 画像キャプチャ
    img = cam.read()
    
    # OCR実行（UnitV2内蔵機能）
    # ※ 現在のファームウェアバージョンによって利用可能
    
    # 画像を表示
    disp.show(img)
    
    time.sleep(0.1)
```

##### オプション2: 外部API経由（Google Vision API）

```python
# UnitV2でGoogle Vision APIを使用
import requests
import base64
from maix import camera
import json

GOOGLE_API_KEY = "your_api_key"

def ocr_with_google(image_data):
    url = f"https://vision.googleapis.com/v1/images:annotate?key={GOOGLE_API_KEY}"
    
    # Base64エンコード
    image_base64 = base64.b64encode(image_data).decode()
    
    payload = {
        "requests": [{
            "image": {"content": image_base64},
            "features": [{"type": "TEXT_DETECTION"}]
        }]
    }
    
    response = requests.post(url, json=payload)
    result = response.json()
    
    if result.get('responses'):
        annotations = result['responses'][0].get('textAnnotations', [])
        if annotations:
            return annotations[0]['description']
    return ""

# メインループ
cam = camera.Camera()

while True:
    img = cam.read()
    
    # 画像をJPEGに変換
    img_bytes = img.to_jpeg()
    
    # OCR実行
    text = ocr_with_google(img_bytes)
    print(f"認識結果: {text}")
    
    time.sleep(1)
```

##### オプション3: Tesseract OCR（ローカル処理）

UnitV2上でTesseract OCRを実行することも可能（要カスタムファームウェア）

#### 4. プログラムのアップロード

##### 方法A: adb push

```bash
# プログラムをUnitV2にアップロード
adb push main.py /root/

# 実行
adb shell python3 /root/main.py
```

##### 方法B: Web UI経由

1. Web IDEでコードを編集
2. 「保存」ボタンでUnitV2に保存
3. 「実行」ボタンで起動

##### 方法C: SSH/SCP

```bash
# SCPでファイル転送
scp main.py root@<UnitV2_IP>:/root/

# SSH接続して実行
ssh root@<UnitV2_IP>
python3 /root/main.py
```

#### 5. 自動起動設定

起動時に自動実行させる：

```bash
# SSH接続
ssh root@<UnitV2_IP>

# 自動起動スクリプトを編集
vi /etc/init.d/S99custom

# 以下を追加
#!/bin/sh
python3 /root/main.py &

# 実行権限付与
chmod +x /etc/init.d/S99custom
```

### UnitV2のネットワーク設定

#### WiFi接続

```python
# WiFi設定（MaixPy3）
from maix import network

# WiFiに接続
network.wifi.connect("SSID", "PASSWORD")

# IPアドレス確認
ip = network.wifi.ifconfig()
print(f"IP: {ip}")
```

#### Web UIへのアクセス

1. UnitV2の電源を入れる
2. WiFi接続を設定
3. ブラウザで `http://<UnitV2_IP>` にアクセス
4. Web IDEが開きます

### デバッグ方法

#### シリアル接続でログ確認

```bash
# Windows
& "$env:USERPROFILE\.platformio\penv\Scripts\platformio.exe" device monitor -b 115200

# Linux/Mac  
screen /dev/ttyUSB0 115200
```

#### adb logcat

```bash
adb connect <UnitV2_IP>:5555
adb logcat
```

## プロジェクト構造（UnitV2版）

```
M5unitV2OCR/
├── unitv2/
│   ├── main.py              # UnitV2のメインプログラム
│   ├── ocr_module.py        # OCR処理モジュール
│   ├── camera_utils.py      # カメラユーティリティ
│   └── config.py            # 設定ファイル
├── tools/
│   ├── upload.sh            # アップロードスクリプト
│   └── connect.sh           # 接続スクリプト
└── README_UNITV2.md        # UnitV2開発ガイド
```

## トラブルシューティング

### UnitV2が認識されない

1. **USB-Cケーブル確認** - データ転送対応か
2. **adbドライバ** - Android SDK Platform Toolsをインストール
3. **デバイスモード** - UnitV2を開発者モードにする

### WiFi接続できない

1. 2.4GHz WiFiを使用（5GHzは非対応）
2. UnitV2を工場出荷状態にリセット
3. シリアル経由で手動設定

### プログラムが動かない

1. Python版の確認（Python 3.x）
2. 必要なモジュールがインストールされているか
3. ファームウェアバージョンの確認

## 参考リンク

- [M5Stack UnitV2 公式ドキュメント](https://docs.m5stack.com/en/unit/unitv2)
- [MaixPy3 ドキュメント](https://wiki.sipeed.com/maixpy3/)
- [UnitV2 GitHub](https://github.com/m5stack/UnitV2_Firmware)
- [M5Stack Community Forum](https://community.m5stack.com/)

## 次のステップ

実際のUnitV2用コードを[unitv2/main.py](unitv2/main.py)で作成します。
