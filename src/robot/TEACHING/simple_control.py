# piggioのエラー出たら以下コマンド入力
# sudo killall pigpiod || true
# sudo rm -f /var/run/pigpio.pid

# -*- coding: utf-8 -*-
import time
import splebo_n
# constant.py は軸の定義などで使用します
import constant as const

# --- 設定 ---
# 移動に使用する軸 (1:X, 2:Y, 3:XY, 4:Z, 5:XZ, 6:YZ, 7:XYZ全軸)
# ※ 通常はXYZ全軸(7)を指定します
AXIS_XYZ = 7 

# 移動速度 (%)
SPEED_PERCENT = 5

def main():
    print("=== SPLEBO-N コンソール制御モード ===")
    
    # 1. ライブラリの初期化
    # splebo_nクラスのインスタンス化 (通信確立・GPIO初期化)
    splebo = splebo_n.splebo_n_class()

    try:
        # 2. 原点復帰 (必須)
        # 電源投入後、位置情報を確定させるために必ず行います
        print("\n[INFO] 原点復帰を開始します...")
        print("       (ロボットが動きます。周囲の安全を確認してください)")
        
        # 原点復帰実行 (完了するまで待機します)
        splebo.motion_home()
        print("[INFO] 原点復帰完了")

        # 3. 動作テストループ
        while True:
            print("\n------------------------------------------------")
            print("コマンドを入力してください:")
            print(" [Enterキー]: ポイント1へ移動して戻る動作を実行")
            print(" [q] + Enter: 終了")
            
            user_input = input(">> ")

            if user_input.lower() == 'q':
                splebo.motion_home()
                break

            # --- 移動動作シーケンス ---
            print("[ACTION] ポイント No.1 へ移動中...")
            # motion_movePoint(軸ビット, ポイント番号, 速度%)
            splebo.motion_movePoint(AXIS_XYZ, 1, SPEED_PERCENT)
            
            # 到着を確認するために少し待機 (または作業時間)
            input(">> ")

            print("[ACTION] ポイント No.2 へ移動中...")
            # motion_movePoint(軸ビット, ポイント番号, 速度%)
            splebo.motion_movePoint(AXIS_XYZ, 2, SPEED_PERCENT)

            input(">> ")

            print("[ACTION] ディスペンサー吐出")
            splebo.canio_output(1, 0, True)
            time.sleep(0.1)
            splebo.canio_output(1, 0, False)

            print("[INFO] 動作サイクル完了")

    except KeyboardInterrupt:
        print("\n[INFO] ユーザーによる中断")
    
    except Exception as e:
        print(f"\n[ERROR] エラーが発生しました: {e}")

    finally:
        # 4. 終了処理
        print("[INFO] システムを終了します")
        splebo.close()

if __name__ == '__main__':
    main()