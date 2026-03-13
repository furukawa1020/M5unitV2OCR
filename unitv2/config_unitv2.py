"""
UnitV2 OCR 設定ファイル (APモード版)

UnitV2 が WiFi APとして動作:
  SSID: M5UV2_XXXX
  Password: 12345678
  IP: 10.254.239.1
  Web UI: http://10.254.239.1  または  http://unitv2.local
"""

# Google Cloud Vision API Key
# https://console.cloud.google.com/apis/credentials で取得
GOOGLE_API_KEY = ""

# カメラ設定
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480

# OCR設定
AUTO_OCR_INTERVAL = 10   # 秒（自動OCR実行間隔、0=手動のみ）
OCR_TIMEOUT = 10         # 秒（API タイムアウト）

# デバッグ設定
DEBUG_MODE = True

# 画像保存先（認識後に保存する場合）
SAVE_IMAGES = True
SAVE_PATH = "/root/ocr_images/"
