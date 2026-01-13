import asyncio
from src.robot import RobotManager, create_robot_manager

async def main():
    # ロボットマネージャーを作成
    # (simulation_mode=True なので実機がなくても動く想定)
    robot = create_robot_manager(simulation_mode=False)

    try:
        # 初期化
        print("Initializing...")
        await robot.initialize()

        # 原点復帰
        print("Homing...")
        await robot.home_all()

        # 軸移動
        print("Moving axis 0...")
        await robot.move_axis(0, 100.0, speed_percent=50)
        await robot.wait_motion_complete()

        # ティーチングポイントへ移動
        print("Moving to P001...")
        await robot.move_to_position("P001")

    except Exception as e:
        print(f"エラーが発生しました: {e}")

    finally:
        # エラーが起きても起きなくても必ずシャットダウンする
        print("Shutting down...")
        await robot.shutdown()

# エントリーポイント
if __name__ == "__main__":
    asyncio.run(main())