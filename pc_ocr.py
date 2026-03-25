"""
UnitV2 OCR - EasyOCR版 リアルタイムプレビュー
OCRエンジン: EasyOCR (深層学習・日本語対応)
初回起動時にモデルをダウンロードします (~200MB、2回目以降はキャッシュ使用)

操作:
  q     … 終了
  s     … 今すぐOCR実行
  Space … 自動OCR オン/オフ切替
"""

import sys, os, time, subprocess, threading, warnings
warnings.filterwarnings("ignore")   # PyTorch pin_memory 警告などを抑制

# ─── 設定 ────────────────────────────────────────
UNITV2_IP    = "10.254.239.1"
OCR_LANGS    = ["ja", "en"]   # EasyOCR言語コード
OCR_INTERVAL = 0               # 自動OCR間隔(秒)  0=待機なし（全力回転）
CONF_MIN     = 0.1             # 信頼度下限 (0.0〜1.0)  低い単語は無視
SCALE        = 2.0             # 前処理拡大率 (3.0は重いので2.0へ戻し、フィルタでカバー)
WEB_PORT     = 8080            # Webサーバーポート

FUNC_URL    = f"http://{UNITV2_IP}/func"
STREAM_URL  = f"http://{UNITV2_IP}/video_feed"
WINDOW_NAME = "UnitV2 OCR (EasyOCR)  [q:終了  s:OCR  Space:自動ON/OFF]"
# ─────────────────────────────────────────────────

latest_frame  = None
frame_lock    = threading.Lock()
ocr_result    = []   # list of (bbox, text, conf)
ocr_lock      = threading.Lock()
ocr_running   = False
auto_ocr      = True
last_ocr_time = 0.0
easyocr_reader = None   # 起動時に初期化


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Web Server (Flask)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def run_web_server():
    from flask import Flask, send_from_directory, jsonify
    app = Flask(__name__, static_folder='-/')

    @app.route('/')
    def index():
        return send_from_directory('-/', 'index.html')

    @app.route('/<path:path>')
    def static_files(path):
        return send_from_directory('-/', path)

    @app.route('/api/ocr_result')
    def get_ocr_result():
        with ocr_lock:
            # テキストを結合して返す
            full_text = "".join([t for _, t, _ in ocr_result]) if ocr_result else ""
            # 最も信頼度の高い1文字を取得（文字認識モード用）
            top_char = ""
            if ocr_result:
                # 信頼度順にソートしたり、単純に最初の文字を使ったり
                top_char = ocr_result[0][1][0] if ocr_result[0][1] else ""
            
            return jsonify({
                "text": full_text,
                "top_char": top_char,
                "raw": [{"text": t, "conf": float(c), "bbox": [[int(x), int(y)] for x, y in b]} for b, t, c in ocr_result]
            })

    log(f"Webサーバー起動中: http://localhost:{WEB_PORT}", "INFO")
    app.run(host='0.0.0.0', port=WEB_PORT, debug=False, use_reloader=False)


def log(msg, level="INFO"):
    tag = {"INFO":"[INFO]","OK":"[ OK ]","ERR":"[ERR ]","OCR":"[OCR ]"}.get(level, "[    ]")
    print(f"{tag} {msg}", flush=True)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MJPEG ストリーム受信スレッド
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def stream_thread_func(session, stop_event):
    global latest_frame
    while not stop_event.is_set():
        try:
            resp = session.get(STREAM_URL, stream=True, timeout=10)
            if resp.status_code != 200:
                time.sleep(2); continue
            buf = b""
            for chunk in resp.iter_content(chunk_size=4096):
                if stop_event.is_set(): break
                buf += chunk
                while True:
                    s = buf.find(b"\xff\xd8")
                    if s == -1: break
                    e = buf.find(b"\xff\xd9", s + 2)
                    if e == -1: break
                    with frame_lock:
                        latest_frame = buf[s:e + 2]
                    buf = buf[e + 2:]
                if len(buf) > 200_000:
                    buf = b""
            resp.close()
        except Exception as ex:
            if not stop_event.is_set():
                log(f"ストリームエラー: {ex}", "ERR")
                time.sleep(2)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 前処理: カラーのまま拡大+シャープのみ
# (EasyOCRはカラー画像を前提とした検出モデルを使う)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def preprocess_for_easyocr(image_bytes):
    import cv2, numpy as np
    arr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)   # BGR
    if img is None:
        return None
    h, w = img.shape[:2]
    if SCALE != 1.0:
        img = cv2.resize(img, (int(w * SCALE), int(h * SCALE)),
                         interpolation=cv2.INTER_LANCZOS4)
    
    # 手書き向け前処理パイプライン (高速化版)
    # 1. グレースケール化
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # 2. ノイズ除去 (高速化のため GaussianBlur に変更)
    # fastNlMeansDenoising はリアルタイムには重すぎるため
    gray = cv2.GaussianBlur(gray, (5, 5), 0)

    # 3. Adaptive Threshold (二値化) - 照明ムラ・影に対応
    binary = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                   cv2.THRESH_BINARY, 11, 2)
    
    # 4. 膨張 (dilate) - 手書きの細い線やかすれをつなげる
    kernel = np.ones((2, 2), np.uint8)
    dilated = cv2.dilate(binary, kernel, iterations=1)

    # 5. EasyOCR用にRGBに戻す (Gray -> RGB)
    return cv2.cvtColor(dilated, cv2.COLOR_GRAY2RGB)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# OCR ワーカー (バックグラウンド)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def _ocr_worker(image_bytes):
    global ocr_result, ocr_running
    start_time = time.time()
    try:
        rgb = preprocess_for_easyocr(image_bytes)
        if rgb is None:
            return
        
        # readtext: detail=1 でバウンディングボックスつき
        raw = easyocr_reader.readtext(
            rgb,
            detail=1,
            paragraph=False,
            # 手書き最適化パラメータ
            batch_size=4,
            width_ths=1.0,         # 字間が広くてもつなげる (デフォルト0.7)
            contrast_ths=0.05,     # 低コントラスト(薄い字)も拾う (デフォルト0.1)
            text_threshold=0.3,    # 確信度が低くても文字候補とする (デフォルト0.5)
            low_text=0.2,          # 文字領域の検出閾値を下げる (デフォルト0.4)
            slope_ths=0.3,         # 斜め書き許容 (デフォルト0.1)
            ycenter_ths=0.7,       # 行の縦ズレ許容 (デフォルト0.5)
        )

        # 信頼度フィルタ
        results = [(bbox, txt, conf)
                   for bbox, txt, conf in raw
                   if conf >= CONF_MIN and txt.strip()]

        with ocr_lock:
            ocr_result = results

        elapsed = time.time() - start_time
        if results:
            log(f"OCR完了: {len(results)}件 ({elapsed:.2f}秒) - {results[0][1]}", "OCR")
        else:
            log(f"OCR完了: 0件 ({elapsed:.2f}秒)", "OCR")

    except Exception as e:
        log(f"OCR例外: {e}", "ERR")
        with ocr_lock:
            ocr_result = []
    finally:
        ocr_running = False


def trigger_ocr():
    global ocr_running, last_ocr_time
    if ocr_running or easyocr_reader is None: return
    with frame_lock: frame = latest_frame
    if frame is None: return
    ocr_running = True
    last_ocr_time = time.time()
    log("OCR 実行中...")
    threading.Thread(target=_ocr_worker, args=(frame,), daemon=True).start()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 描画: バウンディングボックス + テキスト (日本語対応)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def draw_results(img, results, auto_on, is_running, scale):
    """
    img     : BGR numpy array (カメラ解像度)
    results : list of (bbox, text, conf)  ※EasyOCR座標はSCALE適用後
    scale   : 前処理でかけた拡大率 (座標をimg解像度に戻すため割る)
    """
    import cv2, numpy as np
    from PIL import Image as PILImage, ImageDraw, ImageFont

    h, w = img.shape[:2]

    # ─ バウンディングボックス ─
    for bbox, txt, conf in results:
        pts = [(int(x / scale), int(y / scale)) for x, y in bbox]
        pts_arr = np.array(pts, dtype=np.int32).reshape((-1, 1, 2))  # cv2.polylines は (N,1,2) 必須
        cv2.polylines(img, [pts_arr], True, (0, 255, 80), 2)
        # 左上にconfidence
        cv2.putText(img, f"{conf:.0%}", pts[0],
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 220, 60), 1, cv2.LINE_AA)

    # ─ ステータスバー (上部, cv2で描く) ─
    status = ("OCR実行中...  " if is_running else "") + \
             f"自動: {'ON' if auto_on else 'OFF'}  {OCR_INTERVAL:.0f}秒毎  " \
             f"(EasyOCR conf>={CONF_MIN:.0%})"
    cv2.rectangle(img, (0, 0), (w, 24), (20, 20, 20), -1)
    cv2.putText(img, status, (6, 17),
                cv2.FONT_HERSHEY_SIMPLEX, 0.48, (180, 255, 180), 1, cv2.LINE_AA)
    cv2.putText(img, "s:OCR  Space:自動  q:終了", (w - 240, 17),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (130, 130, 130), 1, cv2.LINE_AA)

    # ─ テキスト一覧パネル (下部, Pillowで日本語描画) ─
    lines = [f"[{conf:.0%}] {txt}" for _, txt, conf in results][:10]
    if lines:
        LINE_H = 28
        panel_h = len(lines) * LINE_H + 12
        panel_bgr = np.zeros((panel_h, w, 3), dtype=np.uint8)
        try:
            pil = PILImage.fromarray(cv2.cvtColor(panel_bgr, cv2.COLOR_BGR2RGB))
            draw = ImageDraw.Draw(pil)
            font = None
            for fp in [r"C:\Windows\Fonts\meiryo.ttc",
                       r"C:\Windows\Fonts\msgothic.ttc",
                       r"C:\Windows\Fonts\YuGothM.ttc"]:
                if os.path.exists(fp):
                    try: font = ImageFont.truetype(fp, 18); break
                    except: pass
            if font is None: font = ImageFont.load_default()
            for i, line in enumerate(lines):
                draw.text((8, 5 + i * LINE_H), line, font=font, fill=(80, 255, 80))
            panel_bgr = cv2.cvtColor(np.array(pil), cv2.COLOR_RGB2BGR)
        except Exception:
            for i, line in enumerate(lines):
                cv2.putText(panel_bgr, line[:80], (8, 22 + i * LINE_H),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.55, (50, 255, 50), 1, cv2.LINE_AA)
        img = np.vstack([img, panel_bgr])

    return img


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ユーティリティ
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def check_connection():
    import socket
    try:
        s = socket.create_connection((UNITV2_IP, 80), timeout=3); s.close(); return True
    except: return False

def activate_camera_stream(session):
    try:
        session.get(f"http://{UNITV2_IP}/", timeout=8)
        r = session.post(FUNC_URL, json={"type_name":"camera_stream","args":[]}, timeout=10)
        if r.status_code == 200:
            log("camera_stream 起動", "OK"); time.sleep(4); return True
    except Exception as e:
        log(f"camera_stream 起動失敗: {e}", "ERR")
    return False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# メイン
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def main():
    global auto_ocr, last_ocr_time, easyocr_reader

    print("=" * 56, flush=True)
    print("  UnitV2 OCR  EasyOCR版 リアルタイムプレビュー", flush=True)
    print(f"  接続先: http://{UNITV2_IP}", flush=True)
    print(f"  OCR言語: {OCR_LANGS}  自動間隔: {OCR_INTERVAL}秒", flush=True)
    import torch
    print(f"  GPU使用: {torch.cuda.is_available()} ({torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'N/A'})")
    print("=" * 56, flush=True); print("", flush=True)

    import cv2, numpy as np, requests

    # ── Webサーバー起動 (最優先) ──
    threading.Thread(target=run_web_server, daemon=True).start()
    log("Webサーバー起動試行中...", "INFO")

    # ── EasyOCR 初期化 ──
    log(f"EasyOCR 初期化中... (GPU: {torch.cuda.is_available()})")
    try:
        import easyocr
        easyocr_reader = easyocr.Reader(OCR_LANGS, gpu=True, verbose=False)
        log("EasyOCR 初期化完了", "OK")
    except ImportError:
        log("easyocr 未インストール: pip install easyocr", "ERR"); sys.exit(1)
    except Exception as e:
        log(f"EasyOCR 初期化失敗: {e}", "ERR"); sys.exit(1)

    # ── UnitV2 接続 (リトライループ) ──
    log("UnitV2 接続確認中...")
    session = requests.Session()
    stop_event = threading.Event()

    # 接続待機ループ
    connected_once = False
    while not connected_once:
        if check_connection():
            log("接続OK", "OK")
            connected_once = True
        else:
            log(f"接続失敗: {UNITV2_IP} に繋がりません。再試行中... (3秒後)", "ERR")
            # プレビューウィンドウを一応出しておく（ユーザーが状況わかるように）
            blank = np.zeros((300, 640, 3), dtype=np.uint8)
            cv2.putText(blank, "Connecting to UnitV2...", (50, 150),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 1)
            cv2.imshow(WINDOW_NAME, blank)
            if cv2.waitKey(3000) & 0xFF == ord('q'):
                sys.exit(0)

    log("camera_stream 起動中...")
    activate_camera_stream(session)

    threading.Thread(target=stream_thread_func, args=(session, stop_event),
                     daemon=True).start()
    log("ストリーム受信開始", "OK")

    # Start Web Server (移動済み)
    # threading.Thread(target=run_web_server, daemon=True).start()

    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WINDOW_NAME, 640, 560)
    log("プレビューウィンドウを開きました  (前面に出ない場合はタスクバーをクリック)", "OK")
    print("", flush=True)

    last_ocr_time = time.time()

    try:
        while True:
            with frame_lock: raw = latest_frame

            if raw is None:
                blank = np.zeros((300, 640, 3), dtype=np.uint8)
                cv2.putText(blank, "Waiting for stream...", (140, 150),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (70, 70, 70), 1)
                cv2.imshow(WINDOW_NAME, blank)
            else:
                arr = np.frombuffer(raw, np.uint8)
                img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                if img is not None:
                    with ocr_lock: results = list(ocr_result)
                    disp = draw_results(img.copy(), results, auto_ocr, ocr_running, SCALE)
                    cv2.imshow(WINDOW_NAME, disp)

            # 自動OCR
            if (auto_ocr and not ocr_running and raw is not None
                    and time.time() - last_ocr_time >= OCR_INTERVAL):
                trigger_ocr()

            key = cv2.waitKey(30) & 0xFF
            if key == ord("q"):
                break
            elif key == ord("s"):
                trigger_ocr()
            elif key == 32:
                auto_ocr = not auto_ocr
                log(f"自動OCR: {'ON' if auto_ocr else 'OFF'}")

            if cv2.getWindowProperty(WINDOW_NAME, cv2.WND_PROP_VISIBLE) < 1:
                break

    except KeyboardInterrupt:
        pass
    finally:
        stop_event.set()
        cv2.destroyAllWindows()
        log("終了")


if __name__ == "__main__":
    main()
