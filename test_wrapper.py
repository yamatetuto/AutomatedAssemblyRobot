#!/usr/bin/env python3
"""
SPLEBO Wrapper テストスクリプト

TEACHINGのラッパーを使用して軸移動とホーミングをテストします。
"""
import sys
import os
import time
import logging

# ログ設定
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# パス追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def main():
    print("="*70)
    print(" SPLEBO Wrapper テスト")
    print("="*70)
    
    # ラッパーをインポート
    print("\n[STEP 1] ラッパーをインポート...")
    try:
        from splebo import SpleboController, AxisConfig, AxisStatus
        print("   [OK] インポート成功")
    except Exception as e:
        print(f"   [FAIL] インポート失敗: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # コントローラ作成
    print("\n[STEP 2] コントローラ作成...")
    controller = SpleboController(
        sys_file_path="/home/splebopi/SPLEBO/TEACHING/SPLEBO-N.sys"
    )
    print("   [OK] コントローラ作成完了")
    
    # 初期化
    print("\n[STEP 3] コントローラ初期化...")
    try:
        result = controller.initialize()
        if result:
            print("   [OK] 初期化成功")
        else:
            print("   [FAIL] 初期化失敗")
            return
    except Exception as e:
        print(f"   [FAIL] 初期化エラー: {e}")
        import traceback
        traceback.print_exc()
        return
    
    try:
        # 軸設定確認
        print("\n[STEP 4] 軸設定確認...")
        for axis in range(min(3, controller.axis_count)):
            cfg = controller.get_axis_config(axis)
            print(f"   軸{axis}: MotorType={cfg.motor_type.name}, OriginSensor={cfg.origin_sensor.name}")
        
        # 現在位置確認
        print("\n[STEP 5] 現在位置確認...")
        for axis in range(min(3, controller.axis_count)):
            sts = controller.get_axis_status(axis)
            print(f"   軸{axis}: 座標={sts.abs_coord:.3f}mm, busy={sts.is_busy}")
        
        # 移動テスト
        print("\n[STEP 6] 軸0を10mm移動...")
        print("   *** 警告: モーターが動作します！ ***")
        
        try:
            input("   Enterキーで移動開始（Ctrl+Cでキャンセル）...")
        except KeyboardInterrupt:
            print("\n   キャンセルされました")
            return
        
        print("   移動中...")
        result = controller.move_relative(0, 10.0, speed_percent=50.0, wait=True)
        
        if result:
            print("   [OK] 移動完了")
        else:
            print("   [FAIL] 移動失敗")
        
        # 移動後の位置確認
        sts = controller.get_axis_status(0)
        print(f"   移動後の座標: {sts.abs_coord:.3f}mm")
        
        # ホーミングテスト
        print("\n[STEP 7] 軸0のホーミング...")
        print("   *** 警告: モーターが原点に戻ります！ ***")
        
        try:
            input("   Enterキーでホーミング開始（Ctrl+Cでキャンセル）...")
        except KeyboardInterrupt:
            print("\n   キャンセルされました")
            return
        
        print("   ホーミング中...")
        result = controller.home_axis(0, wait=True)
        
        if result:
            print("   [OK] ホーミング完了")
        else:
            print("   [FAIL] ホーミング失敗")
        
        # ホーミング後の位置確認
        sts = controller.get_axis_status(0)
        print(f"   ホーミング後の座標: {sts.abs_coord:.3f}mm")
        
        # 結果サマリー
        print("\n" + "="*70)
        print(" テスト完了")
        print("="*70)
        
    except KeyboardInterrupt:
        print("\n   中断されました")
    except Exception as e:
        print(f"\n   [ERROR] エラー発生: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # シャットダウン
        print("\n[CLEANUP] シャットダウン...")
        controller.shutdown()
        print("   [OK] 完了")


if __name__ == "__main__":
    main()
