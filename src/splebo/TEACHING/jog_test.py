import time
import splebo_n
import constant as const

def main():
    # 1. ロボット制御クラスの初期化
    robot = splebo_n.splebo_n_class()
    
    # 制御用インスタンスへの参照を取得
    mc = robot.motion_class
    
    print("初期化完了。ジョグ移動を開始します...")
    
    # --- 設定値 ---
    target_axis = splebo_n.axis_type_class.axis_X  # 動かす軸 (0:X, 1:Y, 2:Z)
    jog_speed = 1000  # 速度 (安全のため低速から試してください)
    direction_ccw = False  # False: プラス方向, True: マイナス方向
    
    try:
        # 2. ジョグ移動コマンドの送信（動き出します）
        # 引数: (軸番号, 反時計回りフラグ, 速度)
        # ※このコマンドは「移動開始」を指示するだけで、停止命令を送るまで動き続けます。
        splebo_n.set_order_motion_ctrl_class.axis = target_axis
        splebo_n.set_order_motion_ctrl_class.isCcw = direction_ccw
        splebo_n.set_order_motion_ctrl_class.dv = jog_speed
        
        # コマンドID 14 (kMoveJOG) を送信
        order_id = mc.set_write_command(splebo_n.motion_controller_cmd_class.kMoveJOG)
        mc.wait_write_order_motion_ctrl(order_id)
        
        if not splebo_n.order_motion_ctrl_class[order_id].isFuncSuccess:
            print("エラー: ジョグ移動の開始に失敗しました")
            return

        print(f"JOG開始: 軸{target_axis}, 速度{jog_speed}")
        
        # 3. 指定時間だけ動かす（ここでボタン長押しの代わり待機）
        time.sleep(1.0) 
        
        # 4. 停止コマンドの送信
        print("停止コマンド送信")
        splebo_n.set_order_motion_ctrl_class.axis = target_axis
        
        # コマンドID 15 (kStop) を送信
        order_id = mc.set_write_command(splebo_n.motion_controller_cmd_class.kStop)
        mc.wait_write_order_motion_ctrl(order_id)
        
        print("停止しました")

    except KeyboardInterrupt:
        # Ctrl+Cがおされた場合の緊急停止
        print("緊急停止！")
        splebo_n.set_order_motion_ctrl_class.axis = target_axis
        mc.set_write_command(splebo_n.motion_controller_cmd_class.kStop)
        
    finally:
        # 終了処理
        robot.close()

if __name__ == "__main__":
    main()