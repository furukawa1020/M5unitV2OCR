"""
UnitV2 OCR - PC側リアルタイム表示版 (API不要・オフライン)

画面構成:
  ┌────────────────────────────┐
  │   UnitV2 カメラ映像 (連続) │  リアルタイムプレビュー
  │  認識テキストをオーバーレイ│
  └────────────────────────────┘

操作:
  q     … 終了
  s     … 今すぐOCR実行
  Space … 自動OCR オン/オフ切替

接続:
  USB:  USB-C ケーブル → SR9900ドライバ → 10.254.239.1
  WiFi: SSID=M5UV2_XXXX  Password=12345678
"""

import sys, os, time, subprocess, threading

# --- 設定 ---
UNITV2_IP    = "10.254.239.1"
OCR_LANG     = "jpn+eng"   # "eng" のみで軽量化可
OCR_INTERVAL = 5.0          # 自動OCR間隔(秒)  0=手動のみ
TESSERACT    = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

FUNC_URL    = f"http://{UNITV2_IP}/func"
STREAM_URL  = f"http://{UNITV2_IP}/video_feed"
WINDOW_NAME = "UnitV2 OCR  [q:終了  s:OCR  Space:自動ON/OFF]"

# ---- グローバル状態 ----
latest_frame  = None
frame_lock    = threading.Lock()
ocr_result    = ""
ocr_lock      = threading.Lock()
ocr_running   = False
auto_ocr      = True
last_ocr_time = 0.0


def log(msg, level="INFO"):
    tag = {"INFO":"[INFO]","OK":"[ OK ]","ERR":"[ERR ]","OCR":"[OCR ]"}.get(level,"[    ]")
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
                    frame = buf[s:e + 2]
                    buf = buf[e + 2:]
                    with frame_lock:
                        latest_frame = frame
                if len(buf) > 200_000:
                    buf = b""
            resp.close()
        except Exception as ex:
            if not stop_event.is_set():
                log(f"ストリームエラー: {ex}", "ERR")
                time.sleep(2)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 画像前処理
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def preprocess(image_bytes):
    try:
        import cv2, numpy as np
        arr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        eq = clahe.apply(gray)
        blur = cv2.GaussianBlur(eq, (3,3), 0)
        binary = cv2.adaptiveThreshold(blur, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
        _, buf = cv2.imencode(".jpg", binary, [cv2.IMWRITE_JPEG_QUALITY, 95])
        return buf.tobytes()
    except Exception:
        return image_bytes


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# OCR (バックグラウンドスレッド)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def _ocr_worker(image_bytes, tess_path):
    global ocr_result, ocr_running
    import tempfile
    tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    base = tmp.name[:-4]
    try:
        tmp.write(preprocess(image_bytes)); tmp.close()
        r = subprocess.run([tess_path, tmp.name, base, "-l", OCR_LANG, "--psm", "3"],
                           capture_output=True, text=True, timeout=30)
        txt_path = base + ".txt"
        if os.path.exists(txt_path):
            with open(txt_path, encoding="utf-8", errors="replace") as f:
                text = "\n".join(ln for ln in f.read().splitlines() if ln.strip())
        else:
            text = ""
        with ocr_lock:
            ocr_result = text if text else "（テキストなし）"
        log(f"OCR完了: {len(text)}文字", "OCR")
        if text:
            log(text[:100].replace("\n","  "), "OCR")
    except Exception as e:
        with ocr_lock: ocr_result = f"（エラー: {e}）"
    finally:
        ocr_running = False
        for p in [tmp.name, base + ".txt"]:
            try: os.unlink(p)
            except: pass


def trigger_ocr(tess_path):
    global ocr_running, last_ocr_time
    if ocr_running: return
    with frame_lock: frame = latest_frame
    if frame is None: return
    ocr_running = True
    last_ocr_time = time.time()
    log("OCR 実行中...")
    threading.Thread(target=_ocr_worker, args=(frame, tess_path), daemon=True).start()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# テキストオーバーレイ描画 (日本語対応)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def draw_overlay(img, text, auto_on, is_ocr_running):
    import cv2, numpy as np
    h, w = img.shape[:2]

    # ステータスバー (上部)
    status = ("OCR実行中...  " if is_ocr_running else "") + \
             f"自動: {'ON' if auto_on else 'OFF'}  {OCR_INTERVAL:.0f}秒毎"
    cv2.rectangle(img, (0, 0), (w, 24), (30, 30, 30), -1)
    cv2.putText(img, status, (6, 17),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 255, 180), 1, cv2.LINE_AA)
    cv2.putText(img, "s:OCR  Space:自動  q:終了", (w - 240, 17),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (140, 140, 140), 1, cv2.LINE_AA)

    # OCR結果パネル (下部) - 日本語対応
    lines = [ln for ln in text.split("\n") if ln.strip()][:8]
    if lines:
        panel_h = len(lines) * 30 + 16
        panel = np.zeros((panel_h, w, 3), dtype=np.uint8)
        try:
            from PIL import Image as PILImage, ImageDraw, ImageFont
            pil = PILImage.fromarray(panel)
            draw = ImageDraw.Draw(pil)
            font = None
            for fp in [r"C:\Windows\Fonts\meiryo.ttc",
                       r"C:\Windows\Fonts\msgothic.ttc",
                       r"C:\Windows\Fonts\YuGothM.ttc"]:
                if os.path.exists(fp):
                    try: font = ImageFont.truetype(fp, 21); break
                    except: pass
            if font is None:
                font = ImageFont.load_default()
            for i, line in enumerate(lines):
                draw.text((8, 6 + i * 30), line, font=font, fill=(50, 255, 50))
            panel = np.array(pil)
        except Exception:
            for i, line in enumerate(lines):
                cv2.putText(panel, line[:70], (8, 24 + i * 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (50, 255, 50), 1, cv2.LINE_AA)
        img = np.vstack([img, panel])

    return img


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 起動ヘルパー
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def check_tesseract():
    for path in ["tesseract", TESSERACT,
                 r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"]:
        try:
            r = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=5)
            if r.returncode == 0:
                log(f"Tesseract: {r.stdout.split(chr(10))[0]}", "OK")
                return path
        except: pass
    return None

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

def install_deps():
    missing = []
    for pkg, mod in [("requests","requests"),("opencv-python","cv2"),("Pillow","PIL")]:
        try: __import__(mod)
        except ImportError: missing.append(pkg)
    if missing:
        log(f"パッケージインストール: {missing}")
        subprocess.run([sys.executable, "-m", "pip", "install"] + missing,
                       check=False, capture_output=True)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# メイン
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def main():
    global auto_ocr, last_ocr_time

    print("=" * 52, flush=True)
    print("  UnitV2 OCR  リアルタイムプレビュー版", flush=True)
    print(f"  接続先: http://{UNITV2_IP}", flush=True)
    print(f"  OCR言語: {OCR_LANG}  自動間隔: {OCR_INTERVAL}秒", flush=True)
    print("=" * 52, flush=True); print("", flush=True)

    install_deps()

    import cv2, numpy as np, requests

    tess = check_tesseract()
    if not tess:
        log("Tesseract未インストール: winget install UB-Mannheim.TesseractOCR", "ERR"); sys.exit(1)

    log("UnitV2 接続確認中...")
    if not check_connection():
        log("接続失敗。USB/WiFi接続を確認してください。", "ERR"); sys.exit(1)
    log("接続OK", "OK")

    session = requests.Session()
    log("camera_stream 起動中...")
    activate_camera_stream(session)

    stop_event = threading.Event()
    st = threading.Thread(target=stream_thread_func, args=(session, stop_event), daemon=True)
    st.start()
    log("ストリーム受信開始", "OK")

    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WINDOW_NAME, 640, 540)
    log("プレビューウィンドウを開きました  (ウィンドウが前面に出ない場合はタスクバーをクリック)", "OK")
    print("", flush=True)

    last_ocr_time = time.time()

    try:
        while True:
            with frame_lock: raw = latest_frame

            if raw is None:
                blank = np.zeros((300, 640, 3), dtype=np.uint8)
                cv2.putText(blank, "Waiting for stream...", (150, 150),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (80, 80, 80), 1)
                cv2.imshow(WINDOW_NAME, blank)
            else:
                arr = np.frombuffer(raw, np.uint8)
                img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                if img is not None:
                    with ocr_lock: result = ocr_result
                    disp = draw_overlay(img.copy(), result, auto_ocr, ocr_running)
                    cv2.imshow(WINDOW_NAME, disp)

            # 自動OCR
            if (auto_ocr and OCR_INTERVAL > 0 and not ocr_running and raw is not None
                    and time.time() - last_ocr_time >= OCR_INTERVAL):
                trigger_ocr(tess)

            key = cv2.waitKey(30) & 0xFF    # 30ms = ~33fps 上限
            if key == ord("q"):
                break
            elif key == ord("s"):
                trigger_ocr(tess)
            elif key == 32:                  # Space
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
