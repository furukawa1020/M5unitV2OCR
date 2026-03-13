"""
M5UnitV2 OCR 設定ファイル
Google Cloud Vision APIの設定を記載
"""

# Google Cloud Vision API設定
# https://console.cloud.google.com/apis/credentials でAPIキーを取得
GOOGLE_API_KEY = ""  # ここにあなたのAPIキーを入力

# UART設定
UART_TX = 17  # UnitV2 TX接続ピン（必要に応じて変更）
UART_RX = 16  # UnitV2 RX接続ピン（必要に応じて変更）
BAUDRATE = 115200

# その他の設定
DEBUG_MODE = True  # デバッグメッセージを表示
