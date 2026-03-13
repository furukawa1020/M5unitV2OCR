"""
M5UnitV2 OCR シンプルバージョン
最小限のコードでOCRを実行するサンプル
"""

import M5
from M5 import *
import time
import urequests
import json
import base64

# Google Cloud Vision API Key（config.pyから読み込むことを推奨）
try:
    from config import GOOGLE_API_KEY
except:
    GOOGLE_API_KEY = ""  # ここに直接APIキーを入力

def capture_and_ocr():
    """画像をキャプチャしてOCRを実行"""
    print("画像をキャプチャ中...")
    
    # UnitV2から画像を取得（実装は環境による）
    # ここでは例として、画像データの取得方法を示します
    
    # 実際の実装では、UnitV2のSDカードから画像を読み込むか、
    # UART経由で画像データを受信します
    
    print("OCR実行中...")
    
    # ダミーの画像データ（実際には UnitV2 からの画像を使用）
    # image_data = get_image_from_unitv2()
    
    # OCR結果の表示
    print("OCR完了")
    

def ocr_from_file(image_path):
    """
    ファイルからOCRを実行
    Args:
        image_path: 画像ファイルのパス
    """
    if not GOOGLE_API_KEY:
        print("APIキーが設定されていません")
        return
    
    try:
        # 画像ファイルを読み込み
        with open(image_path, 'rb') as f:
            image_data = f.read()
        
        # Base64エンコード
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        # Google Cloud Vision API呼び出し
        url = f"https://vision.googleapis.com/v1/images:annotate?key={GOOGLE_API_KEY}"
        
        payload = {
            "requests": [{
                "image": {"content": image_base64},
                "features": [{"type": "TEXT_DETECTION"}]
            }]
        }
        
        print("APIにリクエスト送信中...")
        response = urequests.post(url, json=payload)
        
        if response.status_code == 200:
            result = response.json()
            
            # テキストを抽出
            if result['responses'][0].get('textAnnotations'):
                text = result['responses'][0]['textAnnotations'][0]['description']
                print("\n=== 認識されたテキスト ===")
                print(text)
                print("=" * 40)
                return text
            else:
                print("テキストが検出されませんでした")
        else:
            print(f"エラー: {response.status_code}")
            print(response.text)
        
        response.close()
        
    except Exception as e:
        print(f"エラー: {e}")


def main_simple():
    """シンプルなメイン関数"""
    print("M5UnitV2 OCR - シンプルバージョン")
    print("=" * 40)
    
    # M5Stack初期化
    try:
        M5.begin()
    except:
        pass
    
    # テスト実行
    # 画像ファイルがある場合
    # ocr_from_file('/sd/test_image.jpg')
    
    print("\nAボタンでOCR実行")
    
    while True:
        M5.update()
        
        if M5.BtnA.wasPressed():
            capture_and_ocr()
        
        time.sleep(0.1)


if __name__ == "__main__":
    main_simple()
