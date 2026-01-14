import curses
import time
import splebo_n
import constant as const

# --- 設定 ---
SPEED_MM_S = 10.0      # 移動速度
# ------------------------------
# ★リミット設定
SOFT_LIMIT_MIN = 10.0   # 全軸共通: 0.5mm以下禁止
SOFT_LIMIT_MAX = [800.5-10, 250.5-10, 100.0-10] # [X, Y, Z] 上限
# ------------------------------
# ★チューニング (安全のため少し余裕を持つ)
KEY_TIMEOUT_MS = 50    # キー待ち時間
STOP_DELAY_SEC = 0.1   # この時間入力がなければ停止 (通信遅延を考慮して少し長めに)
# ------------------------------

def get_pps(axis, speed_mm_s):
    pulse_len = splebo_n.axis_set_class[axis].pulse_length
    if pulse_len == 0: return 100
    return int(speed_mm_s / pulse_len)

def stop_all_axes(mc):
    """全軸に停止命令を送る（緊急用）"""
    for i in range(3):
        splebo_n.set_order_motion_ctrl_class.axis = i
        mc.set_write_command(splebo_n.motion_controller_cmd_class.kStop)
    time.sleep(0.05)

def main(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.timeout(KEY_TIMEOUT_MS)

    stdscr.addstr(0, 0, "Connecting...")
    stdscr.refresh()
    
    robot = splebo_n.splebo_n_class()
    mc = robot.motion_class
    robot.motion_home()
    
    stdscr.clear()
    stdscr.addstr(0, 0, "=== HIGH SPEED RESPONSE JOG ===")
    stdscr.addstr(1, 0, "[Arrow Keys]: X/Y Axis")
    stdscr.addstr(2, 0, "[U / D]: Z Axis")
    stdscr.addstr(3, 0, "[SPACE]: EMERGENCY STOP (ALL AXIS)")
    stdscr.addstr(4, 0, "[Q]: Quit")
    
    # 座標キャッシュ（表示用）
    cached_pos = [0.0, 0.0, 0.0]
    # 初回だけ全軸取得
    for i in range(3):
        cached_pos[i] = robot.motion_getposition(i)

    current_axis = -1
    is_moving = False
    last_key_time = time.time()
    moving_direction_ccw = False

    try:
        while True:
            # ★ 1. 入力バッファの完全消去 (ラグの元を断つ)
            curses.flushinp()

            # ★ 2. 座標取得の最適化 (ここが最重要)
            # 移動中なら「その軸だけ」更新する。停止中は更新しない(または稀に更新)。
            # これにより通信待ち時間を大幅に減らし、ループを高速回転させる。
            if is_moving and current_axis != -1:
                # 動いている軸だけ最新座標を取る
                cur_pos = robot.motion_getposition(current_axis)
                cached_pos[current_axis] = cur_pos
                
                # --- リミット監視 ---
                limit_hit = False
                if moving_direction_ccw and cur_pos <= SOFT_LIMIT_MIN:
                    limit_hit = True
                elif not moving_direction_ccw and cur_pos >= SOFT_LIMIT_MAX[current_axis]:
                    limit_hit = True
                
                if limit_hit:
                    # 強制停止
                    splebo_n.set_order_motion_ctrl_class.axis = current_axis
                    mc.set_write_command(splebo_n.motion_controller_cmd_class.kStop)
                    is_moving = False
                    current_axis = -1
                    stdscr.addstr(9, 0, "!!! LIMIT STOP !!!           ", curses.A_BOLD)
                    continue

            # 画面表示 (キャッシュを表示)
            stdscr.addstr(6, 0, f"X: {cached_pos[0]:8.2f} / {SOFT_LIMIT_MAX[0]}")
            stdscr.addstr(7, 0, f"Y: {cached_pos[1]:8.2f} / {SOFT_LIMIT_MAX[1]}")
            stdscr.addstr(8, 0, f"Z: {cached_pos[2]:8.2f} / {SOFT_LIMIT_MAX[2]}")
            if not is_moving:
                stdscr.move(9, 0); stdscr.clrtoeol()
            stdscr.refresh()

            # ★ 3. キー入力 (待ち時間あり)
            key = stdscr.getch()
            current_time = time.time()

            # --- 緊急停止 (スペースキー) ---
            if key == ord(' '):
                stop_all_axes(mc)
                is_moving = False
                current_axis = -1
                stdscr.addstr(9, 0, "!!! EMERGENCY STOP !!!       ", curses.A_BOLD | curses.A_REVERSE)
                continue

            # --- 停止判定 (キー離し) ---
            # キー入力がない(-1) 状態が続いたら止める
            if key == -1:
                if is_moving and (current_time - last_key_time > STOP_DELAY_SEC):
                    splebo_n.set_order_motion_ctrl_class.axis = current_axis
                    mc.set_write_command(splebo_n.motion_controller_cmd_class.kStop)
                    is_moving = False
                    current_axis = -1
                continue

            # キー入力があったので時刻更新
            last_key_time = current_time
            
            if key == ord('q') or key == ord('Q'): 
                break

            # --- 移動方向判定 ---
            target_axis = -1
            direction_ccw = False 
            
            if key == curses.KEY_RIGHT: target_axis = 0; direction_ccw = False
            elif key == curses.KEY_LEFT: target_axis = 0; direction_ccw = True
            elif key == curses.KEY_UP: target_axis = 1; direction_ccw = False
            elif key == curses.KEY_DOWN: target_axis = 1; direction_ccw = True
            elif key == ord('u') or key == ord('U'): target_axis = 2; direction_ccw = False
            elif key == ord('d') or key == ord('D'): target_axis = 2; direction_ccw = True

            # --- 移動実行 ---
            if target_axis != -1:
                # 軸が変わる、または停止状態からの開始
                if not is_moving or current_axis != target_axis:
                    
                    # リミットチェック (発進前)
                    target_val = cached_pos[target_axis]
                    if direction_ccw and target_val <= SOFT_LIMIT_MIN:
                        continue
                    if not direction_ccw and target_val >= SOFT_LIMIT_MAX[target_axis]:
                        continue

                    # 軸変更時は念のため停止
                    if is_moving:
                        splebo_n.set_order_motion_ctrl_class.axis = current_axis
                        mc.set_write_command(splebo_n.motion_controller_cmd_class.kStop)
                        time.sleep(0.01)

                    pps = get_pps(target_axis, SPEED_MM_S)
                    
                    splebo_n.set_order_motion_ctrl_class.axis = target_axis
                    splebo_n.set_order_motion_ctrl_class.isCcw = direction_ccw
                    splebo_n.set_order_motion_ctrl_class.dv = pps
                    
                    order_id = mc.set_write_command(splebo_n.motion_controller_cmd_class.kMoveJOG)
                    mc.wait_write_order_motion_ctrl(order_id)
                    
                    is_moving = True
                    current_axis = target_axis
                    moving_direction_ccw = direction_ccw

    except KeyboardInterrupt:
        stop_all_axes(mc)
    finally:
        stop_all_axes(mc)
        robot.close()

if __name__ == "__main__":
    curses.wrapper(main)