#!/usr/bin/env python3
"""
カメラ動作確認スクリプト
使い方: python3 tests/test_camera_check.py
"""
import sys
import cv2

def check_camera(device_id=0):
    """カメラの動作確認"""
    print(f"🎥 カメラ {device_id} を確認中...")
    
    try:
        cap = cv2.VideoCapture(device_id)
        
        if not cap.isOpened():
            print(f"❌ カメラ {device_id} が開けません")
            return False
        
        # カメラ情報を取得
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        print(f"✅ カメラ {device_id} が正常に動作しています")
        print(f"   解像度: {width}x{height}")
        print(f"   FPS: {fps}")
        
        # テストフレームをキャプチャ
        ret, frame = cap.read()
        if ret:
            print(f"   フレームサイズ: {frame.shape}")
            print("✅ フレームキャプチャ成功")
        else:
            print("⚠️ フレームキャプチャに失敗")
        
        cap.release()
        return True
        
    except Exception as e:
        print(f"❌ エラー: {e}")
        return False

def main():
    print("=" * 50)
    print("カメラ動作確認")
    print("=" * 50)
    
    # 利用可能なカメラを検出
    detected = []
    for i in range(3):  # 0-2までチェック
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            detected.append(i)
            cap.release()
    
    if not detected:
        print("❌ カメラが検出されませんでした")
        print("\n対処法:")
        print("  1. カメラが接続されているか確認")
        print("  2. 'ls /dev/video*' でデバイスを確認")
        print("  3. カメラのドライバが正しくインストールされているか確認")
        return False
    
    print(f"✅ 検出されたカメラ: {detected}")
    print()
    
    # 各カメラをテスト
    success = True
    for device_id in detected:
        if not check_camera(device_id):
            success = False
        print()
    
    if success:
        print("=" * 50)
        print("✅ すべてのカメラが正常です")
        print("=" * 50)
    else:
        print("=" * 50)
        print("⚠️ 一部のカメラに問題があります")
        print("=" * 50)
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
