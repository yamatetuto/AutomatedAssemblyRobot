import asyncio
from src.robot.robot_manager import RobotManager, create_robot_manager

async def main():
    # ロボットマネージャーを作成
    # (simulation_mode=True なので実機がなくても動く想定)
    robot = create_robot_manager(simulation_mode=False)

    try:
        # 初期化
        print("Initializing...")
        success = await robot.initialize()
        if not success:
            print("初期化に失敗しました")
            return
        
        print("初期化完了！")
        
        # ステータス確認
        status = robot.get_status()
        print(f"ロボット状態: {status}")
        
        # 現在座標を取得
        for axis in range(3):
            pos = robot.motion.get_axis_status(axis)
            if pos:
                print(f"軸{axis}現在位置: {pos.abs_coord}")
            else:
                print(f"軸{axis}現在位置: 取得失敗")
        
        # 原点復帰（コメントアウト - 実行時に有効化）
        print("Homing...")
        await robot.home_all()

        # 軸移動（コメントアウト - 実行時に有効化）
        print("Moving axis 0...")
        await robot.move_axis(0, 100.0, speed_percent=50)
        await robot.wait_motion_complete()

        # # ティーチングポイントへ移動（コメントアウト - ポジションファイルが必要）
        # print("Moving to P001...")
        # await robot.move_to_position("P001")

    except Exception as e:
        print(f"エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # エラーが起きても起きなくても必ずシャットダウンする
        print("Shutting down...")
        await robot.shutdown()
        print("完了")

# エントリーポイント
if __name__ == "__main__":
    asyncio.run(main())