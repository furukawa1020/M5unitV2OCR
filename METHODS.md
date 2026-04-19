# pc_ocr.py — 関数・メソッド一覧

`pc_ocr.py` に含まれる関数の仕様をまとめたリファレンスです。

---

## 目次

1. [log](#log)
2. [run_web_server](#run_web_server)
3. [stream_thread_func](#stream_thread_func)
4. [preprocess_for_easyocr](#preprocess_for_easyocr)
5. [_ocr_worker](#_ocr_worker)
6. [trigger_ocr](#trigger_ocr)
7. [draw_results](#draw_results)
8. [check_connection](#check_connection)
9. [activate_camera_stream](#activate_camera_stream)
10. [main](#main)

---

## log

```python
def log(msg: str, level: str = "INFO") -> None
```

### 概要
タグ付きのログメッセージを標準出力に出力するユーティリティ関数です。

### 引数

| 引数 | 型 | デフォルト | 説明 |
|---|---|---|---|
| `msg` | `str` | ― | 出力するメッセージ |
| `level` | `str` | `"INFO"` | ログレベル。`"INFO"` / `"OK"` / `"ERR"` / `"OCR"` のいずれか |

### 出力例
```
[INFO] Webサーバー起動試行中...
[ OK ] EasyOCR 初期化完了
[ERR ] ストリームエラー: ...
[OCR ] OCR完了: 3件 (1.23秒) - 認識テキスト
```

---

## run_web_server

```python
def run_web_server() -> None
```

### 概要
Flask を用いた Web API サーバーを起動します。デーモンスレッドとして呼び出されることを前提としています。

### エンドポイント

| メソッド | パス | 説明 |
|---|---|---|
| `GET` | `/` | `-/` ディレクトリの `index.html` を返す |
| `GET` | `/<path>` | `-/` ディレクトリの静的ファイルを返す |
| `GET` | `/api/ocr_result` | 最新の OCR 結果を JSON で返す |

### `/api/ocr_result` レスポンス例

```json
{
  "text": "認識したテキスト全体",
  "top_char": "認",
  "raw": [
    {
      "text": "認識したテキスト",
      "conf": 0.95,
      "bbox": [[10, 20], [200, 20], [200, 50], [10, 50]]
    }
  ]
}
```

### CORS
すべてのオリジンからのアクセスを許可します（`Access-Control-Allow-Origin: *`）。

---

## stream_thread_func

```python
def stream_thread_func(session: requests.Session, stop_event: threading.Event) -> None
```

### 概要
UnitV2 の MJPEG ストリームを受信し、グローバル変数 `latest_frame` を継続的に更新するスレッド関数です。

### 引数

| 引数 | 型 | 説明 |
|---|---|---|
| `session` | `requests.Session` | HTTP セッション |
| `stop_event` | `threading.Event` | セットされるとスレッドが終了する |

### 動作
- MJPEG ストリームのバイト列から JPEG フレーム（`\xff\xd8` ～ `\xff\xd9`）を抽出します。
- エラー発生時は 2 秒後に自動で再接続します。
- バッファが 200 KB を超えた場合はバッファをクリアします。

---

## preprocess_for_easyocr

```python
def preprocess_for_easyocr(image_bytes: bytes) -> np.ndarray | None
```

### 概要
EasyOCR に渡す前の前処理（拡大・コントラスト強調・シャープ化）を行います。

### 引数

| 引数 | 型 | 説明 |
|---|---|---|
| `image_bytes` | `bytes` | JPEG 形式の画像バイト列 |

### 戻り値
- RGB 形式の numpy 配列（`np.ndarray`）
- デコードに失敗した場合は `None`

### 処理ステップ

1. **拡大** — `SCALE` 倍に Lanczos 補間でリサイズ
2. **CLAHE** — L チャンネルに対してコントラスト制限付き適応ヒストグラム均等化を適用
3. **アンシャープマスク** — エッジを強調するためのシャープ化

---

## _ocr_worker

```python
def _ocr_worker(image_bytes: bytes) -> None
```

### 概要
バックグラウンドスレッドで EasyOCR を実行し、グローバル変数 `ocr_result` を更新します。`trigger_ocr()` から呼び出されます。

### 引数

| 引数 | 型 | 説明 |
|---|---|---|
| `image_bytes` | `bytes` | JPEG 形式の画像バイト列 |

### 動作
- `preprocess_for_easyocr()` で前処理した後、`easyocr_reader.readtext()` を実行します。
- 信頼度 `CONF_MIN` 未満のテキストはフィルタリングします。
- 処理完了後、`ocr_running` を `False` にリセットします。
- 例外発生時は `ocr_result` を空リストにリセットします。

### EasyOCR パラメータ

| パラメータ | 値 | 説明 |
|---|---|---|
| `text_threshold` | `0.5` | テキスト検出の閾値（デフォルト 0.7 より低め） |
| `low_text` | `0.3` | テキスト確率の下限 |
| `link_threshold` | `0.3` | 文字間リンクの閾値 |
| `contrast_ths` | `0.1` | 低コントラスト文字も検出 |
| `adjust_contrast` | `0.5` | 内部コントラスト補正 |
| `width_ths` | `0.7` | 幅方向の結合閾値 |

---

## trigger_ocr

```python
def trigger_ocr() -> None
```

### 概要
OCR をバックグラウンドスレッドで開始します。既に OCR が実行中の場合、またはフレームが取得できていない場合は何もしません。

### 動作
- `ocr_running` が `True` の場合はスキップ
- `easyocr_reader` が初期化されていない場合はスキップ
- `latest_frame` が `None` の場合はスキップ
- 上記を通過した場合、`_ocr_worker` を新規スレッドで起動

---

## draw_results

```python
def draw_results(
    img: np.ndarray,
    results: list[tuple],
    auto_on: bool,
    is_running: bool,
    scale: float
) -> np.ndarray
```

### 概要
カメラフレームに OCR 結果のバウンディングボックス・信頼度・テキスト一覧を描画します。

### 引数

| 引数 | 型 | 説明 |
|---|---|---|
| `img` | `np.ndarray` | BGR 形式のカメラフレーム |
| `results` | `list` | `(bbox, text, conf)` のリスト（EasyOCR の出力） |
| `auto_on` | `bool` | 自動 OCR の ON/OFF 状態 |
| `is_running` | `bool` | OCR 実行中フラグ |
| `scale` | `float` | 前処理でかけた拡大率（座標補正に使用） |

### 戻り値
描画後の BGR numpy 配列。テキスト一覧パネルが追加されるため、入力より縦方向に大きくなることがあります。

### 描画内容

1. **バウンディングボックス** — OCR 検出領域を緑色のポリラインで描画し、左上に信頼度を表示
2. **ステータスバー（上部）** — 自動 OCR の状態・間隔・信頼度閾値を表示
3. **テキスト一覧パネル（下部）** — Pillow を用いて日本語フォント（メイリオ等）で最大 10 件のテキストを表示

---

## check_connection

```python
def check_connection() -> bool
```

### 概要
UnitV2 の IP アドレス（`UNITV2_IP`）に対してソケット接続を試み、接続可否を返します。

### 戻り値

| 値 | 説明 |
|---|---|
| `True` | ポート `80` への接続成功（UnitV2 に疎通できる） |
| `False` | 接続失敗（タイムアウト等） |

---

## activate_camera_stream

```python
def activate_camera_stream(session: requests.Session) -> bool
```

### 概要
UnitV2 に `camera_stream` 機能の起動を要求します。ストリーム受信前に呼び出します。

### 引数

| 引数 | 型 | 説明 |
|---|---|---|
| `session` | `requests.Session` | HTTP セッション |

### 動作
1. `http://{UNITV2_IP}/` にアクセスしてセッションを確立
2. `POST /func` に `{"type_name":"camera_stream","args":[]}` を送信
3. 成功時は 4 秒待機してストリームが安定するのを待つ

### 戻り値

| 値 | 説明 |
|---|---|
| `True` | HTTP 200 が返り、起動成功 |
| `False` | リクエスト失敗 |

---

## main

```python
def main() -> None
```

### 概要
アプリケーションのエントリポイントです。以下の順序で初期化と メインループを実行します。

### 起動シーケンス

1. 起動メッセージを表示（接続先・OCR 言語・GPU 使用有無）
2. Flask Web サーバーをデーモンスレッドで起動
3. EasyOCR リーダーを初期化
4. `check_connection()` で UnitV2 への接続が成功するまでリトライ
5. `activate_camera_stream()` でカメラストリームを起動
6. `stream_thread_func()` をデーモンスレッドで起動
7. OpenCV のプレビューウィンドウを表示

### メインループ

- 最新フレームを取得し、OCR 結果をオーバーレイして表示
- `OCR_INTERVAL` 秒ごとに自動 OCR を実行
- キー入力を処理

| キー | 動作 |
|---|---|
| `q` | アプリケーション終了 |
| `s` | 即時 OCR 実行 |
| `Space` | 自動 OCR オン / オフ切替 |

---

## グローバル変数

| 変数名 | 型 | 説明 |
|---|---|---|
| `latest_frame` | `bytes \| None` | 最新の JPEG フレーム |
| `frame_lock` | `threading.Lock` | `latest_frame` へのアクセスを保護するロック |
| `ocr_result` | `list` | 最新の OCR 結果 `[(bbox, text, conf), ...]` |
| `ocr_lock` | `threading.Lock` | `ocr_result` へのアクセスを保護するロック |
| `ocr_running` | `bool` | OCR 処理中フラグ |
| `auto_ocr` | `bool` | 自動 OCR 有効フラグ |
| `last_ocr_time` | `float` | 最後に OCR を実行した時刻（`time.time()` 値） |
| `easyocr_reader` | `easyocr.Reader \| None` | EasyOCR リーダーインスタンス |

---

→ [README.md](README.md) — セットアップ・使い方・Web API の概要  
→ [USB_DRIVER_INSTALL.md](USB_DRIVER_INSTALL.md) — SR9900 ドライバのインストール詳細手順
