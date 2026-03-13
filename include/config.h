/**
 * M5UnitV2 OCR - 設定ファイル
 * WiFiとAPIの設定を記載
 */

#ifndef CONFIG_H
#define CONFIG_H

// WiFi設定
#define WIFI_SSID "your_wifi_ssid"
#define WIFI_PASSWORD "your_wifi_password"

// Google Cloud Vision API Key
// https://console.cloud.google.com/apis/credentials で取得
#define GOOGLE_API_KEY "your_google_api_key_here"

// UART設定（UnitV2）
#define UNITV2_RX_PIN 16
#define UNITV2_TX_PIN 17
#define UNITV2_BAUDRATE 115200

// デバッグ設定
#define DEBUG_MODE true

#endif // CONFIG_H
