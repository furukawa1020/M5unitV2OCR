"""
UnitV2 OCR - PC側実行スクリプト (API不要・オフライン)

動作原理:
  1. PC を UnitV2 の WiFi AP (M5UV2_XXXX) か USB LAN に接続
  2. UnitV2 のカメラストリームを取得 (http://10.254.239.1)
  3. PC上で Tesseract OCR を実行 (インターネット不要)
  4. 認識結果をリアルタイムで端末に表示

接続方法:
  WiFi: SSID=M5UV2_XXXX  Password=12345678
  USB:  USB-C ケーブルで接続 → SR9900ドライバインストール
        → ネットワークアダプタが自動作成 → 10.254.239.1 で通信可

必要なもの (PC側のみ):
  pip install opencv-python requests pytesseract pillow
  Tesseract本体: https://github.com/UB-Mannheim/tesseract/wiki (Windows)
                → インストール先: C:/Program Files/Tesseract-OCR/tesseract.exe
"""

import sys
import os
import time
import subprocess

# --- 設定 ---
UNITV2_IP   = "10.254.239.1"
OCR_LANG    = "jpn+eng"   # "eng" のみにすると日本語モデル不要で軽量
INTERVAL    = 5            # 秒 (0=連続モード)
TESSERACT   = r"C:\Program Files\Tesseract-OCR\tesseract.exe"  # Windows既定パス

# UnitV2 Flask サーバーエンドポイント (確認済み)
FUNC_URL    = f"http://{UNITV2_IP}/func"          # 機能切替 POST
STREAM_URL  = f"http://{UNITV2_IP}/video_feed"    # MJPEGストリーム

# フォールバック用スナップ候補 (video_feed が失敗した場合)
SNAP_URLS = [
    f"http://{UNITV2_IP}/shot.jpg",
    f"http://{UNITV2_IP}/capture",
]

def log(msg, level="INFO"):
    tag = {"INFO":"[INFO]","OK":"[ OK ]","ERR":"[ERR ]","OCR":"[OCR ]"}.get(level,"[----]")
    print(f"{tag} {msg}", flush=True)


def check_tesseract():
    """PC上の Tesseract を確認"""
    # 環境変数PATH, 既定インストール先, カスタムパスを順に確認
    candidates = [
        "tesseract",
        TESSERACT,
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        "/usr/bin/tesseract",
        "/usr/local/bin/tesseract",
    ]
    for path in candidates:
        try:
            r = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=5)
            if r.returncode == 0:
                ver = r.stdout.split("\n")[0]
                log(f"Tesseract 検出: {ver} ({path})", "OK")
                return path
        except Exception:
            pass
    return None


def run_ocr_tesseract(image_bytes, tess_path, lang=OCR_LANG):
    """Tesseract でOCR実行 (JPEG bytes → テキスト)"""
    import tempfile
    tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    tmp_base = tmp.name[:-4]
    try:
        tmp.write(image_bytes)
        tmp.close()
        cmd = [tess_path, tmp.name, tmp_base, "-l", lang, "--psm", "3"]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if r.returncode != 0:
            return None, f"Tesseract エラー: {r.stderr.strip()}"
        out = tmp_base + ".txt"
        if os.path.exists(out):
            with open(out, encoding="utf-8", errors="replace") as f:
                text = f.read().strip()
            os.unlink(out)
            return text, None
        return "", "出力ファイルなし"
    except FileNotFoundError:
        return None, "tesseract コマンドが見つかりません"
    except Exception as e:
        return None, str(e)
    finally:
        try:
            os.unlink(tmp.name)
        except Exception:
            pass


def preprocess(image_bytes):
    """OpenCV でコントラスト強調・2値化して OCR 精度向上"""
    try:
        import cv2
        import numpy as np
        arr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        # CLAHE でコントラスト均一化
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        eq = clahe.apply(gray)
        # ガウシアンブラーでノイズ除去
        blur = cv2.GaussianBlur(eq, (3, 3), 0)
        # 適応的2値化
        binary = cv2.adaptiveThreshold(
            blur, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 11, 2
        )
        _, buf = cv2.imencode(".jpg", binary, [cv2.IMWRITE_JPEG_QUALITY, 95])
        return buf.tobytes()
    except Exception as e:
        log(f"前処理スキップ ({e})", "INFO")
        return image_bytes


def activate_camera_stream(session):
    """UnitV2 を camera_stream モードに切り替える"""
    try:
        # まず / にアクセスして client_is_connected = True にする (必須)
        session.get(f"http://{UNITV2_IP}/", timeout=8)
        # camera_stream モードに切替
        r = session.post(FUNC_URL,
                         json={"type_name": "camera_stream", "args": []},
                         timeout=10)
        if r.status_code == 200:
            log("camera_stream モード起動", "OK")
            time.sleep(4)  # 起動待ち
            return True
        else:
            log(f"func POST 失敗: {r.status_code}", "ERR")
    except Exception as e:
        log(f"func POST エラー: {e}", "ERR")
    return False


def fetch_from_mjpeg(session):
    """MJPEG ストリーム (multipart/x-mixed-replace) から1フレーム取得"""
    try:
        r = session.get(STREAM_URL, stream=True, timeout=8)
        if r.status_code != 200:
            log(f"video_feed HTTP {r.status_code}", "ERR")
            return None
        buf = b""
        for chunk in r.iter_content(chunk_size=4096):
            buf += chunk
            start = buf.find(b"\xff\xd8")
            end   = buf.rfind(b"\xff\xd9")
            if start != -1 and end != -1 and end > start:
                frame = buf[start:end + 2]
                r.close()
                log(f"フレーム取得: {len(frame)} bytes", "OK")
                return frame
            if len(buf) > 500_000:
                break
        r.close()
    except Exception as e:
        log(f"ストリーム取得エラー: {e}", "ERR")
    return None


def get_frame(session):
    """MJPEG ストリームからフレーム取得 (camera_streamが必要)"""
    return fetch_from_mjpeg(session)


def print_result(text, elapsed, count):
    sep = "=" * 48
    print("", flush=True)
    print(sep, flush=True)
    print(f"  OCR 認識結果  #{count}  ({elapsed:.1f}秒)", flush=True)
    print(sep, flush=True)
    if text and text.strip():
        for line in text.split("\n"):
            if line.strip():
                print(f"  {line}", flush=True)
    else:
        print("  （テキストが検出されませんでした）", flush=True)
    print(sep, flush=True)
    print("", flush=True)


def check_connection():
    """UnitV2 への接続を確認"""
    import socket
    try:
        s = socket.create_connection((UNITV2_IP, 80), timeout=3)
        s.close()
        return True
    except Exception:
        return False


def install_deps():
    """必要な Python パッケージを確認・インストール"""
    missing = []
    for pkg, mod in [("requests","requests"), ("opencv-python","cv2"), ("Pillow","PIL")]:
        try:
            __import__(mod)
        except ImportError:
            missing.append(pkg)
    if missing:
        log(f"不足パッケージをインストール: {missing}", "INFO")
        subprocess.run([sys.executable, "-m", "pip", "install"] + missing, check=False)


def main():
    print("=" * 48, flush=True)
    print("  UnitV2 OCR (PC側実行版)", flush=True)
    print(f"  接続先: http://{UNITV2_IP}", flush=True)
    print(f"  OCR言語: {OCR_LANG}", flush=True)
    print("=" * 48, flush=True)
    print("", flush=True)

    # 依存パッケージ確認
    install_deps()

    # Tesseract 確認
    tess = check_tesseract()
    if not tess:
        print("[ERR] Tesseract がインストールされていません", flush=True)
        print("", flush=True)
        print("  インストール方法:", flush=True)
        print("  1. https://github.com/UB-Mannheim/tesseract/wiki を開く", flush=True)
        print("  2. 最新の Windows インストーラーをダウンロード", flush=True)
        print("  3. インストール時に Japanese + English を選択", flush=True)
        print("  4. このスクリプトを再実行", flush=True)
        print("", flush=True)
        print("  ※ コマンドプロンプトで:", flush=True)
        print("     winget install UB-Mannheim.TesseractOCR", flush=True)
        sys.exit(1)

    # UnitV2 接続確認
    log(f"UnitV2 への接続確認中 ({UNITV2_IP})...")
    if not check_connection():
        print("", flush=True)
        print("[ERR] UnitV2 に接続できません", flush=True)
        print("", flush=True)
        print("  ■ WiFi 接続の場合:", flush=True)
        print(f"    SSID: M5UV2_XXXX  Password: 12345678", flush=True)
        print("    PCのWiFiを UnitV2 のAPに切り替えてください", flush=True)
        print("", flush=True)
        print("  ■ USB 接続の場合:", flush=True)
        print("    USB-C ケーブルで接続 → SR9900 ドライバをインストール", flush=True)
        print("    ドライバ: デバイスマネージャー → 'USB 10/100 LAN' →", flush=True)
        print("    右クリック → ドライバの更新 → 自動検索", flush=True)
        sys.exit(1)
    log(f"UnitV2 接続OK", "OK")

    import requests
    session = requests.Session()
    session.timeout = 8

    # camera_stream モードを起動
    log("UnitV2 を camera_stream モードに切り替え中...")
    if not activate_camera_stream(session):
        log("自動切替失敗 - 手動で http://10.254.239.1 を開いて camera_stream を選択するか続行します", "WAIT")
        time.sleep(2)

    count = 0
    error_count = 0

    log(f"OCR 開始 (間隔: {INTERVAL}秒  停止: Ctrl+C)")
    print("", flush=True)

    try:
        while True:
            count += 1
            t0 = time.time()
            log(f"--- 第{count}回 撮影中... ---")

            raw = get_frame(session)
            if raw is None:
                error_count += 1
                log("フレーム取得失敗 (UnitV2に接続されているか確認)", "ERR")
                time.sleep(3)
                continue

            log("前処理中...")
            processed = preprocess(raw)

            log("OCR 実行中...")
            text, err = run_ocr_tesseract(processed, tess)
            elapsed = time.time() - t0

            if err:
                error_count += 1
                log(f"OCR エラー: {err}", "ERR")
            else:
                print_result(text, elapsed, count)
                log(f"完了 ({elapsed:.1f}秒 / {len(text)}文字)", "OK")

            if INTERVAL > 0:
                time.sleep(INTERVAL)
            else:
                input(f"[Enter で次のOCRを実行]")

    except KeyboardInterrupt:
        print("", flush=True)
        log(f"停止しました  実行: {count}回  エラー: {error_count}")


if __name__ == "__main__":
    main()
