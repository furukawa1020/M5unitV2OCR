"""
M5Stack UnitV2 OCR - UnitV2直接実行版
UnitV2本体で動作するOCRプログラム

必要環境:
- UnitV2 (ファームウェア v1.4.0以降)
- WiFi接続
- Google Cloud Vision API Key

アップロード方法:
1. WiFi設定を行う
2. adb connect <UnitV2_IP>:5555
3. adb push unitv2/main.py /root/
4. adb shell python3 /root/main.py
"""

from maix import camera, display, image, nn
import time
import json
import requests
import base64

# 設定
GOOGLE_API_KEY = ""  # Google Cloud Vision APIキー
WIFI_SSID = ""  # WiFi SSID
WIFI_PASSWORD = ""  # WiFiパスワード

# 画面サイズ
SCREEN_WIDTH = 240
SCREEN_HEIGHT = 135

# カメラ解像度
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480

class UnitV2_OCR:
    """UnitV2でOCR機能を実装するクラス"""
    
    def __init__(self):
        """初期化"""
        print("=================================")
        print("UnitV2 OCR System")
        print("=================================")
        
        # カメラ初期化
        try:
            self.cam = camera.Camera(CAMERA_WIDTH, CAMERA_HEIGHT)
            print("Camera: OK")
        except Exception as e:
            print(f"Camera Error: {e}")
            self.cam = None
        
        # ディスプレイ初期化
        try:
            self.disp = display.Display()
            print("Display: OK")
        except Exception as e:
            print(f"Display Error: {e}")
            self.disp = None
        
        # WiFi接続
        self.wifi_connected = False
        if WIFI_SSID and WIFI_PASSWORD:
            self.connect_wifi()
        else:
            print("WiFi: Not configured")
        
        self.last_ocr_result = ""
        
    def connect_wifi(self):
        """WiFiに接続"""
        try:
            from maix import network
            print(f"WiFi connecting to {WIFI_SSID}...")
            
            network.wifi.connect(WIFI_SSID, WIFI_PASSWORD)
            time.sleep(3)
            
            # 接続確認
            if network.wifi.is_connected():
                ip_info = network.wifi.ifconfig()
                print(f"WiFi Connected!")
                print(f"IP: {ip_info}")
                self.wifi_connected = True
            else:
                print("WiFi connection failed")
                self.wifi_connected = False
                
        except Exception as e:
            print(f"WiFi Error: {e}")
            self.wifi_connected = False
    
    def capture_image(self):
        """画像をキャプチャ"""
        if not self.cam:
            print("Camera not available")
            return None
        
        try:
            img = self.cam.read()
            return img
        except Exception as e:
            print(f"Capture Error: {e}")
            return None
    
    def ocr_with_google_vision(self, img):
        """
        Google Cloud Vision APIでOCRを実行
        
        Args:
            img: 画像データ (maix.image)
            
        Returns:
            str: 認識されたテキスト
        """
        if not self.wifi_connected:
            return "Error: WiFi not connected"
        
        if not GOOGLE_API_KEY:
            return "Error: API key not set"
        
        try:
            print("Converting image...")
            
            # 画像をJPEGに変換
            img_bytes = img.to_jpeg(quality=80)
            
            # Base64エンコード
            print("Encoding to Base64...")
            image_base64 = base64.b64encode(img_bytes).decode('utf-8')
            
            # APIリクエスト
            print("Sending OCR request...")
            url = f"https://vision.googleapis.com/v1/images:annotate?key={GOOGLE_API_KEY}"
            
            payload = {
                "requests": [{
                    "image": {
                        "content": image_base64
                    },
                    "features": [{
                        "type": "TEXT_DETECTION",
                        "maxResults": 10
                    }]
                }]
            }
            
            headers = {'Content-Type': 'application/json'}
            
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            
            if response.status_code == 200:
                result = response.json()
                
                # テキストを抽出
                if 'responses' in result and len(result['responses']) > 0:
                    text_annotations = result['responses'][0].get('textAnnotations', [])
                    if text_annotations:
                        detected_text = text_annotations[0]['description']
                        print(f"OCR Success! Detected {len(detected_text)} characters")
                        return detected_text
                    else:
                        print("No text detected")
                        return "No text detected"
                else:
                    print("Empty response")
                    return "Error: Empty response"
            else:
                print(f"API Error: {response.status_code}")
                return f"API Error: {response.status_code}"
                
        except Exception as e:
            print(f"OCR Error: {e}")
            return f"Error: {str(e)}"
    
    def display_text(self, text, color=(255, 255, 255)):
        """
        ディスプレイにテキストを表示
        
        Args:
            text: 表示するテキスト
            color: テキスト色 (R, G, B)
        """
        if not self.disp:
            return
        
        try:
            # 画像を作成
            img = image.Image(size=(SCREEN_WIDTH, SCREEN_HEIGHT))
            
            # 背景を黒で塗りつぶし
            img.draw_rectangle(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, color=(0, 0, 0), thickness=-1)
            
            # テキストを表示（簡易版）
            lines = text.split('\n')
            y = 10
            for line in lines[:8]:  # 最大8行
                if len(line) > 30:
                    line = line[:30] + "..."
                img.draw_string(5, y, line, color=color, scale=1)
                y += 15
                if y > SCREEN_HEIGHT - 15:
                    break
            
            self.disp.show(img)
            
        except Exception as e:
            print(f"Display Error: {e}")
    
    def display_camera_preview(self):
        """カメラプレビューを表示"""
        if not self.cam or not self.disp:
            return
        
        try:
            img = self.cam.read()
            # 画面サイズにリサイズ
            img_resized = img.resize(SCREEN_WIDTH, SCREEN_HEIGHT)
            self.disp.show(img_resized)
        except Exception as e:
            print(f"Preview Error: {e}")
    
    def run_ocr(self):
        """OCRを実行"""
        print("\n--- OCR Start ---")
        
        # "Capturing..." メッセージを表示
        self.display_text("Capturing...", color=(255, 255, 0))
        
        # 画像をキャプチャ
        img = self.capture_image()
        
        if img is None:
            print("Capture failed")
            self.display_text("Capture Failed!", color=(255, 0, 0))
            time.sleep(2)
            return
        
        # "Processing..." メッセージを表示
        self.display_text("Processing OCR...", color=(255, 255, 0))
        
        # OCR実行
        result = self.ocr_with_google_vision(img)
        
        # 結果を保存
        self.last_ocr_result = result
        
        # 結果を表示
        print("=== OCR Result ===")
        print(result)
        print("==================")
        
        self.display_text(f"Result:\n{result}", color=(0, 255, 0))
        
        return result


def main():
    """メイン関数"""
    
    # UnitV2 OCR初期化
    ocr = UnitV2_OCR()
    
    print("\nSystem Ready!")
    print("\nInstructions:")
    print("- ボタンを押してOCRを実行")
    print("- カメラプレビューが表示されます")
    print("\n")
    
    # メインループ
    frame_count = 0
    last_process_time = time.time()
    
    try:
        while True:
            # カメラプレビューを表示
            if frame_count % 5 == 0:  # 5フレームごとに更新
                ocr.display_camera_preview()
            
            # ボタン入力チェック（UnitV2のボタンがある場合）
            # 簡易版: 10秒ごとに自動実行（テスト用）
            current_time = time.time()
            if current_time - last_process_time > 10:
                # OCR実行
                ocr.run_ocr()
                last_process_time = current_time
                time.sleep(3)  # 結果表示時間
            
            frame_count += 1
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\nProgram stopped by user")
    except Exception as e:
        print(f"Error in main loop: {e}")
    finally:
        print("Exiting...")


if __name__ == "__main__":
    # 設定チェック
    if not GOOGLE_API_KEY:
        print("Warning: GOOGLE_API_KEY not set!")
        print("Please edit this file and set your API key")
        print("Or use config file")
        
        try:
            from config_unitv2 import GOOGLE_API_KEY, WIFI_SSID, WIFI_PASSWORD
        except ImportError:
            pass
    
    main()
