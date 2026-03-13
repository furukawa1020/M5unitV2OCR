"""
UnitV2 OCR 設定ファイル (オフライン・API不要版)

UnitV2 が WiFi APとして動作:
  SSID: M5UV2_XXXX
  Password: 12345678
  IP: 10.254.239.1
  Web UI: http://10.254.239.1
"""

# ===== OCR エンジン設定 =====
# "tesseract" : Tesseract OCR（推奨、要インストール）
# "opencv"    : OpenCV のみ（インストール不要、精度低め）
OCR_ENGINE = "tesseract"

# Tesseract 言語設定
# "jpn"     : 日本語
# "eng"     : 英語
# "jpn+eng" : 日本語＋英語（混在）
TESSERACT_LANG = "jpn+eng"

# Tesseract ページセグメントモード (PSM)
# 3=自動(推奨), 6=1ブロック, 11=1行
TESSERACT_PSM = "3"

# カメラ設定
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480

# OCR設定
AUTO_OCR_INTERVAL = 10   # 秒（0=手動のみ）

# デバッグ設定
DEBUG_MODE = True

# 画像保存先
SAVE_IMAGES = True
SAVE_PATH = "/root/ocr_images/"

# 前処理（グレースケール＋2値化でOCR精度向上）
PREPROCESS = True
