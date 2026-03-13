/**
 * M5Stack UnitV2 OCR - C++/Arduino版
 * PlatformIOを使用してUSB経由でビルド・アップロード
 * 
 * 必要なハードウェア:
 * - M5Stack (Core2, Basic, Grayなど)
 * - M5Stack UnitV2カメラモジュール
 * 
 * 接続:
 * - UnitV2をPortA (GPIO 16/17)に接続
 */

#include <M5Stack.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <base64.h>

// WiFi設定 - config.hから読み込むか、ここに直接記入
#ifndef WIFI_SSID
#define WIFI_SSID "your_wifi_ssid"
#define WIFI_PASSWORD "your_wifi_password"
#endif

// Google Cloud Vision API設定
#ifndef GOOGLE_API_KEY
#define GOOGLE_API_KEY "your_google_api_key_here"
#endif

// UnitV2 UART設定
#define UNITV2_RX 16  // M5Stack RX (UnitV2 TX)
#define UNITV2_TX 17  // M5Stack TX (UnitV2 RX)
#define UNITV2_BAUDRATE 115200

// グローバル変数
HardwareSerial UnitV2Serial(2);
bool wifiConnected = false;
String lastOcrResult = "";

/**
 * WiFiに接続
 */
void connectWiFi() {
  M5.Lcd.println("WiFi connecting...");
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    M5.Lcd.print(".");
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    wifiConnected = true;
    M5.Lcd.println("\nWiFi Connected!");
    M5.Lcd.print("IP: ");
    M5.Lcd.println(WiFi.localIP());
    Serial.println("WiFi Connected!");
    Serial.print("IP: ");
    Serial.println(WiFi.localIP());
  } else {
    wifiConnected = false;
    M5.Lcd.println("\nWiFi Failed!");
    Serial.println("WiFi Connection Failed!");
  }
}

/**
 * UnitV2から画像をキャプチャ
 */
bool captureImageFromUnitV2(uint8_t* buffer, size_t* length) {
  // UnitV2にキャプチャコマンドを送信
  UnitV2Serial.println("{\"cmd\":\"capture\"}");
  
  delay(500);  // キャプチャ待機
  
  // レスポンスを読み取り
  if (UnitV2Serial.available()) {
    size_t bytesRead = 0;
    while (UnitV2Serial.available() && bytesRead < *length) {
      buffer[bytesRead++] = UnitV2Serial.read();
    }
    *length = bytesRead;
    return bytesRead > 0;
  }
  
  return false;
}

/**
 * Google Cloud Vision APIでOCRを実行
 */
String performOCR(const uint8_t* imageData, size_t imageSize) {
  if (!wifiConnected) {
    Serial.println("WiFi not connected!");
    return "Error: WiFi not connected";
  }
  
  HTTPClient http;
  String url = "https://vision.googleapis.com/v1/images:annotate?key=";
  url += GOOGLE_API_KEY;
  
  // 画像をBase64エンコード
  String imageBase64 = base64::encode(imageData, imageSize);
  
  // JSONペイロードを作成
  StaticJsonDocument<8192> doc;
  JsonArray requests = doc.createNestedArray("requests");
  JsonObject request = requests.createNestedObject();
  
  JsonObject image = request.createNestedObject("image");
  image["content"] = imageBase64;
  
  JsonArray features = request.createNestedArray("features");
  JsonObject feature = features.createNestedObject();
  feature["type"] = "TEXT_DETECTION";
  feature["maxResults"] = 10;
  
  String jsonPayload;
  serializeJson(doc, jsonPayload);
  
  // HTTPリクエストを送信
  http.begin(url);
  http.addHeader("Content-Type", "application/json");
  
  Serial.println("Sending OCR request...");
  int httpCode = http.POST(jsonPayload);
  
  String result = "";
  
  if (httpCode == HTTP_CODE_OK) {
    String response = http.getString();
    
    // レスポンスをパース
    DynamicJsonDocument responseDoc(16384);
    DeserializationError error = deserializeJson(responseDoc, response);
    
    if (!error) {
      JsonArray responses = responseDoc["responses"];
      if (responses.size() > 0) {
        JsonArray textAnnotations = responses[0]["textAnnotations"];
        if (textAnnotations.size() > 0) {
          result = textAnnotations[0]["description"].as<String>();
          Serial.println("OCR Success!");
        } else {
          result = "No text detected";
          Serial.println("No text detected");
        }
      }
    } else {
      result = "Parse error";
      Serial.println("JSON parse error");
    }
  } else {
    result = "HTTP Error: " + String(httpCode);
    Serial.print("HTTP Error: ");
    Serial.println(httpCode);
  }
  
  http.end();
  return result;
}

/**
 * 画面に結果を表示
 */
void displayResult(const String& text) {
  M5.Lcd.fillScreen(BLACK);
  M5.Lcd.setCursor(0, 0);
  M5.Lcd.setTextColor(WHITE);
  M5.Lcd.setTextSize(2);
  M5.Lcd.println("OCR Result:");
  M5.Lcd.println("================");
  M5.Lcd.setTextSize(1);
  
  // テキストを表示（長い場合は切り詰める）
  String displayText = text;
  if (displayText.length() > 200) {
    displayText = displayText.substring(0, 200) + "...";
  }
  
  M5.Lcd.println(displayText);
  
  // ボタンガイドを表示
  M5.Lcd.setCursor(0, 220);
  M5.Lcd.println("A:Capture  B:Clear");
}

/**
 * 初期画面を表示
 */
void displayMainScreen() {
  M5.Lcd.fillScreen(BLACK);
  M5.Lcd.setCursor(0, 0);
  M5.Lcd.setTextColor(WHITE);
  M5.Lcd.setTextSize(2);
  M5.Lcd.println("M5UnitV2 OCR");
  M5.Lcd.println("================");
  M5.Lcd.setTextSize(1);
  M5.Lcd.println();
  M5.Lcd.println("Status:");
  M5.Lcd.print("WiFi: ");
  M5.Lcd.println(wifiConnected ? "Connected" : "Disconnected");
  M5.Lcd.println();
  M5.Lcd.println("Instructions:");
  M5.Lcd.println("- Point camera at text");
  M5.Lcd.println("- Press A to capture & OCR");
  M5.Lcd.println("- Press B to reconnect WiFi");
  M5.Lcd.println("- Press C for system info");
  M5.Lcd.println();
  
  if (!lastOcrResult.isEmpty()) {
    M5.Lcd.println("Last Result:");
    String preview = lastOcrResult.substring(0, min(50, (int)lastOcrResult.length()));
    M5.Lcd.println(preview + "...");
  }
}

void setup() {
  // M5Stack初期化
  M5.begin();
  M5.Power.begin();
  
  // シリアル初期化
  Serial.begin(115200);
  Serial.println("\n\n=================================");
  Serial.println("M5Stack UnitV2 OCR System");
  Serial.println("=================================\n");
  
  // LCD設定
  M5.Lcd.setTextSize(1);
  M5.Lcd.setTextColor(WHITE);
  M5.Lcd.fillScreen(BLACK);
  
  M5.Lcd.println("Initializing...");
  
  // UnitV2 UART初期化
  UnitV2Serial.begin(UNITV2_BAUDRATE, SERIAL_8N1, UNITV2_RX, UNITV2_TX);
  M5.Lcd.println("UnitV2 UART: OK");
  Serial.println("UnitV2 UART initialized");
  
  delay(500);
  
  // WiFi接続
  connectWiFi();
  
  delay(1000);
  
  // メイン画面表示
  displayMainScreen();
  
  Serial.println("\nSystem ready!");
  Serial.println("Press A button to capture and perform OCR");
}

void loop() {
  M5.update();
  
  // Aボタン: 画像キャプチャ & OCR実行
  if (M5.BtnA.wasPressed()) {
    Serial.println("\n--- Capture & OCR Start ---");
    
    M5.Lcd.fillScreen(BLACK);
    M5.Lcd.setCursor(10, 100);
    M5.Lcd.setTextSize(2);
    M5.Lcd.println("Capturing...");
    
    // 画像キャプチャ（デモ用 - 実際のUnitV2実装に置き換え）
    // ここでは簡単なダミー実装
    uint8_t imageBuffer[1024];
    size_t imageSize = sizeof(imageBuffer);
    
    bool captureSuccess = captureImageFromUnitV2(imageBuffer, &imageSize);
    
    if (captureSuccess) {
      M5.Lcd.fillScreen(BLACK);
      M5.Lcd.setCursor(10, 100);
      M5.Lcd.println("Processing OCR...");
      
      // OCR実行
      lastOcrResult = performOCR(imageBuffer, imageSize);
      
      // 結果表示
      displayResult(lastOcrResult);
      
      Serial.println("--- OCR Result ---");
      Serial.println(lastOcrResult);
      Serial.println("------------------");
    } else {
      M5.Lcd.fillScreen(BLACK);
      M5.Lcd.setCursor(10, 100);
      M5.Lcd.setTextColor(RED);
      M5.Lcd.println("Capture Failed!");
      Serial.println("Image capture failed");
      delay(2000);
      displayMainScreen();
    }
  }
  
  // Bボタン: WiFi再接続
  if (M5.BtnB.wasPressed()) {
    Serial.println("\n--- WiFi Reconnect ---");
    M5.Lcd.fillScreen(BLACK);
    M5.Lcd.setCursor(0, 0);
    connectWiFi();
    delay(2000);
    displayMainScreen();
  }
  
  // Cボタン: システム情報表示
  if (M5.BtnC.wasPressed()) {
    Serial.println("\n--- System Info ---");
    M5.Lcd.fillScreen(BLACK);
    M5.Lcd.setCursor(0, 0);
    M5.Lcd.setTextSize(1);
    M5.Lcd.println("System Information:");
    M5.Lcd.println("==================");
    M5.Lcd.print("WiFi: ");
    M5.Lcd.println(wifiConnected ? "Connected" : "Disconnected");
    if (wifiConnected) {
      M5.Lcd.print("IP: ");
      M5.Lcd.println(WiFi.localIP());
      M5.Lcd.print("RSSI: ");
      M5.Lcd.print(WiFi.RSSI());
      M5.Lcd.println(" dBm");
    }
    M5.Lcd.print("Free Heap: ");
    M5.Lcd.print(ESP.getFreeHeap());
    M5.Lcd.println(" bytes");
    M5.Lcd.println("\nPress any button to return");
    
    // ボタン待機
    while (true) {
      M5.update();
      if (M5.BtnA.wasPressed() || M5.BtnB.wasPressed() || M5.BtnC.wasPressed()) {
        break;
      }
      delay(100);
    }
    displayMainScreen();
  }
  
  delay(100);
}
