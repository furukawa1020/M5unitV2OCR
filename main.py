"""
M5Stack UnitV2 OCR文字認識
M5UnitV2を使用してOCR（文字認識）を実行するサンプルコード
"""

import M5
from M5 import *
from hardware import *
import time
import urequests
import json
import base64

# 設定
UART_TX = 17  # UnitV2 TX接続ピン
UART_RX = 16  # UnitV2 RX接続ピン
BAUDRATE = 115200

# Google Cloud Vision APIの設定（オプション）
# config.pyファイルに記載することを推奨
GOOGLE_API_KEY = ""  # ここにGoogle Cloud Vision APIキーを入力

class UnitV2OCR:
    """M5Stack UnitV2でOCR機能を実装するクラス"""
    
    def __init__(self, tx_pin=UART_TX, rx_pin=UART_RX, baudrate=BAUDRATE):
        """
        初期化
        Args:
            tx_pin: UART TXピン
            rx_pin: UART RXピン
            baudrate: 通信速度
        """
        self.uart = None
        self.tx_pin = tx_pin
        self.rx_pin = rx_pin
        self.baudrate = baudrate
        self.init_uart()
        
    def init_uart(self):
        """UART通信の初期化"""
        try:
            from machine import UART
            self.uart = UART(2, baudrate=self.baudrate, tx=self.tx_pin, rx=self.rx_pin)
            print("UnitV2 UART初期化完了")
        except Exception as e:
            print(f"UART初期化エラー: {e}")
    
    def capture_image(self):
        """
        UnitV2で画像をキャプチャ
        Returns:
            bytes: キャプチャした画像データ
        """
        if not self.uart:
            print("UARTが初期化されていません")
            return None
        
        try:
            # UnitV2に画像キャプチャコマンドを送信
            command = b'{"cmd":"capture"}\n'
            self.uart.write(command)
            
            # レスポンスを待つ
            time.sleep(0.5)
            
            if self.uart.any():
                response = self.uart.read()
                return response
            else:
                print("UnitV2からの応答がありません")
                return None
                
        except Exception as e:
            print(f"画像キャプチャエラー: {e}")
            return None
    
    def ocr_with_google_vision(self, image_data):
        """
        Google Cloud Vision APIを使用してOCRを実行
        Args:
            image_data: 画像データ（bytes）
        Returns:
            str: 認識されたテキスト
        """
        if not GOOGLE_API_KEY:
            print("Google API Keyが設定されていません")
            return None
        
        try:
            # 画像をBase64エンコード
            if isinstance(image_data, bytes):
                image_base64 = base64.b64encode(image_data).decode('utf-8')
            else:
                print("無効な画像データ形式")
                return None
            
            # Google Cloud Vision APIにリクエスト
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
            response = urequests.post(url, data=json.dumps(payload), headers=headers)
            
            if response.status_code == 200:
                result = response.json()
                response.close()
                
                # テキストを抽出
                if 'responses' in result and len(result['responses']) > 0:
                    text_annotations = result['responses'][0].get('textAnnotations', [])
                    if text_annotations:
                        detected_text = text_annotations[0]['description']
                        return detected_text
                    else:
                        print("テキストが検出されませんでした")
                        return ""
            else:
                print(f"API リクエストエラー: {response.status_code}")
                response.close()
                return None
                
        except Exception as e:
            print(f"OCRエラー: {e}")
            return None
    
    def display_result(self, text):
        """
        認識結果を表示
        Args:
            text: 認識されたテキスト
        """
        if text:
            print("=" * 40)
            print("認識されたテキスト:")
            print(text)
            print("=" * 40)
            
            # M5Stackのディスプレイに表示（オプション）
            try:
                M5.Lcd.clear()
                M5.Lcd.setCursor(0, 0)
                M5.Lcd.print("OCR Result:")
                M5.Lcd.setCursor(0, 30)
                # テキストが長い場合は切り詰める
                display_text = text[:100] if len(text) > 100 else text
                M5.Lcd.print(display_text)
            except:
                pass
        else:
            print("テキストが認識されませんでした")


def main():
    """メイン関数"""
    # M5Stackの初期化
    try:
        M5.begin()
        print("M5Stack 初期化完了")
    except:
        print("M5Stack初期化をスキップ（デバッグモード）")
    
    # UnitV2 OCRの初期化
    ocr = UnitV2OCR()
    
    print("M5UnitV2 OCR 文字認識システム")
    print("Aボタン: 画像キャプチャ&OCR実行")
    print("=" * 40)
    
    # メインループ
    while True:
        try:
            # Aボタンが押されたら画像をキャプチャしてOCRを実行
            M5.update()
            
            if M5.BtnA.wasPressed():
                print("\n画像をキャプチャ中...")
                
                # 画像をキャプチャ
                image_data = ocr.capture_image()
                
                if image_data:
                    print("OCR処理中...")
                    
                    # Google Cloud Vision APIでOCRを実行
                    detected_text = ocr.ocr_with_google_vision(image_data)
                    
                    # 結果を表示
                    ocr.display_result(detected_text)
                else:
                    print("画像のキャプチャに失敗しました")
            
            time.sleep(0.1)
            
        except KeyboardInterrupt:
            print("\nプログラムを終了します")
            break
        except Exception as e:
            print(f"エラー: {e}")
            time.sleep(1)


if __name__ == "__main__":
    main()
