#!/usr/bin/env python3
"""
ホーミングテストスクリプト

詳細なログを出力してホーミング処理のデバッグを行う
SPLEBO-N.sysから設定を読み込む
"""
import asyncio
import logging
import sys

# ログ設定
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

async def main():
    from src.robot.motion_controller import (
        MotionController, MotorType, AxisConfig, 
        initialize_pigpio, cleanup_pigpio,
        load_axis_configs_from_sys_file
    )
    
    print("="*60)
    print(" ホーミングテスト (SPLEBO-N.sys設定使用)")
    print("="*60)
    
    # SPLEBO-N.sysから設定を読み込む
    print("\n1. SPLEBO-N.sysから設定読み込み...")
    sys_file_path = "/home/splebopi/SPLEBO/TEACHING/SPLEBO-N.sys"
    try:
        axis_configs = load_axis_configs_from_sys_file(sys_file_path)
        print(f"   [OK] {len(axis_configs)} 軸の設定を読み込み")
        for axis, config in axis_configs.items():
            motor_type_name = config.motor_type.name if config.motor_type else "NONE"
            print(f"   軸{axis}: MotorType={motor_type_name}, OriginSensor={config.origin_sensor}, OriginDir={config.origin_dir}")
    except Exception as e:
        print(f"   [FAIL] 設定読み込み失敗: {e}")
        return
    
    # pigpioを初期化
    print("\n2. pigpio初期化...")
    if not initialize_pigpio():
        print("   [FAIL] pigpio初期化失敗")
        print("   sudo権限で実行してください: sudo python test_homing.py")
        return
    print("   [OK] pigpio初期化成功")
    
    # モーションコントローラを作成（シミュレーションなし）
    print("\n3. モーションコントローラ作成...")
    controller = MotionController(
        axis_count=4,
        simulation_mode=False
    )
    
    # SPLEBO-N.sysから読み込んだ設定を適用
    for axis, config in axis_configs.items():
        if axis < 4:  # axis_count=4
            controller.set_axis_config(axis, config)
    
    print("   [OK] モーションコントローラ作成完了")
    
    # 初期化
    print("\n4. モーションコントローラ初期化...")
    try:
        result = await controller.initialize()
        if result:
            print("   [OK] 初期化成功")
            print(f"   状態: {controller.state}")
        else:
            print("   [FAIL] 初期化失敗")
            return
    except Exception as e:
        print(f"   [FAIL] 初期化中にエラー: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # レジスタ読み取りテスト
    print("\n5. レジスタ読み取りテスト...")
    for axis in range(3):
        try:
            reg = await asyncio.to_thread(
                controller._native_lib.read_register, axis, 3)  # RR3
            if reg is not None:
                print(f"   軸{axis} RR3: 0x{reg:08X}")
            else:
                print(f"   軸{axis} RR3: 読み取り失敗")
        except Exception as e:
            print(f"   軸{axis} RR3: エラー - {e}")
    
    # ホーミングテスト（軸0のみ）
    print("\n6. 軸0のホーミングテスト...")
    
    # origin_sensorの値を確認
    axis0_config = axis_configs.get(0)
    if axis0_config and axis0_config.origin_sensor == 0:
        print("   *** OriginSensor=0 (OFF) なので、物理的なホーミングは行われません ***")
        print("   *** 座標が0にリセットされるだけです ***")
    elif axis0_config and axis0_config.origin_sensor == 2:
        print("   *** OriginSensor=2 (AUTO) なので、物理的なホーミングが行われます ***")
        print("   注意: モーターが動作します！安全を確認してください。")
    
    try:
        input("   Enterキーを押すとホーミングを開始します...")
    except KeyboardInterrupt:
        print("\n   キャンセルされました")
        await controller.shutdown()
        cleanup_pigpio()
        return
    
    print("   ホーミング開始...")
    try:
        result = await controller.home_axis(0)
        if result:
            print("   [OK] ホーミング成功")
        else:
            print("   [FAIL] ホーミング失敗")
    except Exception as e:
        print(f"   [FAIL] ホーミング中にエラー: {e}")
        import traceback
        traceback.print_exc()
    
    # 現在位置確認
    print("\n7. 現在位置確認...")
    for axis in range(3):
        status = controller.get_axis_status(axis)
        if status:
            print(f"   軸{axis}: {status.abs_coord}mm, busy={status.is_busy}, servo={status.is_servo_on}")
    
    # シャットダウン
    print("\n8. シャットダウン...")
    await controller.shutdown()
    cleanup_pigpio()
    print("   [OK] 完了")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n中断されました")
