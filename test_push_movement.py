#!/usr/bin/env python3
"""
押付け動作の詳細デバッグ
実際にグリッパーを動かして動作を確認
"""
from src.gripper.controller import CONController
import time

PORT = '/dev/ttyUSB0'
SLAVE_ID = 1
BAUD = 38400

controller = CONController(PORT, SLAVE_ID, BAUD)

try:
    print("=" * 70)
    print("押付け動作デバッグ - グリッパーを実際に動かして確認")
    print("=" * 70)
    
    # サーボON
    print("\n1. サーボON...")
    controller.servo_on()
    time.sleep(1)
    
    # 原点復帰
    print("\n2. 原点復帰...")
    controller.home()
    time.sleep(2)
    
    current_pos = controller.get_current_position()
    print(f"\n原点復帰後の位置: {current_pos} mm")
    
    # ポジション0: 通常の位置決め（押付けなし）
    print("\n" + "=" * 70)
    print("テスト1: 通常の位置決め（押付けなし）")
    print("=" * 70)
    controller.set_position_data(
        position_number=0,
        position_mm=1.5,
        width_mm=0.1,
        speed_mm_s=50.0,
        push_current_percent=0  # 押付けなし
    )
    
    print("\nポジション0に移動...")
    controller.move_to_pos(0)
    time.sleep(2)
    
    pos_after_normal = controller.get_current_position()
    print(f"移動後の位置: {pos_after_normal} mm")
    print(f"期待位置: 1.5 mm")
    print(f"差分: {abs(pos_after_normal - 1.5):.3f} mm")
    
    # ポジション1: 押付け動作（プラス方向 = 閉じる方向）
    print("\n" + "=" * 70)
    print("テスト2: 押付け動作（プラス方向=閉じる方向）")
    print("=" * 70)
    controller.set_position_data(
        position_number=1,
        position_mm=2.0,        # 目標位置 2.0mm
        width_mm=0.3,           # 押付け幅 0.3mm
        speed_mm_s=5.0,         # 低速
        push_current_percent=40,  # 押付け電流 40%
        push_direction=False    # プラス方向（閉じる）
    )
    
    data = controller.get_position_data(1)
    ctl_flag = int(data['control_flag_hex'], 16)
    print(f"\n設定確認:")
    print(f"  目標位置: {data['position_mm']} mm")
    print(f"  押付け幅: {data['width_mm']} mm")
    print(f"  制御フラグ: {data['control_flag_hex']} (2進数: {ctl_flag:04b})")
    print(f"  ビット1 (押付け有効): {(ctl_flag >> 1) & 1}")
    print(f"  ビット2 (押付け方向): {(ctl_flag >> 2) & 1}  # 0=プラス, 1=マイナス")
    
    print("\n原点復帰...")
    controller.home()
    time.sleep(2)
    
    pos_before = controller.get_current_position()
    print(f"移動前の位置: {pos_before} mm")
    
    print("\nポジション1に移動（押付け動作）...")
    controller.move_to_pos(1)
    time.sleep(3)
    
    pos_after_push = controller.get_current_position()
    current_val = controller.get_current_mA()
    psfl = controller.get_push_detect()
    
    print(f"\n押付け動作後:")
    print(f"  現在位置: {pos_after_push} mm")
    print(f"  電流値: {current_val} mA")
    print(f"  空振りフラグ: {psfl}")
    print(f"\n解析:")
    print(f"  目標位置: 2.0 mm")
    print(f"  押付け幅: 0.3 mm")
    print(f"  期待最終位置: 2.3 mm（目標 + 押付け幅）")
    print(f"  実際の位置: {pos_after_push} mm")
    print(f"  差分: {pos_after_push - 2.0:.3f} mm")
    
    if pos_after_push > 2.0:
        print("\n✅ プラス方向（閉じる方向）に動作しました")
    elif pos_after_push < 2.0:
        print("\n❌ マイナス方向（開く方向）に動作しました - バグ確認")
    else:
        print("\n⚠️ 移動していません")
    
finally:
    print("\n原点復帰してサーボOFF...")
    try:
        controller.home()
    except:
        pass
    controller.servo_off()
    controller.close()
    print("テスト完了")
