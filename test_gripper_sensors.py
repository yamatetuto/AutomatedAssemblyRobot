#!/usr/bin/env python3
"""
グリッパーセンサー値テストスクリプト

電流値、荷重データ、押付け空振りフラグを読み取り、
単位とスケールを特定します。
"""
import minimalmodbus
import time
import sys

def main():
    print("=" * 60)
    print("グリッパーセンサー値テストスクリプト")
    print("=" * 60)
    print()
    
    # Modbus接続
    print("グリッパーに接続中...")
    try:
        instrument = minimalmodbus.Instrument('/dev/ttyUSB0', 1, mode='rtu')
        instrument.serial.baudrate = 38400
        instrument.serial.timeout = 2.0
        print("✅ 接続成功: /dev/ttyUSB0")
    except Exception as e:
        print(f"❌ 接続失敗: {e}")
        sys.exit(1)
    
    print()
    print("各レジスタから値を読み取ります...")
    print("-" * 60)
    print(f"{'時刻':<12} {'電流値':<12} {'荷重':<12} {'PSFL':<8} {'PEND':<8} {'MOVE':<8}")
    print("-" * 60)
    
    try:
        while True:
            try:
                # 電流値 (0x900C = 36876)
                current = instrument.read_register(0x900C, signed=True)
                
                # 荷重データ (0x901E = 36894)
                load = instrument.read_register(0x901E, signed=True)
                
                # デバイスステータス1 (0x9005)
                status_dss1 = instrument.read_register(0x9005)
                psfl = (status_dss1 >> 11) & 0x1  # ビット11: 押付け空振りフラグ
                pend = (status_dss1 >> 3) & 0x1   # ビット3: 位置決め完了
                
                # 拡張ステータス (0x9007)
                status_dsse = instrument.read_register(0x9007)
                move = (status_dsse >> 5) & 0x1   # ビット5: 移動中信号
                
                # 時刻
                timestamp = time.strftime("%H:%M:%S")
                
                # 表示
                print(f"{timestamp:<12} {current:<12} {load:<12} {psfl:<8} {pend:<8} {move:<8}")
                
            except Exception as e:
                print(f"読み取りエラー: {e}")
            
            time.sleep(0.1)  # 100ms間隔
            
    except KeyboardInterrupt:
        print()
        print()
        print("=" * 60)
        print("テスト終了")
        print("=" * 60)
        print()
        print("【テスト手順】")
        print("1. グリッパーを開いた状態で数秒待つ → 電流値・荷重の基準値を記録")
        print("2. 何も掴まずに閉じる（空振り） → PSFLフラグを確認")
        print("3. 軽い物体を掴む → 電流値・荷重の変化を記録")
        print("4. 重い物体を掴む → 電流値・荷重の変化を記録")
        print()
        print("これらのデータから適切な閾値を決定します。")

if __name__ == "__main__":
    main()
