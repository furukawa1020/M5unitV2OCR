"""
M5Stack UnitV2 OCR - オフライン版 (API不要)

Tesseract OCR を使用してインターネット接続なしで文字認識。

アップロード方法:
  adb connect 10.254.239.1:5555
  adb push main.py /root/
  adb push config_unitv2.py /root/
  adb shell sh /root/setup_tesseract.sh   # 初回のみ
  adb shell python3 /root/main.py
"""

import time
import sys
import os
import subprocess
import tempfile

# 設定ファイルを読み込む
try:
    from config_unitv2 import (
        OCR_ENGINE, TESSERACT_LANG, TESSERACT_PSM,
        CAMERA_WIDTH, CAMERA_HEIGHT,
        AUTO_OCR_INTERVAL, DEBUG_MODE,
        SAVE_IMAGES, SAVE_PATH, PREPROCESS
    )
except ImportError:
    OCR_ENGINE = "tesseract"
    TESSERACT_LANG = "jpn+eng"
    TESSERACT_PSM = "3"
    CAMERA_WIDTH = 640
    CAMERA_HEIGHT = 480
    AUTO_OCR_INTERVAL = 10
    DEBUG_MODE = True
    SAVE_IMAGES = False
    SAVE_PATH = "/root/ocr_images/"
    PREPROCESS = True

def log(msg, level="INFO"):
    prefix = {"INFO": "[INFO]", "OK": "[ OK ]", "ERR": "[ERR ]"}.get(level, "[----]")
    print(f"{prefix} {msg}", flush=True)

def init_camera():
    log("カメラを初期化中...")
    try:
        from maix import camera as maix_camera
        cam = maix_camera.Camera(CAMERA_WIDTH, CAMERA_HEIGHT)
        log(f"カメラ初期化完了 ({CAMERA_WIDTH}x{CAMERA_HEIGHT})", "OK")
        return cam
    except Exception as e:
        log(f"カメラエラー: {e}", "ERR")
        return None

def init_display():
    try:
        from maix import display as maix_display
        disp = maix_display.Display()
        log("ディスプレイ初期化完了", "OK")
        return disp
    except Exception as e:
        log(f"ディスプレイエラー（スキップ）: {e}", "ERR")
        return None

def show_on_display(disp, lines, color=(255, 255, 255), bg=(0, 0, 0)):
    if not disp:
        return
    try:
        from maix import image as maix_image
        img = maix_image.Image(size=(240, 135))
        img.draw_rectangle(0, 0, 240, 135, color=bg, thickness=-1)
        y = 5
        for line in lines[:8]:
            if len(line) > 28:
                line = line[:28] + ".."
            img.draw_string(2, y, line, color=color, scale=1)
            y += 16
        disp.show(img)
    except Exception as e:
        if DEBUG_MODE:
            log(f"表示エラー: {e}", "ERR")

def capture_jpeg(cam):
    try:
        img = cam.read()
        jpeg = img.to_jpeg(quality=90)
        log(f"キャプチャ完了 ({len(jpeg)} bytes)", "OK")
        return jpeg, img
    except Exception as e:
        log(f"キャプチャエラー: {e}", "ERR")
        return None, None

def save_image(jpeg_data, filename=None):
    if not SAVE_IMAGES or not jpeg_data:
        return None
    try:
        os.makedirs(SAVE_PATH, exist_ok=True)
        if filename is None:
            filename = f"ocr_{int(time.time())}.jpg"
        path = os.path.join(SAVE_PATH, filename)
        with open(path, "wb") as f:
            f.write(jpeg_data)
        log(f"画像保存: {path}", "OK")
        return path
    except Exception as e:
        log(f"画像保存エラー: {e}", "ERR")
        return None

def preprocess_image(jpeg_data):
    if not PREPROCESS:
        return jpeg_data
    try:
        import cv2
        import numpy as np
        nparr = np.frombuffer(jpeg_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        denoised = cv2.fastNlMeansDenoising(gray, h=10)
        binary = cv2.adaptiveThreshold(
            denoised, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 11, 2
        )
        _, buf = cv2.imencode(".jpg", binary, [cv2.IMWRITE_JPEG_QUALITY, 95])
        log("前処理完了 (グレースケール+2値化)", "OK")
        return buf.tobytes()
    except Exception as e:
        log(f"前処理スキップ: {e}", "INFO")
        return jpeg_data

def ocr_tesseract(jpeg_data):
    processed = preprocess_image(jpeg_data)
    tmp_img = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
    tmp_base = tmp_img.name[:-4]
    try:
        tmp_img.write(processed)
        tmp_img.close()
        cmd = ["tesseract", tmp_img.name, tmp_base,
               "-l", TESSERACT_LANG, "--psm", TESSERACT_PSM]
        log(f"Tesseract 実行中... (lang={TESSERACT_LANG})")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            return None, f"Tesseract エラー: {result.stderr.strip()}"
        out_file = tmp_base + ".txt"
        if os.path.exists(out_file):
            with open(out_file, "r", encoding="utf-8", errors="replace") as f:
                text = f.read().strip()
            os.unlink(out_file)
            return text, None
        return "", "出力ファイルが見つかりません"
    except FileNotFoundError:
        return None, "Tesseract 未インストール。setup_tesseract.sh を実行してください"
    except subprocess.TimeoutExpired:
        return None, "Tesseract タイムアウト"
    except Exception as e:
        return None, f"OCR エラー: {e}"
    finally:
        try:
            os.unlink(tmp_img.name)
        except Exception:
            pass

def ocr_opencv_only(jpeg_data):
    try:
        import cv2
        import numpy as np
        nparr = np.frombuffer(jpeg_data, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        text_like = [c for c in contours if 20 < cv2.contourArea(c) < 5000]
        info = f"[OpenCV] 文字候補領域: {len(text_like)} 個検出\n"
        info += f"解像度: {img.shape[1]}x{img.shape[0]}\n"
        info += "Tesseract をインストールすると文字内容を読み取れます"
        return info, None
    except ImportError:
        return None, "cv2 も tesseract も使えません。setup_tesseract.sh を実行してください"
    except Exception as e:
        return None, f"OpenCV エラー: {e}"

def run_ocr(jpeg_data):
    if OCR_ENGINE == "tesseract":
        return ocr_tesseract(jpeg_data)
    return ocr_opencv_only(jpeg_data)

def print_ocr_result(text, elapsed=None):
    sep = "=" * 44
    print("", flush=True)
    print(sep, flush=True)
    print("  OCR 認識結果" + (f"  ({elapsed:.1f}秒)" if elapsed else ""), flush=True)
    print(sep, flush=True)
    if text:
        for line in text.split("\n"):
            print(f"  {line}", flush=True)
    else:
        print("  （テキストが検出されませんでした）", flush=True)
    print(sep, flush=True)
    print("", flush=True)

def check_tesseract():
    try:
        r = subprocess.run(["tesseract", "--version"], capture_output=True, text=True, timeout=5)
        if r.returncode == 0:
            ver = r.stdout.split("\n")[0]
            log(f"Tesseract 検出: {ver}", "OK")
            return True
    except Exception:
        pass
    log("Tesseract が見つかりません", "ERR")
    log("  -> sh /root/setup_tesseract.sh を実行してインストールしてください")
    return False

def main():
    log("=" * 44)
    log("  UnitV2 OCR システム起動 (オフライン版)")
    log("  API不要 - Tesseract OCR 使用")
    log("=" * 44)

    cam = init_camera()
    disp = init_display()

    if not cam:
        log("カメラが使えないため終了します", "ERR")
        sys.exit(1)

    tess_ok = check_tesseract()
    if tess_ok:
        show_on_display(disp,
            ["UnitV2 OCR Ready", "", "Tesseract: OK",
             f"lang: {TESSERACT_LANG}", f"間隔: {AUTO_OCR_INTERVAL}s"],
            color=(0, 255, 0))
    else:
        show_on_display(disp,
            ["UnitV2 OCR", "", "Tesseract:", "未インストール", "setup_tesseract.sh"],
            color=(255, 100, 0))

    log(f"OCR エンジン: {OCR_ENGINE}  言語: {TESSERACT_LANG}")
    log(f"OCR 実行間隔: {AUTO_OCR_INTERVAL} 秒 (0=手動)")
    log("停止: Ctrl+C")
    log("=" * 44)

    ocr_count = 0
    error_count = 0

    try:
        while True:
            ocr_count += 1
            t_start = time.time()
            log(f"--- 第 {ocr_count} 回 OCR 開始 ---")
            show_on_display(disp, [f"OCR #{ocr_count}", "撮影中..."], color=(255, 255, 0))

            jpeg, _ = capture_jpeg(cam)
            if jpeg is None:
                error_count += 1
                time.sleep(2)
                continue

            save_image(jpeg, f"ocr_{ocr_count:04d}.jpg")

            show_on_display(disp, [f"OCR #{ocr_count}", "認識中..."], color=(255, 200, 0))
            text, err = run_ocr(jpeg)
            elapsed = time.time() - t_start

            if err:
                error_count += 1
                log(f"OCR エラー: {err}", "ERR")
                show_on_display(disp, [f"OCR #{ocr_count}", "エラー", str(err)[:28]], color=(255, 0, 0))
            else:
                print_ocr_result(text, elapsed)
                lines = ["[OCR 結果]"] + (text.split("\n")[:6] if text else ["(テキストなし)"])
                show_on_display(disp, lines, color=(0, 255, 128))
                log(f"完了 ({elapsed:.1f}秒, {len(text)} 文字)", "OK")

            log(f"--- 第 {ocr_count} 回 完了 (エラー累計: {error_count}) ---")

            if AUTO_OCR_INTERVAL > 0:
                log(f"{AUTO_OCR_INTERVAL} 秒後に次の OCR を実行...")
                time.sleep(AUTO_OCR_INTERVAL)
            else:
                input("Enter キーで次の OCR を実行 > ")

    except KeyboardInterrupt:
        log("停止しました (Ctrl+C)")
    finally:
        log(f"実行回数: {ocr_count}  エラー: {error_count}")
        log("終了")

if __name__ == "__main__":
    main()