"""
SPLEBO-N ロボット定数定義モジュール

TEACHINGシステムから移植した定数・Enum定義。

参照元ファイル:
    - TEACHING/constant.py: Bit, Led7Seg, InputPort, OutputPort
    - TEACHING/splebo_n.py: NOVA_Class, gpio_class, axis_type_class

移植時の変更点:
    - クラス定数 → IntEnum に変換（型安全性向上）
    - 命名規則を PEP8 準拠に変更
    - 日本語コメント追加
"""
from enum import Enum, IntEnum
from typing import List


class Bit:
    """ビット操作用マスク定数"""
    BitOn0 = 0x01
    BitOn1 = 0x02
    BitOn2 = 0x04
    BitOn3 = 0x08
    BitOn4 = 0x10
    BitOn5 = 0x20
    BitOn6 = 0x40
    BitOn7 = 0x80
    BitOff0 = 0xFE
    BitOff1 = 0xFD
    BitOff2 = 0xFB
    BitOff3 = 0xF7
    BitOff4 = 0xEF
    BitOff5 = 0xDF
    BitOff6 = 0xBF
    BitOff7 = 0x7F
    BitOff012 = 0xF8
    BitOff2345 = 0xC3


class DEFSwStat:
    """スイッチステータス定数"""
    LEFTSW = 21
    RIGHTSW = 22
    StartSw1ON = 0x20
    StartSw2ON = 0x40
    StartSw1Sw2ON = 0x60


class Led7Seg:
    """7セグメントLED表示パターン"""
    # 数字
    LED_0 = 0x3F
    LED_1 = 0x06
    LED_2 = 0x5B
    LED_3 = 0x4F
    LED_4 = 0x66
    LED_5 = 0x6D
    LED_6 = 0x7D
    LED_7 = 0x07
    LED_8 = 0x7F
    LED_9 = 0x6F
    
    # アルファベット
    LED_A = 0x77
    LED_B = 0x7C
    LED_C = 0x58
    LED_D = 0x5E
    LED_E = 0x79
    LED_F = 0x71
    LED_G = 0x3D
    LED_H = 0x76
    LED_I = 0x04
    LED_J = 0x1E
    LED_K = 0x3A
    LED_L = 0x38
    LED_M = 0x55
    LED_N = 0x54
    LED_O = 0x5C
    LED_P = 0x73
    LED_Q = 0x67
    LED_R = 0x50
    LED_S = 0x2D
    LED_T = 0x78
    LED_U = 0x3E
    LED_V = 0x1C
    LED_W = 0x1D
    LED_X = 0x36
    LED_Y = 0x6E
    LED_Z = 0x1B
    
    # 記号
    LED_Minus = 0x40
    LED_Off = 0x00
    LED_Equals = 0x48
    LED_Underline = 0x08
    
    # 定義済みメッセージ
    SEG_ORG: List[int] = [LED_O, LED_R, LED_G]      # 原点復帰
    SEG_STB: List[int] = [LED_S, LED_T, LED_B]      # スタンバイ
    SEG_RUN: List[int] = [LED_R, LED_U, LED_N]      # 実行中
    SEG_RDY: List[int] = [LED_R, LED_D, LED_Y]      # 準備完了
    SEG_END: List[int] = [LED_E, LED_N, LED_D]      # 終了
    SEG_ERR: List[int] = [LED_E, LED_R, LED_R]      # エラー
    SEG_EMG: List[int] = [LED_E, LED_M, LED_G]      # 非常停止
    SEG_PRG: List[int] = [LED_P, LED_R, LED_G]      # プログラム
    SEG_OFF: List[int] = [LED_Off, LED_Off, LED_Off]  # 消灯
    SEG_ALM: List[int] = [LED_A, LED_L, LED_M]      # アラーム
    
    # エラーコード
    SEG_E17: List[int] = [LED_E, LED_1, LED_7]
    SEG_E18: List[int] = [LED_E, LED_1, LED_8]
    SEG_E19: List[int] = [LED_E, LED_1, LED_9]
    SEG_E27: List[int] = [LED_E, LED_2, LED_7]
    SEG_E28: List[int] = [LED_E, LED_2, LED_8]
    SEG_E29: List[int] = [LED_E, LED_2, LED_9]
    SEG_E41: List[int] = [LED_E, LED_4, LED_1]
    SEG_E42: List[int] = [LED_E, LED_4, LED_2]
    SEG_R18: List[int] = [LED_R, LED_1, LED_8]
    SEG_R19: List[int] = [LED_R, LED_1, LED_9]
    
    @staticmethod
    def get_digit(num: int) -> int:
        """数字(0-9)に対応する7セグパターンを取得"""
        mapping = {
            0: Led7Seg.LED_0, 1: Led7Seg.LED_1, 2: Led7Seg.LED_2,
            3: Led7Seg.LED_3, 4: Led7Seg.LED_4, 5: Led7Seg.LED_5,
            6: Led7Seg.LED_6, 7: Led7Seg.LED_7, 8: Led7Seg.LED_8,
            9: Led7Seg.LED_9,
        }
        return mapping.get(num, Led7Seg.LED_Off)
    
    @staticmethod
    def format_number(num: int, prefix: int = None) -> List[int]:
        """2桁の数字を3桁表示用リストに変換
        
        Args:
            num: 表示する数値 (0-99)
            prefix: 先頭文字 (例: LED_P でプログラム番号表示)
        
        Returns:
            3要素のリスト [prefix, tens, ones]
        """
        tens = (num // 10) % 10
        ones = num % 10
        first = prefix if prefix is not None else Led7Seg.LED_Off
        return [first, Led7Seg.get_digit(tens), Led7Seg.get_digit(ones)]


class Axis(IntEnum):
    """軸番号定義"""
    X = 0
    Y = 1
    Z = 2
    U = 3
    S1 = 4
    S2 = 5
    A = 6
    B = 7


class AxisMask(IntEnum):
    """軸選択ビットマスク"""
    X = 0x01
    Y = 0x02
    Z = 0x04
    U = 0x08
    S1 = 0x10
    S2 = 0x20
    A = 0x40
    B = 0x80
    
    XY = 0x03
    XZ = 0x05
    YZ = 0x06
    XYZ = 0x07
    ALL = 0xFF


class OutputPort(IntEnum):
    """出力ポート定義"""
    DRIVER_SV = 100         # ドライバー上下SV
    SCREW_GUIDE = 102       # ネジガイド開閉SV
    SCREW_VACUUM = 104      # ネジ吸着SV
    DS_TIMING = 106         # 変位センサーTiming信号
    DS_RESET = 107          # 変位センサーReset信号
    DRIVER = 109            # 電動ドライバーON/OFF
    WORK_LOCK = 110         # ワークロック
    EMG_LED = 112           # 非常停止LED
    START_LEFT = 113        # スタート左LED
    START_RIGHT = 114       # スタート右LED
    BUZZER = 115            # ブザー


class InputPort(IntEnum):
    """入力ポート定義"""
    DRIVER_UP = 0           # ドライバー上端
    DRIVER_DOWN = 1         # ドライバー下端
    SCREW_GUIDE_CLOSE = 2   # ガイド閉
    SCREW_GUIDE_OPEN = 3    # ガイド開
    SCREW_DETECT = 4        # ネジ有無
    FEEDER_SCREW = 5        # フィーダーネジ
    DS_HIGH = 6             # 変位センサーHigh
    DS_OK = 7               # 変位センサーOK
    DS_LOW = 8              # 変位センサーLow
    DRIVER_TORQUE_UP = 9    # トルクアップ
    WORK_LOCK_ORG = 10      # ワークロック解除
    WORK_LOCK_LOCK = 11     # ワークロック
    WORK_ENABLE = 12        # ワーク有無
    START_LEFT_SW = 13      # 左スタートSW
    START_RIGHT_SW = 14     # 右スタートSW
    EMG_SW = 15             # 非常停止スイッチ


class NOVARegister:
    """NOVAコントローラ レジスタアドレス定義"""
    # 書き込みレジスタ
    WR0 = 0x00
    WR1 = 0x01
    WR2 = 0x02
    WR3 = 0x03
    
    # 読み取りレジスタ
    RR0 = 0x00
    RR0_XDRV = 0x01  # X軸駆動中
    RR0_YDRV = 0x02  # Y軸駆動中
    RR0_ZDRV = 0x04  # Z軸駆動中
    RR0_UDRV = 0x08  # U軸駆動中
    RR0_XERR = 0x10  # X軸エラー
    RR0_YERR = 0x20  # Y軸エラー
    RR0_ZERR = 0x40  # Z軸エラー
    RR0_UERR = 0x80  # U軸エラー
    
    RR1 = 0x01
    RR2 = 0x02
    RR2_ALM = 0x10   # アラーム
    RR2_EMG = 0x20   # 非常停止
    
    RR3 = 0x03
    RR3_STOP0 = 0x0001  # 停止0
    RR3_STOP1 = 0x0002  # 停止1
    RR3_STOP2 = 0x0002  # 停止2 (IAIホーミング完了チェック用)
    RR3_INPOS = 0x0008  # In Position (移動完了)
    RR3_BUSY = 0x0010   # ビジー
    RR3_ALARM = 0x0020  # アラーム
    RR3_ORG = 0x0040    # 原点センサー


class GPIOPin:
    """Raspberry Pi GPIOピン割り当て"""
    NOVA_RESET = 14    # NOVAリセットピン
    NOVA_POWER = 12    # NOVA電源ピン
    POWER = 12         # 電源ピン（NOVA_POWERの別名）
    CAN_CS = 8         # CAN SPIチップセレクト
    EMG_SW = 15        # 非常停止スイッチ


class CANConfig:
    """CAN通信設定"""
    SPI_BUS = 0
    SPI_DEVICE = 0
    SPI_SPEED_HZ = 500000
    BAUDRATE_500K = 500000
    MAX_BOARDS = 16


# MCP2515 CAN Controller Commands
class MCP2515:
    """MCP2515 CANコントローラ コマンド定義"""
    CMD_RESET = 0xC0
    CMD_READ = 0x03
    CMD_WRITE = 0x02
    CMD_BITMOD = 0x05
    CMD_RDRXBUF = 0x90
    CMD_LDTXBUF = 0x40
    CMD_RTS = 0x80
    CMD_STATUS = 0xA0
    CMD_RXSTATUS = 0xB0
    
    REG_RXB0CTRL = 0x60
    REG_RXB1CTRL = 0x70
    REG_CAN_CTRL = 0x0F
    REG_CAN_CNF1 = 0x2A
    REG_CAN_CNF2 = 0x29
    REG_CAN_CNF3 = 0x28
    REG_CANSTAT = 0x0E
    
    MODE_NORMAL = 0
    MODE_SLEEP = 1
    MODE_LOOPBACK = 2
    MODE_LISTEN = 3
    MODE_CONFIG = 4
    
    RX_NO_MASK = 0x60
    MSK_MSGRX0 = 0x40
    MSK_MSGRX1 = 0x80


class RobotState(Enum):
    """ロボット状態"""
    DISCONNECTED = "disconnected"
    INITIALIZING = "initializing"
    IDLE = "idle"
    READY = "ready"
    HOMING = "homing"
    MOVING = "moving"
    ERROR = "error"
    EMERGENCY = "emergency"
    SHUTDOWN = "shutdown"


class ErrorCode(Enum):
    """エラーコード定義"""
    NONE = (0, "エラーなし")
    SCREW_EXISTS = (19, "ネジあり確認エラー")
    FEEDER_EMPTY = (18, "フィーダーネジなし")
    GUIDE_OPEN = (27, "ガイドオープンエラー")
    GUIDE_CLOSE = (28, "ガイドクローズエラー")
    TORQUE_OFF = (41, "トルクアップOFFエラー")
    TORQUE_ON = (42, "トルクアップONエラー")
    
    def __init__(self, code: int, message: str):
        self._code = code
        self._message = message
    
    @property
    def code(self) -> int:
        return self._code
    
    @property
    def message(self) -> str:
        return self._message
    
    def to_7seg(self) -> List[int]:
        """7セグ表示用リストを取得"""
        return Led7Seg.format_number(self._code, Led7Seg.LED_E)
