# M5Stack UnitV2 OCR — PC リアルタイムプレビュー版

UnitV2 のカメラ映像を PC で受信し、**EasyOCR**（深層学習）でリアルタイム文字認識するプロジェクトです。  
WiFi **不要**。USB ケーブル 1 本で接続します。

---

## 動作イメージ

```
UnitV2 (カメラ) ─── USB-C ─── SR9900 USB-LAN ─── PC
                                                   │
                                            pc_ocr.py
                                         EasyOCR リアルタイム表示
```

- UnitV2 の映像がリアルタイムでウィンドウに表示される
- 文字が検出されると **緑の枠** でハイライト
- 画面下部に認識テキスト・信頼度一覧を表示

---

## 必要なもの

### ハードウェア
| 品名 | 備考 |
|---|---|
| M5Stack UnitV2 | カメラモジュール |
| USB-C ケーブル | データ転送対応のもの |

> UnitV2 は SR9900 チップの USB-LAN として認識されます。M5Stack 本体は不要です。

### ソフトウェア
| ソフト | バージョン |
|---|---|
| Python | 3.14 (動作確認済) |
| EasyOCR | 1.7.2 |
| OpenCV (`opencv-python`) | 4.13 |
| Pillow | 12.x |
| requests | 最新 |

---

## セットアップ

### 1. SR9900 USB-LAN ドライバのインストール

UnitV2 を PC に USB 接続する前に、ドライバをインストールします。

**PowerShell（管理者）で実行：**
```powershell
.\tools\install_sr9900_driver.ps1
```

インストール後にケーブルを接続し直すと、PC に IP `10.254.239.124`、UnitV2 に `10.254.239.1` が割り当てられます。  
接続確認：
```powershell
ping 10.254.239.1
```

詳細手順 → [USB_DRIVER_INSTALL.md](USB_DRIVER_INSTALL.md)

### 2. Python パッケージのインストール

```powershell
python -m pip install easyocr opencv-python pillow requests
```

> ⚠️ `opencv-python-headless` は GUI が使えないため **インストール禁止**。  
> EasyOCR が自動でインストールしようとしたら手動で削除してください：
> ```powershell
> pip uninstall opencv-python-headless -y
> pip install opencv-python --force-reinstall
> ```

### 3. SSH 鍵の登録（初回のみ）

UnitV2 に公開鍵を登録するとパスワード不要になります：

```powershell
python tools\probe_unitv2.py
```

---

## 使い方

```powershell
python pc_ocr.py
```

| キー | 動作 |
|---|---|
| `s` | 今すぐ OCR 実行 |
| `Space` | 自動 OCR オン / オフ |
| `q` | 終了 |

### 設定のカスタマイズ

`pc_ocr.py` の冒頭部分で調整できます：

```python
OCR_LANGS    = ["ja", "en"]  # 認識言語
OCR_INTERVAL = 5.0           # 自動 OCR 間隔（秒）
CONF_MIN     = 0.1           # 信頼度の下限（0.0〜1.0）
SCALE        = 2.0           # 前処理拡大率（大きいほど精度↑・速度↓）
```

---

## ファイル構成

```
M5unitV2OCR/
├── pc_ocr.py                  ★ メインスクリプト（EasyOCR版）
├── tools/
│   ├── install_sr9900_driver.ps1  SR9900 ドライバインストーラー
│   ├── connect_usb.ps1            USB 接続確認
│   └── probe_unitv2.py            UnitV2 接続テスト・SSH 鍵登録
├── USB_DRIVER_INSTALL.md      ドライバインストール詳細手順
└── README.md                  このファイル
```

---

## トラブルシューティング

### ウィンドウが開かない / `cv2.namedWindow` エラー
`opencv-python-headless` が入っていないか確認：
```powershell
python -m pip list | Select-String opencv
```
`opencv-python-headless` が表示されたら削除して `opencv-python` を再インストールしてください。

### `10.254.239.1` に ping が届かない
- SR9900 ドライバが正しくインストールされているか確認
- デバイスマネージャーで `Corechip SR9900` が「正常」になっているか確認
- USB ケーブルを抜き差し
- `.\tools\connect_usb.ps1` で診断

### OCR が「テキストなし」になる
- ターミナルの `RAW検出: N件` を確認
  - `0件` → カメラが近すぎる / ピンぼけ / 照明不足
  - `N件 (conf < 0.1)` → `CONF_MIN` をさらに下げる（例：`0.05`）
- `SCALE = 3.0` に上げると小さい文字への精度が向上

### 初回起動が遅い
EasyOCR は初回起動時に日英モデル（約 200 MB）をダウンロードします。  
2 回目以降はキャッシュが使われます。

---

## 接続情報

| 項目 | 値 |
|---|---|
| UnitV2 IP | `10.254.239.1` |
| PC IP | `10.254.239.124` |
| 映像 URL | `http://10.254.239.1/video_feed` |
| SSH | `m5stack@10.254.239.1` (鍵認証) |
