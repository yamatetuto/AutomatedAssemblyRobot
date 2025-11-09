#!/usr/bin/env python3
"""
グリッパー動作確認スクリプト
使い方: python3 tests/test_gripper_check.py [ポート] [スレーブアドレス] [ボーレート]
例: python3 tests/test_gripper_check.py /dev/ttyUSB0 1 9600
"""
import sys
import os

# グリッパーコントローラーをインポート
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from gripper_controller.CONController import CONController
except ImportError:
    print("❌ CONController をインポートできません")
    print("gripper_controller/CONController.py が存在するか確認してください")
    sys.exit(1)

def check_gripper(port="/dev/ttyUSB0", slave_address=1, baudrate=9600):
    """グリッパーの動作確認"""
    print(f"🤖 グリッパー接続確認")
    print(f"   ポート: {port}")
    print(f"   スレーブアドレス: {slave_address}")
    print(f"   ボーレート: {baudrate}")
    print()
    
    try:
        # 接続テスト
        print("1. 接続テスト...")
        gripper = CONController(port, slave_address, baudrate)
        print("✅ 接続成功")
        print()
        
        # 現在の状態を取得
        print("2. 状態確認...")
        try:
            current_pos = gripper.instrument.read_register(
                gripper.REG_CURRENT_POS, 
                functioncode=3
            )
            print(f"   現在位置: {current_pos}")
        except Exception as e:
            print(f"⚠️ 位置読み取りエラー: {e}")
        
        try:
            alarm = gripper.instrument.read_register(
                gripper.REG_CURRENT_ALARM,
                functioncode=3
            )
            if alarm == 0:
                print(f"   アラーム: なし")
            else:
                print(f"⚠️ アラーム: {alarm}")
        except Exception as e:
            print(f"⚠️ アラーム読み取りエラー: {e}")
        
        try:
            status = gripper.instrument.read_register(
                gripper.REG_DEVICE_STATUS,
                functioncode=3
            )
            servo_on = (status >> gripper.BIT_SERVO_READY) & 1
            print(f"   サーボ状態: {'ON' if servo_on else 'OFF'}")
        except Exception as e:
            print(f"⚠️ ステータス読み取りエラー: {e}")
        
        print("✅ 状態確認完了")
        print()
        
        # クローズ
        gripper.close()
        print("✅ グリッパー動作確認完了")
        return True
        
    except Exception as e:
        print(f"❌ エラー: {e}")
        print("\n対処法:")
        print("  1. グリッパーが接続されているか確認")
        print(f"  2. 'ls {port}' でデバイスが存在するか確認")
        print("  3. USBケーブルの接続を確認")
        print("  4. ポート番号、スレーブアドレス、ボーレートが正しいか確認")
        print("  5. 'sudo usermod -a -G dialout $USER' でシリアルポートの権限を確認")
        return False

def main():
    print("=" * 50)
    print("グリッパー動作確認")
    print("=" * 50)
    print()
    
    # コマンドライン引数の処理
    port = sys.argv[1] if len(sys.argv) > 1 else "/dev/ttyUSB0"
    slave_address = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    baudrate = int(sys.argv[3]) if len(sys.argv) > 3 else 9600
    
    # シリアルポートの存在確認
    if not os.path.exists(port):
        print(f"❌ ポート {port} が見つかりません")
        print("\n利用可能なシリアルポート:")
        os.system("ls /dev/ttyUSB* /dev/ttyACM* 2>/dev/null || echo '  シリアルポートが見つかりません'")
        print()
        return False
    
    success = check_gripper(port, slave_address, baudrate)
    
    if success:
        print()
        print("=" * 50)
        print("✅ グリッパーが正常に動作しています")
        print("=" * 50)
    else:
        print()
        print("=" * 50)
        print("❌ グリッパーに問題があります")
        print("=" * 50)
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
