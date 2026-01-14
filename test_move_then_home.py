#!/usr/bin/env python3
"""
軸移動→ホーミングテストスクリプト

1. 軸を移動させる
2. ホーミングを実行
3. 座標が0になることを確認

SPLEBO-N.sys設定:
- OriginSensor=0 (OFF): 物理的なホーミングなし、座標リセットのみ
- OriginSensor=2 (AUTO): 物理的なオートホーミング
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
        load_axis_configs_from_sys_file,
        ControllerState
    )
    
    print("="*70)
    print(" 軸移動→ホーミングテスト")
    print("="*70)
    
    # ===== STEP 1: SPLEBO-N.sysから設定を読み込む =====
    print("\n[STEP 1] SPLEBO-N.sysから設定読み込み...")
    sys_file_path = "/home/splebopi/SPLEBO/TEACHING/SPLEBO-N.sys"
    try:
        axis_configs = load_axis_configs_from_sys_file(sys_file_path)
        print(f"   [OK] {len(axis_configs)} 軸の設定を読み込み")
        for axis, config in axis_configs.items():
            if axis < 3:  # 軸0-2のみ表示
                motor_type_name = config.motor_type.name if config.motor_type else "NONE"
                origin_sensor_str = {0: "OFF", 1: "ON", 2: "AUTO"}.get(config.origin_sensor, "?")
                print(f"   軸{axis}: MotorType={motor_type_name}, OriginSensor={config.origin_sensor}({origin_sensor_str})")
    except Exception as e:
        print(f"   [FAIL] 設定読み込み失敗: {e}")
        return
    
    # OriginSensor=0の場合の警告
    print("\n   [INFO] 設定変更:")
    print("   - motor_dir=1（方向反転）でテストします")
    print("   - origin_sensor=2（AUTO）で物理的ホーミングを有効化します")
    
    # ===== STEP 2: pigpio初期化 =====
    print("\n[STEP 2] pigpio初期化...")
    if not initialize_pigpio():
        print("   [FAIL] pigpio初期化失敗")
        print("   sudo権限で実行してください: sudo python test_move_then_home.py")
        return
    print("   [OK] pigpio初期化成功")
    
    controller = None
    try:
        # ===== STEP 3: モーションコントローラ作成 =====
        print("\n[STEP 3] モーションコントローラ作成...")
        controller = MotionController(
            axis_count=4,
            simulation_mode=False
        )
        
        # 設定を適用（motor_dir、origin_sensor、origin_dirを上書き）
        for axis, config in axis_configs.items():
            if axis < 4:
                # motor_dir=1 で方向反転（実機が反対に動く問題の修正）
                config.motor_dir = 1
                # origin_sensor=2 (AUTO) で物理的ホーミングを有効化
                config.origin_sensor = 2
                # origin_dir=1 (CCW) でホーミング方向を反転
                config.origin_dir = 1
                controller.set_axis_config(axis, config)
        
        print("   [OK] モーションコントローラ作成完了")
        print("   設定変更: motor_dir=1, origin_sensor=2, origin_dir=1(CCW)")
        
        # ===== STEP 4: 初期化 =====
        print("\n[STEP 4] モーションコントローラ初期化...")
        result = await controller.initialize()
        if result:
            print(f"   [OK] 初期化成功 (状態: {controller.state})")
        else:
            print("   [FAIL] 初期化失敗")
            return
        
        # ===== STEP 5: 現在位置確認 =====
        print("\n[STEP 5] 現在位置確認...")
        for axis in range(3):
            await controller._update_axis_status(axis)
            status = controller.get_axis_status(axis)
            if status:
                print(f"   軸{axis}: 座標={status.abs_coord:.3f}mm")
        
        # ===== STEP 6: 軸移動（相対移動） =====
        print("\n[STEP 6] 軸0を10mm移動...")
        print("   *** 警告: モーターが動作します！ ***")
        
        try:
            input("   Enterキーで移動開始（Ctrl+Cでキャンセル）...")
        except KeyboardInterrupt:
            print("\n   キャンセルされました")
            return
        
        # 相対移動 +10mm
        target_axis = 0
        move_distance = 10.0  # mm
        
        print(f"   軸{target_axis}を{move_distance}mm移動中...")
        move_result = await controller.move_relative(target_axis, move_distance)
        
        if move_result:
            # 移動完了を待つ（Busyがfalseになるまで）
            timeout = 30.0
            start_time = asyncio.get_event_loop().time()
            while (asyncio.get_event_loop().time() - start_time) < timeout:
                await controller._update_axis_status(target_axis)
                status = controller.get_axis_status(target_axis)
                if status and not status.is_busy:
                    break
                await asyncio.sleep(0.1)
            else:
                print("   [WARNING] 移動タイムアウト")
            
            # 移動完了後、状態をREADYに戻す
            controller._state = ControllerState.READY
        
        if move_result:
            print(f"   [OK] 移動完了")
        else:
            print(f"   [FAIL] 移動失敗")
            # 失敗しても続行
        
        # 移動後の位置確認
        await controller._update_axis_status(target_axis)
        status = controller.get_axis_status(target_axis)
        if status:
            print(f"   移動後の座標: {status.abs_coord:.3f}mm")
        
        # ===== STEP 7: ホーミング =====
        print("\n[STEP 7] 軸0のホーミング...")
        print("   *** origin_sensor=2 (AUTO) に設定済み ***")
        print("   *** 物理的なオートホーミングが実行されます ***")
        print("   *** 警告: モーターが原点方向に動作します！ ***")
        
        try:
            input("   Enterキーでホーミング開始（Ctrl+Cでキャンセル）...")
        except KeyboardInterrupt:
            print("\n   キャンセルされました")
            return
        
        print("   ホーミング実行中...")
        home_result = await controller.home_axis(target_axis)
        
        if home_result:
            print(f"   [OK] ホーミング完了")
        else:
            print(f"   [FAIL] ホーミング失敗")
        
        # ===== STEP 8: ホーミング後の位置確認 =====
        print("\n[STEP 8] ホーミング後の位置確認...")
        await controller._update_axis_status(target_axis)
        status = controller.get_axis_status(target_axis)
        if status:
            print(f"   軸{target_axis}: 座標={status.abs_coord:.3f}mm")
            
            if abs(status.abs_coord) < 0.001:
                print("   [OK] 座標が0にリセットされました")
            else:
                print("   [WARNING] 座標が0ではありません")
        
        # ===== STEP 9: 結果サマリー =====
        print("\n" + "="*70)
        print(" テスト結果サマリー")
        print("="*70)
        print(f"   移動テスト: {'成功' if move_result else '失敗'}")
        print(f"   ホーミング: {'成功' if home_result else '失敗'}")
        
        print("\n   [設定]")
        print("   - motor_dir=1（方向反転）")
        print("   - origin_sensor=2（AUTO - 物理的ホーミング）")
        
    except Exception as e:
        print(f"\n   [ERROR] エラー発生: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # ===== クリーンアップ =====
        print("\n[CLEANUP] シャットダウン...")
        if controller:
            await controller.shutdown()
        cleanup_pigpio()
        print("   [OK] 完了")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n中断されました")
