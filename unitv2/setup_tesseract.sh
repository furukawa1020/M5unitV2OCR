#!/bin/sh
# UnitV2 Tesseract OCR セットアップスクリプト
# Tina Linux (OpenWRT ベース) 向け

echo "================================================"
echo "  UnitV2 Tesseract OCR セットアップ"
echo "================================================"

# ストレージ確認
echo "[INFO] ストレージ空き容量:"
df -h /

# opkg で Tesseract を試す
echo "[INFO] opkg で Tesseract を検索..."
opkg update 2>/dev/null
if opkg list | grep -q "tesseract"; then
    echo "[ OK ] tesseract が見つかりました - インストール中..."
    opkg install tesseract-ocr 2>&1
    opkg install tesseract-ocr-tessdata-jpn 2>&1 || true
    opkg install tesseract-ocr-tessdata-eng 2>&1 || true
else
    echo "[WARN] opkg に tesseract がありません"
    echo "[INFO] pip3 で pytesseract を試みます..."
    pip3 install pytesseract 2>&1 | tail -3

    # tesseract バイナリを探す
    if command -v tesseract >/dev/null 2>&1; then
        echo "[ OK ] tesseract コマンド発見"
    else
        echo "[ERR] tesseract バイナリが見つかりません"
        echo ""
        echo "  UnitV2 の容量制限のため、以下の代替案を検討:"
        echo "  1. SDカードを挿して /mnt/sdcard/ に展開"
        echo "  2. UnitV2 を STA モードに変更してネット接続後インストール"
        echo "  3. main.py の OCR_ENGINE = 'opencv' に変更（簡易版）"
        echo ""
        echo "  英語のみなら圧縮済みバイナリ（~5MB）でも動作可能:"
        echo "  -> setup_tesseract_eng_only.sh を実行してください"
        exit 1
    fi
fi

# インストール確認
echo ""
echo "[INFO] Tesseract バージョン確認:"
tesseract --version 2>&1 | head -3

echo ""
echo "[INFO] 利用可能な言語:"
tesseract --list-langs 2>&1

echo ""
echo "[ OK ] セットアップ完了！"
echo "       python3 /root/main.py で OCR を開始できます"