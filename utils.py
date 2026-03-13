"""
M5UnitV2 OCR - WiFi設定とテストユーティリティ
OCR機能のテストと設定を行うためのユーティリティスクリプト
"""

import network
import time

# WiFi設定
WIFI_SSID = "your_wifi_ssid"      # WiFi SSID
WIFI_PASSWORD = "your_wifi_pass"   # WiFi パスワード

def connect_wifi(ssid=WIFI_SSID, password=WIFI_PASSWORD):
    """
    WiFiに接続
    Args:
        ssid: WiFi SSID
        password: WiFi パスワード
    Returns:
        bool: 接続成功した場合True
    """
    print("WiFiに接続中...")
    
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    
    if wlan.isconnected():
        print("既にWiFiに接続されています")
        print(f"IP: {wlan.ifconfig()[0]}")
        return True
    
    wlan.connect(ssid, password)
    
    # 接続を待つ（最大20秒）
    timeout = 20
    while not wlan.isconnected() and timeout > 0:
        print(".", end="")
        time.sleep(1)
        timeout -= 1
    
    if wlan.isconnected():
        print("\nWiFi接続成功!")
        print(f"IP: {wlan.ifconfig()[0]}")
        return True
    else:
        print("\nWiFi接続失敗")
        return False


def test_api_connection():
    """Google Cloud Vision APIへの接続テスト"""
    try:
        from config import GOOGLE_API_KEY
    except:
        print("config.pyが見つかりません")
        return False
    
    if not GOOGLE_API_KEY:
        print("APIキーが設定されていません")
        print("config.pyのGOOGLE_API_KEYを設定してください")
        return False
    
    print("API接続テスト中...")
    
    try:
        import urequests
        url = f"https://vision.googleapis.com/v1/images:annotate?key={GOOGLE_API_KEY}"
        
        # ダミーリクエスト（小さい1x1白画像）
        import base64
        # 1x1の白いPNG画像（最小のテスト画像）
        dummy_image = base64.b64encode(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde').decode()
        
        payload = {
            "requests": [{
                "image": {"content": dummy_image},
                "features": [{"type": "TEXT_DETECTION", "maxResults": 1}]
            }]
        }
        
        response = urequests.post(url, json=payload, timeout=10)
        
        if response.status_code == 200:
            print("✓ API接続成功！")
            response.close()
            return True
        else:
            print(f"✗ API エラー: {response.status_code}")
            print(response.text)
            response.close()
            return False
            
    except Exception as e:
        print(f"✗ 接続エラー: {e}")
        return False


def check_unitv2_connection():
    """UnitV2の接続を確認"""
    print("UnitV2接続チェック中...")
    
    try:
        from machine import UART
        
        # デフォルトピンでUART初期化
        uart = UART(2, baudrate=115200, tx=17, rx=16)
        
        # テストコマンドを送信
        uart.write(b'{"cmd":"status"}\n')
        time.sleep(0.5)
        
        if uart.any():
            response = uart.read()
            print(f"✓ UnitV2応答あり: {response}")
            return True
        else:
            print("✗ UnitV2からの応答なし")
            print("  - 配線を確認してください")
            print("  - UnitV2の電源を確認してください")
            return False
            
    except Exception as e:
        print(f"✗ UnitV2接続エラー: {e}")
        return False


def system_check():
    """システム全体のチェック"""
    print("\n" + "=" * 40)
    print("M5UnitV2 OCR システムチェック")
    print("=" * 40 + "\n")
    
    # 1. WiFi接続チェック
    print("1. WiFi接続チェック")
    wifi_ok = connect_wifi()
    print()
    
    # 2. API接続チェック
    if wifi_ok:
        print("2. Google Vision API接続チェック")
        api_ok = test_api_connection()
        print()
    else:
        print("2. Google Vision API接続チェック - スキップ（WiFi未接続）")
        api_ok = False
        print()
    
    # 3. UnitV2接続チェック
    print("3. UnitV2接続チェック")
    unitv2_ok = check_unitv2_connection()
    print()
    
    # 結果サマリー
    print("=" * 40)
    print("チェック結果:")
    print(f"  WiFi接続: {'✓ OK' if wifi_ok else '✗ NG'}")
    print(f"  API接続: {'✓ OK' if api_ok else '✗ NG'}")
    print(f"  UnitV2接続: {'✓ OK' if unitv2_ok else '✗ NG'}")
    print("=" * 40)
    
    if wifi_ok and api_ok and unitv2_ok:
        print("\n✓ すべてのチェックが完了しました！")
        print("  main.pyを実行してOCRを開始できます")
        return True
    else:
        print("\n✗ いくつかの問題があります")
        print("  上記のエラーメッセージを確認してください")
        return False


if __name__ == "__main__":
    system_check()
