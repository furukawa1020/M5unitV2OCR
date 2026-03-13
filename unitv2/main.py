"""
M5Stack UnitV2 OCR - UnitV2直接実行版 (APモード対応)

UnitV2 が WiFi AP として動作:
  SSID: M5UV2_XXXX  Password: 12345678
  Web UI: http://10.254.239.1

アップロード方法:
  adb connect 10.254.239.1:5555
  adb push main.py /root/
  adb push config_unitv2.py /root/
  adb shell python3 /root/main.py
"""

import time
import sys
import os
import json
import base64

# 設定ファイルを読み込む
try:
    from config_unitv2 import (
        GOOGLE_API_KEY, CAMERA_WIDTH, CAMERA_HEIGHT,
        AUTO_OCR_INTERVAL, OCR_TIMEOUT, DEBUG_MODE,
        SAVE_IMAGES, SAVE_PATH
    )
except ImportError:
    GOOGLE_API_KEY = ""
    CAMERA_WIDTH = 640
    CAMERA_HEIGHT = 480
    AUTO_OCR_INTERVAL = 10
    OCR_TIMEOUT = 10
    DEBUG_MODE = True
    SAVE_IMAGES = False
    SAVE_PATH = "/root/ocr_images/"

def log(msg, level="INFO"):
    """ログ出力（リアルタイムでflush）"""
    prefix = {"INFO": "[INFO]", "OK": "[ OK ]", "ERR": "[ERR ]", "OCR": "[OCR ]"}.get(level, "[----]")
    print(f"{prefix} {msg}", flush=True)

def init_camera():
    """カメラ初期化"""
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
    """ディスプレイ初期化"""
    try:
        from maix import display as maix_display
        disp = maix_display.Display()
        log("ディスプレイ初期化完了", "OK")
        return disp
    except Exception as e:
        log(f"ディスプレイエラー（スキップ）: {e}", "ERR")
        return None

def show_on_display(disp, lines, color=(255, 255, 255), bg=(0, 0, 0)):
    """ディスプレイにテキスト表示"""
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
    """画像をキャプチャしてJPEGバイトを返す"""
    try:
        img = cam.read()
        jpeg = img.to_jpeg(quality=85)
        log(f"キャプチャ完了 ({len(jpeg)} bytes)", "OK")
        return jpeg, img
    except Exception as e:
        log(f"キャプチャエラー: {e}", "ERR")
        return None, None

def save_image(jpeg_data, filename=None):
    """画像をファイルに保存"""
    if not SAVE_IMAGES or not jpeg_data:
        return
    try:
        os.makedirs(SAVE_PATH, exist_ok=True)
        if filename is None:
            filename = f"ocr_{int(time.time())}.jpg"
        path = os.path.join(SAVE_PATH, filename)
        with open(path, 'wb') as f:
            f.write(jpeg_data)
        log(f"画像保存: {path}", "OK")
    except Exception as e:
        log(f"画像保存エラー: {e}", "ERR")

def ocr_google_vision(jpeg_data):
    """
    Google Cloud Vision API で OCR を実行
    Returns: (テキスト, エラーメッセージ)
    """
    if not GOOGLE_API_KEY:
        return None, "API Key が設定されていません (config_unitv2.py の GOOGLE_API_KEY を設定)"

    url = f"https://vision.googleapis.com/v1/images:annotate?key={GOOGLE_API_KEY}"
    payload = json.dumps({
        "requests": [{
            "image": {"content": base64.b64encode(jpeg_data).decode("utf-8")},
            "features": [{"type": "TEXT_DETECTION", "maxResults": 50}]
        }]
    }).encode("utf-8")

    # requests モジュールを試みる、なければ urllib にフォールバック
    try:
        import requests as req
        log("Google Vision API に送信中...")
        resp = req.post(url, data=payload,
                        headers={"Content-Type": "application/json"},
                        timeout=OCR_TIMEOUT)
        if resp.status_code != 200:
            return None, f"API エラー: HTTP {resp.status_code}"
        data = resp.json()
    except ImportError:
        import urllib.request
        log("Google Vision API に送信中 (urllib)...")
        try:
            request = urllib.request.Request(
                url, data=payload,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(request, timeout=OCR_TIMEOUT) as r:
                data = json.loads(r.read().decode("utf-8"))
        except Exception as e:
            return None, f"urllib エラー: {e}"
    except Exception as e:
        return None, f"OCR 実行エラー: {e}"

    annotations = data.get("responses", [{}])[0].get("textAnnotations", [])
    if annotations:
        return annotations[0]["description"].strip(), None
    return "", "テキストが検出されませんでした"

def print_ocr_result(text, elapsed=None):
    """OCR 結果をリアルタイムで見やすく出力"""
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

def main():
    """メイン処理"""
    log("=" * 44)
    log("  UnitV2 OCR システム起動")
    log("  APモード: 10.254.239.1")
    log("=" * 44)

    cam = init_camera()
    disp = init_display()

    if not cam:
        log("カメラが使えないため終了します", "ERR")
        sys.exit(1)

    if not GOOGLE_API_KEY:
        log("警告: GOOGLE_API_KEY が未設定です", "ERR")
        log("  /root/config_unitv2.py を編集して設定してください")
        show_on_display(disp,
            ["UnitV2 OCR", "", "API Key 未設定", "config_unitv2.py", "を編集してください"],
            color=(255, 100, 0))
    else:
        log(f"API Key: {GOOGLE_API_KEY[:8]}...", "OK")
        show_on_display(disp,
            ["UnitV2 OCR Ready", "", "API Key: OK", f"間隔: {AUTO_OCR_INTERVAL}秒"],
            color=(0, 255, 0))

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

            show_on_display(disp, [f"OCR #{ocr_count}", "API 送信中..."], color=(255, 200, 0))
            text, err = ocr_google_vision(jpeg)
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
