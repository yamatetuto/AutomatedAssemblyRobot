import minimalmodbus
import time
import pdb  # デバッグ用

class CONController:
    """
    IAI社製ポジショナーコントローラをModbus RTUで操作するためのクラス。
    """
    # --- Modbusレジスタアドレス---
    POS_TABLE_START = 0x1000   # ポジションテーブル開始アドレス
    REG_CONTROL = 0x0D00       # デバイス制御レジスタ1 (DRG1)
    REG_POS_SELECT = 0x0D03    # ポジション番号指定レジスタ (POSR)
    REG_CURRENT_POS = 0x9000   # 現在位置レジスタ (PNOW)
    REG_CURRENT_ALARM = 0x9002 # 現在発生アラームコードレジスタ (ALMC)
    REG_DEVICE_STATUS = 0x9005 # デバイスステータスレジスタ1 (DSS1)
    REG_EXT_STATUS = 0x9007    # 拡張デバイスステータスレジスタ (DSSE)
    REG_CURRENT_VALUE = 0x900C # 電流値モニターレジスタ (CNOW) 
    REG_LOAD_CELL = 0x901E     # 現在荷重データモニタ (FBFC)

    # --- 制御値 (ビットマスク) ---
    VAL_SERVO_ON = 0x1000      # ビット12: サーボON
    VAL_HOME     = 0x1010      # ビット12: サーボON + ビット4: 原点復帰
    VAL_START    = 0x1008      # ビット12: サーボON + ビット3: 位置決め起動

    # --- ステータスビット位置 ---
    # REG_DEVICE_STATUSのビット位置
    BIT_SERVO_READY = 12       # SV (サーボ ON ステータス)
    BIT_PUSH_MISS = 11         # PSFL (押付け空振りステータス)
    BIT_HOME_END = 4           # HEND (原点復帰完了ステータス)
    BIT_POS_END = 3            # PEND (位置決め完了ステータス)
    # REG_EXT_STATUSのビット位置
    BIT_MOVE = 5               # MOVE (移動中信号)

    def _calculate_timeout(self, baudrate, response_bytes, is_write=False):
        """
        Modbus RTU半二重通信のタイムアウト値を計算
        
        仕様:
        Tout = To + α + (10 × Bprt / Kbr) [ms]
        
        Args:
            baudrate: 通信速度 [bps]
            response_bytes: レスポンスメッセージのバイト数
            is_write: 書き込み処理の場合True（内部処理時間が異なる）
        
        Returns:
            タイムアウト値 [秒]
        """
        # To: 内部処理時間 × 安全率3
        if is_write:
            To = 18 * 3  # 書き込み: 最大18ms × 安全率3
        else:
            To = 4 * 3   # 読み出し: 最大4ms × 安全率3
        
        # α: 従局トランスミッター活性化最小遅延時間（パラメータNo.17, 初期値5ms）
        alpha = 5
        
        # Kbr: 通信速度 [kbps]
        Kbr = baudrate / 1000
        
        # Bprt: レスポンスメッセージのバイト数 + 8
        Bprt = response_bytes + 8
        
        # タイムアウト計算 [ms]
        Tout_ms = To + alpha + (10 * Bprt / Kbr)
        
        # 秒に変換して返す（最小0.1秒、余裕を持って+0.1秒）
        return max(0.1, (Tout_ms / 1000) + 0.1)

    def __init__(self, port, slave_address, baudrate):
        """コントローラの初期化と接続を行う。"""
        try:
            self.instrument = minimalmodbus.Instrument(port, slave_address)
            self.instrument.serial.baudrate = baudrate
            
            # Modbus RTU半二重通信のタイムアウト計算
            # 読み出し用の標準的なレスポンス（レジスタ1個: 7バイト程度）
            read_timeout = self._calculate_timeout(baudrate, response_bytes=7, is_write=False)
            self.instrument.serial.timeout = read_timeout
            
            # ボーレートとタイムアウトを保存（後で書き込み時に使用）
            self.baudrate = baudrate
            self.read_timeout = read_timeout
            self.write_timeout = self._calculate_timeout(baudrate, response_bytes=8, is_write=True)
            
            self.instrument.mode = minimalmodbus.MODE_RTU
            self.instrument.clear_buffers_before_each_transaction = True
            # self.instrument.debug = True # 詳細なログが必要な場合はコメントを外す
            print(f"コントローラ接続成功 (Port: {port})")
        except Exception as e:
            print(f"[Error] 接続エラー: {e}")
            raise

    def close(self):
        """シリアルポートを安全にクローズ。"""
        if self.instrument and self.instrument.serial.is_open:
            self.instrument.serial.close()
            print("ポートをクローズしました。")

    def check_status_bit(self, register, bit_position):
        """指定したレジスタの特定ビットが1か0かを確認。"""
        status = self.instrument.read_register(register, functioncode=3)
        # print(bin(status)) # デバッグ用: 現在の拡張ステータスを表示
        return (status >> bit_position) & 1

    def wait_for_motion_to_stop(self, timeout=10):
        """移動中(MOVE)信号がOFFになるのを待つ。"""
        start_time = time.time()
        print("   ... (移動中信号が 0 になるのを待機中)")
        while True:
            if self.check_status_bit(self.REG_EXT_STATUS, self.BIT_MOVE) == 0:
                print("   移動停止を確認。")
                return True
            if time.time() - start_time > timeout:
                print("   [Error] タイムアウトエラー: 移動が完了しませんでした。")
                return False

    def wait_for_status_bit(self, register, bit_position, expected_state=1, timeout=15):
        """status bitの確認。"""
        start_time = time.time()
        # pdb.set_trace()  # デバッグ用ブレークポイント
        print(f"   ... (ビット {bit_position} が {expected_state} になるのを待機中)")
        while True:
            if self.check_status_bit(register, bit_position) == expected_state:
                print(f"   ステータス確認完了 (ビット {bit_position} が {expected_state} になりました)")
                return True
            if time.time() - start_time > timeout:
                print(f"   [Error] タイムアウトエラー: ビット {bit_position} が {expected_state} になりませんでした。")
                return False

    def servo_on(self, timeout=10):
        """サーボをONにし、安定するまで待つ。"""
        print("\n1. サーボをオンにします...")
        self.instrument.write_register(self.REG_CONTROL, self.VAL_SERVO_ON, functioncode=6)
        
        if self.wait_for_status_bit(self.REG_DEVICE_STATUS, self.BIT_SERVO_READY):
            print("   サーボONを確認。")
        else:
            raise RuntimeError("[Error] サーボONに失敗しました。")

    def servo_off(self):
        """サーボをOFF。"""
        print("\n5. サーボをオフにします...")
        self.instrument.write_register(self.REG_CONTROL, 0, functioncode=6)
        print("   サーボOFF完了。")

    def home(self, timeout=20):
        """原点復帰を実行し、物理的に完了するまで待つ。"""
        print("\n2. 原点復帰を開始します...")
        self.instrument.write_register(self.REG_CONTROL, self.VAL_SERVO_ON, functioncode=6)
        self.instrument.write_register(self.REG_CONTROL, self.VAL_HOME, functioncode=6)

        if not self.wait_for_motion_to_stop(timeout):
            raise RuntimeError("[Error] 原点復帰がタイムアウトしました。")
        self.instrument.write_register(self.REG_CONTROL, self.VAL_SERVO_ON, functioncode=6)
        # 念のためHENDビットも確認
        if self.wait_for_status_bit(self.REG_DEVICE_STATUS, self.BIT_HOME_END):
            print("   HEND信号を確認。原点復帰正常完了。")
        else:
            raise RuntimeError("[Error] 移動は停止しましたが、HEND信号がONになりませんでした。")
        
    def set_position_data(self, position_number:int, position_mm=None, width_mm=0.1, speed_mm_s=78.0, accel_g=0.30, decel_g=0.30, push_current_percent=0, is_closing_push=True):
        """
        指定したポジション番号のテーブルデータを書き換える。(資料 p.227)
        """
        def validate_range(val, minv, maxv, label):
            if val is None or not (minv <= val <= maxv):
                raise ValueError(f"[{label}]は {minv} から {maxv} の範囲で指定してください。")
        
        # push_current_percentが0以外なら押し付け移動
        is_push_move = (push_current_percent != 0)
        validate_range(position_number, 0, 63, "ポジションNo.")
        validate_range(position_mm, 0.0, 4.0, "目標位置")
        if is_push_move:
            validate_range(width_mm, 0.0, 4.0, "押付け幅")
            if (is_closing_push and position_mm + width_mm > 4.0) or (not is_closing_push and position_mm - width_mm < 0.0):
                raise ValueError("押し付け移動では[目標位置]と[位置決め幅]合わせて 0.0 から 4.0 mm の範囲内になるようwidth_mm を指定してください。")
            validate_range(push_current_percent, 20, 70, "押付け")
            validate_range(speed_mm_s, 2.0, 5.0, "速度")
        else:
            validate_range(width_mm, 0.0, 0.5, "位置決め幅")
            validate_range(speed_mm_s, 5.0, 78.0, "速度")
            is_closing_push = True

        validate_range(accel_g, 0.01, 0.3, "加速度")
        validate_range(decel_g, 0.01, 0.3, "減速度")

        print(f"\n【データ書込】ポジションNo.{position_number} のデータを書き込みます...")
        try:
            base_addr = self.POS_TABLE_START + (16 * position_number)
            # 各値を変換して書き込み
            self.instrument.write_long(base_addr + 0, int(position_mm * 100), signed=True)
            self.instrument.write_long(base_addr + 2, int(width_mm * 100), signed=False)
            self.instrument.write_long(base_addr + 4, int(speed_mm_s * 100), signed=False)
            self.instrument.write_register(base_addr + 10, int(accel_g * 100))
            self.instrument.write_register(base_addr + 11, int(decel_g * 100))
            # 押付け電流
            push_val = int(255 * push_current_percent / 100) if is_push_move else 0
            self.instrument.write_register(base_addr + 12, push_val)
            # # 制御フラグ
            # ctl_flag = 0b0000
            # if is_push_move:
            #     ctl_flag = 0b0010 if not is_closing_push else 0b0110
            # self.instrument.write_register(base_addr + 14, ctl_flag)
            # 1. 現在のCTLFレジスタの値を読み出す (オフセット+14)
            current_ctlf = self.instrument.read_register(base_addr + 14, functioncode=3)
            new_ctlf = current_ctlf
            # 2. 変更したいビットだけを操作する
            if is_push_move:
                # PUSHビット(ビット1)をONにする
                new_ctlf = new_ctlf | 0b0010
                # is_closing_pushがTrueならグリッパ閉じる
                if is_closing_push:
                    # DIRビット(ビット2)もONにする
                    new_ctlf = new_ctlf | 0b0100
                else:
                    # DIRビット(ビット2)をOFFにする
                    new_ctlf = new_ctlf & ~0b0100
            else:
                # PUSHとDIRビットをOFFにする
                new_ctlf = new_ctlf & ~0b0110

            # 3. 変更後の値を書き戻す
            self.instrument.write_register(base_addr + 14, new_ctlf)
            
            # 変数 ctl_flag を new_ctlf に変更
            ctl_flag = new_ctlf

            # 設定値を辞書でまとめて表示
            pos_data = {
                'position_mm': position_mm,
                'width_mm': width_mm,
                'speed_mm_s': speed_mm_s,
                'accel_g': accel_g,
                'decel_g': decel_g,
                'push_current_percent': push_current_percent,
                'control_flag_hex': f"{ctl_flag:04X}"
            }
            print("   書き込み値:")
            for key, value in pos_data.items():
                print(f"     - {key:<22}: {value}")

            print("   書き込み完了。")
            return True
        except Exception as e:
            print(f"   [Error] ポジションデータの書き込みに失敗しました: {e}")
            return False


    def move_to_pos(self, position_number, timeout=15):
        """指定したポジション番号へ移動し、物理的に完了するまで待つ。"""
        print(f"\n3. ポジションテーブル No.{position_number} へ移動します...")
        self.instrument.write_register(self.REG_POS_SELECT, position_number, functioncode=6)
        print(f"   移動先 ({position_number}) を設定しました。")
        self.instrument.write_register(self.REG_CONTROL, self.VAL_SERVO_ON, functioncode=6)
        self.instrument.write_register(self.REG_CONTROL, self.VAL_START, functioncode=6)

        if not self.wait_for_motion_to_stop(timeout):
             raise RuntimeError("[Error] 位置決め移動がタイムアウトしました。")

    def get_position_data(self, position_number):
        """
        指定したポジション番号のテーブルデータを全て読み出す。(資料 p.98)
        返値: ポジションデータを格納した辞書(dict)
        """
        print(f"\n【情報照会】ポジションテーブル No.{position_number} のデータを読み出します...")
        try:
            base_addr = self.POS_TABLE_START + (16 * position_number)
            
            # 各データを仕様に合わせて読み出し
            # 計算式：1000H ＋（16 × ポジションNo.）H ＋ アドレス（オフセット値）H
            # 目標位置
            pcmd = self.instrument.read_long(base_addr + 0, functioncode=3, signed=True) / 100.0
            # 位置決め幅
            inp = self.instrument.read_long(base_addr + 2, functioncode=3, signed=False) / 100.0
            # 速度指令
            vcmd = self.instrument.read_long(base_addr + 4, functioncode=3, signed=False) / 100.0
            # 加速度指令
            acmd = self.instrument.read_register(base_addr + 10, functioncode=3) / 100.0
            # 減速度指令
            dcmd = self.instrument.read_register(base_addr + 11, functioncode=3) / 100.0
            # 押付け時電流制限値
            ppow = self.instrument.read_register(base_addr + 12, functioncode=3)
            # 制御フラグ指定
            ctlf = self.instrument.read_register(base_addr + 14, functioncode=3)

            pos_data = {
                'position_mm': pcmd,
                'width_mm': inp,
                'speed_mm_s': vcmd,
                'accel_g': acmd,
                'decel_g': dcmd,
                'push_current_percent': round(ppow * 100 / 255), # %に変換
                'control_flag_hex': f"{ctlf:04X}"
            }
            print("   読み出し成功！")
            for key, value in pos_data.items():
                print(f"     - {key:<22}: {value}")
            return pos_data
        except Exception as e:
            print(f"   [Error] ポジションデータの読み出しに失敗しました: {e}")
            return None

    def get_current_position(self):
        """現在位置をmm単位で取得。"""
        print("\n4. 現在位置を読み出します...")
        pos_raw = self.instrument.read_long(self.REG_CURRENT_POS, functioncode=3, signed=True)
        pos_mm = pos_raw / 100.0
        print(f"   読み出し成功！ 現在位置: {pos_mm:.2f} mm")
        return pos_mm

    def get_current_mA(self):
        """モーターの現在電流値をmA単位で取得。(資料 p.135)"""
        print("\n4c. 現在のモーター電流値を読み出します...")
        try:
            current_raw = self.instrument.read_long(self.REG_CURRENT_VALUE, functioncode=3, signed=False)
            print(f"   読み出し成功！ 現在電流値: {current_raw} mA")
            return current_raw
        except Exception as e:
            print(f"   [Error] 電流値の読み出しに失敗しました: {e}")
            return None

    def get_current_alarm(self):
        """現在発生中のアラームコードを取得。"""
        print("\n4b. 現在発生中のアラームを確認します...")
        alarm_code = self.instrument.read_register(self.REG_CURRENT_ALARM, functioncode=3)
        if alarm_code == 0:
            print("   アラームはありません。正常です。")
        else:
            print(f"   アラーム発生！ コード: {alarm_code} ({alarm_code:04X}H)")
        return alarm_code
    
    def get_push_detect(self):
        """押付け空振り状態を確認。"""
        print("\n4d. 押付け空振り状態を確認します...")
        if self.check_status_bit(self.REG_DEVICE_STATUS, self.BIT_PUSH_MISS):
            print("   押付け空振り状態: 発生中 (PSFL=1)")
            return True
        else:
            print("   押付け空振り状態: 発生していません (PSFL=0)")
            return False

    # PCON-CBP, SCON-CA/CBなど、ロードセル対応機種専用の機能
    def get_load_N(self):
        """
        現在の力荷重をニュートン(N)単位で取得。
        ※PCON-CBP, SCON-CA/CBなど、ロードセル対応機種専用の機能。
        """
        print("\n6. 現在の力荷重を測定します...")
        try:
            # 32bitの符号付き整数で読み取る
            load_raw = self.instrument.read_long(self.REG_LOAD_CELL, functioncode=3, signed=True)
            print(load_raw)
            # 単位(0.01N)をNに変換
            load_newton = load_raw / 100.0
            print(f"   読み出し成功！ 現在荷重: {load_newton:.2f} N")
            return load_newton
        except Exception as e:
            print(f"   [Error] 荷重の読み出しに失敗しました: {e}")
            return None


# --- メイン実行部 ---
if __name__ == "__main__":
    # 接続設定
    PORT = '/dev/ttyUSB0'
    SLAVE_ID = 1
    BAUD = 38400
    
    controller = None # finallyブロックで使うため先に定義
    try:
        # コントローラインスタンスを作成
        controller = CONController(PORT, SLAVE_ID, BAUD)
        controller.get_current_alarm()
        
        # ポジションテーブルの内容を確認
        controller.get_position_data(0)
        controller.get_position_data(1)
        # controller.get_position_data(2)
        # controller.get_position_data(3)


        # 一連の動作を実行
        controller.servo_on()
        controller.home()
        # controller.get_current_mA()

        # controller.move_to_pos(1)
        # controller.get_current_alarm()
        # controller.get_current_position()
        # controller.get_push_detect()
        controller.set_position_data(position_number=1, position_mm=3.0, width_mm=0.9, speed_mm_s=5.0, push_current_percent=50)
        controller.get_position_data(1)
        controller.move_to_pos(1)
        controller.get_current_position()

        # controller.get_current_mA()
        # controller.get_load_N()

        # 状態の読み出し
        # controller.get_current_alarm()

        # controller.home()
        # controller.get_current_mA()


    except Exception as e:
        print(f"\n[Error] メイン処理でエラーが発生しました: {e}")
        # エラー発生時にアラームコードを読み出す試み
        if controller:
            controller.get_current_alarm()

    finally:
        # 正常終了時もエラー終了時も、必ずサーボオフとポートクローズを行う
        if controller:
            controller.servo_off()
            controller.close()