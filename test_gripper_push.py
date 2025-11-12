#!/usr/bin/env python3
"""
グリッパー押付け動作デバッグスクリプト
"""
from src.gripper.controller import CONController

PORT = '/dev/ttyUSB0'
SLAVE_ID = 1
BAUD = 38400

controller = CONController(PORT, SLAVE_ID, BAUD)

try:
    print("=" * 60)
    print("現在のポジション1のデータを確認")
    print("=" * 60)
    controller.get_position_data(1)
    
    print("\n" + "=" * 60)
    print("押付け動作用のデータを設定")
    print("=" * 60)
    controller.set_position_data(
        position_number=1,
        position_mm=2.0,      # 目標位置 2.0mm
        width_mm=0.5,         # 押付け幅 0.5mm
        speed_mm_s=5.0,       # 速度 5mm/s
        push_current_percent=50,  # 押付け電流 50%
        push_direction=False  # プラス方向（閉じる方向）
    )
    
    print("\n" + "=" * 60)
    print("設定後のポジション1のデータを確認")
    print("=" * 60)
    data = controller.get_position_data(1)
    
    print("\n" + "=" * 60)
    print("データ解析")
    print("=" * 60)
    print(f"目標位置: {data['position_mm']} mm")
    print(f"押付け幅: {data['width_mm']} mm")
    print(f"押付け電流: {data['push_current_percent']} %")
    print(f"制御フラグ: {data['control_flag_hex']} (2進数: {int(data['control_flag_hex'], 16):04b})")
    
    ctl_flag_int = int(data['control_flag_hex'], 16)
    print("\nビット解析:")
    print(f"  ビット0: {(ctl_flag_int >> 0) & 1}")
    print(f"  ビット1 (押付け有効): {(ctl_flag_int >> 1) & 1}")
    print(f"  ビット2 (押付け方向): {(ctl_flag_int >> 2) & 1}  # 0=プラス方向, 1=マイナス方向")
    print(f"  ビット3: {(ctl_flag_int >> 3) & 1}")

finally:
    controller.close()
