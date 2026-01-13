# *********************************************************************#
# File Name : motion_controller.py
# Explanation : Async Motion Controller Wrapper for libcsms_splebo_n.so
# Project : AutomatedAssemblyRobot - SPLEBO-N Integration
# ----------------------------------------------------------------------
# Based on : TEACHING/motion_control.py (2544 lines)
# History :
#           ver0.0.1 2026.1.7 New Create - Async wrapper implementation
# *********************************************************************#

"""
MotionController - 非同期モーション制御コントローラ

libcsms_splebo_n.so ネイティブライブラリへのctypesラッパーを提供し、
asyncioベースの非同期インターフェースを実装します。

参照元ファイル:
    - TEACHING/motion_control.py: 全体構造、ctypesラッパー、I2C I/O制御
    - TEACHING/splebo_n.py: axis_set_class, motion_controller_cmd_class

参照元の主要クラス/関数 (行番号はmotion_control.pyを参照):
    - motion_control_class (L39-420):
        - __init__() → MotionController.__init__()
        - initialize_motion_contoller() (L59-300) → MotionController.initialize()
        - motion_control_loop() (L420-740) → MotionController._control_loop()
        - set_write_command() (L740-820) → コマンドキューは廃止、直接呼び出し
    
    - ctypes APIラッパー (L1680-2200):
        - cmd_board_open() → NativeLibrary.open_board()
        - cmd_move_absolute() → NativeLibrary.move_absolute()
        - cmd_move_jog() → NativeLibrary.move_jog()
        - cmd_stop() → NativeLibrary.stop()
        - cmd_get_logicalCoord() → NativeLibrary.get_logical_coordinate()
    
    - モータータイプ別関数:
        - IAI関数 (L1390-1500) → _homing_*_iai(), _servo_on_off_iai()
        - STEPPING関数 (L1500-1600) → _homing_*_step()
        - aSTEP関数 (L1600-1680) → _homing_*_astep()
    
    - I/Oエキスパンダ (L2350-2544):
        - initialize_io_expander() → I2CIOExpander.initialize()
        - write_bit() → I2CIOExpander.write_bit()
        - read_board() → I2CIOExpander.read_board()

移植時の変更点:
    - threading.Thread → asyncio.Task
    - コマンドキューパターン → 直接呼び出し + asyncio.to_thread()
    - splebo_nグローバル変数 → インスタンス変数(AxisConfig, AxisStatus)
    - シミュレーションモード追加（ハードウェアなしでテスト可能）

シミュレーションモード:
    simulation_mode=True で初期化すると、以下が仿像されます:
    - GPIO制御: 仿像値を保持
    - ctypesライブラリ: ロードしない、常にTrueを返す
    - I2C通信: ダミーデータを返す
    ※ 開発PCやCI/CDでのテスト用

使用例:
    controller = MotionController(simulation_mode=True)  # テスト用
    await controller.initialize()
    await controller.move_absolute(Axis.X, 100.0, speed=50)
    await controller.home_all_axes()
    await controller.shutdown()
"""

import asyncio
import ctypes
from ctypes import POINTER, cast, c_int, c_bool
from enum import IntEnum
from dataclasses import dataclass, field
from typing import Optional, Callable, Any, Dict, List
import logging
import time
from pathlib import Path

# 注意: RPi.GPIOは使用しない
# libcsms_splebo_n.soが内部でpigpioを使用しており、
# RPi.GPIOとpigpioを同時に使用するとGPIO設定が競合する
# 詳細: docs/GPIO_CONFLICT_ISSUE.md 参照

try:
    import smbus
    HAS_SMBUS = True
except ImportError:
    HAS_SMBUS = False
    smbus = None

# pigpioのインポートと初期化
# libcsms_splebo_n.so がpigpioを内部的に使用しているため必要
try:
    import pigpio
    HAS_PIGPIO = True
except ImportError:
    HAS_PIGPIO = False
    pigpio = None

# グローバルなpigpioライブラリ・インスタンス
_pigpio_lib = None           # ctypes経由のlibpigpio.soハンドル
_pigpio_instance = None      # Pythonのpigpio.pi()インスタンス
_pigpio_initialized = False

def _load_pigpio_lib():
    """pigpio Cライブラリをロードする（内部関数）"""
    global _pigpio_lib
    
    if _pigpio_lib is not None:
        return _pigpio_lib
    
    import ctypes
    from ctypes import c_int
    
    pigpio_lib_paths = [
        "libpigpio.so",
        "libpigpio.so.1",
        "/usr/lib/libpigpio.so",
        "/usr/lib/arm-linux-gnueabihf/libpigpio.so",
        "/usr/local/lib/libpigpio.so",
    ]
    
    for path in pigpio_lib_paths:
        try:
            _pigpio_lib = ctypes.cdll.LoadLibrary(path)
            # 関数シグネチャの設定
            _pigpio_lib.gpioInitialise.restype = c_int
            _pigpio_lib.gpioTerminate.restype = None
            _pigpio_lib.gpioRead.argtypes = (c_int,)
            _pigpio_lib.gpioRead.restype = c_int
            _pigpio_lib.gpioWrite.argtypes = (c_int, c_int)
            _pigpio_lib.gpioWrite.restype = c_int
            _pigpio_lib.gpioSetMode.argtypes = (c_int, c_int)
            _pigpio_lib.gpioSetMode.restype = c_int
            logger.debug(f"pigpioライブラリ読み込み成功: {path}")
            return _pigpio_lib
        except OSError:
            continue
    
    return None


def initialize_pigpio() -> bool:
    """pigpioを初期化する
    
    libcsms_splebo_n.soがpigpioを内部的に使用しているため、
    ライブラリ使用前にgpioInitialise()を呼び出す必要があります。
    
    注意: 
    - ネイティブライブラリはCレベルのgpioInitialise()を必要とする
    - pigpiodが起動している場合は停止してから実行: sudo killall pigpiod
    - root権限が必要: sudo python ...
    
    Returns:
        初期化成功時True、失敗時False
    """
    global _pigpio_instance, _pigpio_initialized
    
    if _pigpio_initialized:
        return True  # 既に初期化済み
    
    # 方法1: ctypesでlibpigpio.soを直接ロードしてgpioInitialise()を呼び出す
    pigpio_lib = _load_pigpio_lib()
    
    if pigpio_lib is not None:
        try:
            result = pigpio_lib.gpioInitialise()
            if result >= 0:
                _pigpio_initialized = True
                logger.info(f"gpioInitialise() 成功 (version: {result})")
                return True
            else:
                logger.warning(f"gpioInitialise() 失敗 (エラーコード: {result})")
                logger.info("root権限で実行してください: sudo python ...")
        except Exception as e:
            logger.warning(f"gpioInitialise()エラー: {e}")
    else:
        logger.warning("libpigpio.soが見つかりません")
    
    # 方法2: Pythonのpigpioモジュール経由でデーモン接続（フォールバック）
    # 注意: デーモンモードは cw_mc_open() が内部で gpioInitialise() を呼ぶため非推奨
    if HAS_PIGPIO:
        try:
            _pigpio_instance = pigpio.pi()
            if _pigpio_instance.connected:
                logger.info("pigpioデーモンに接続しました（デーモンモード）")
                logger.warning("警告: デーモンモードでは一部機能が制限される可能性があります")
                return True
            else:
                logger.error("pigpioデーモンに接続できません。")
                logger.info("解決策: sudo killall pigpiod && sudo python ...")
                _pigpio_instance = None
        except Exception as e:
            logger.warning(f"pigpioデーモン接続エラー: {e}")
    
    return False


def gpio_read(pin: int) -> int:
    """GPIOピンを読み取る（pigpio経由）
    
    RPi.GPIOの代わりにpigpioを使用してGPIOを読み取る。
    これにより、libcsms_splebo_n.soとのGPIO競合を防ぐ。
    
    Args:
        pin: GPIOピン番号（BCM）
    
    Returns:
        0 または 1、エラー時は -1
    """
    global _pigpio_lib, _pigpio_instance
    
    # Cライブラリ経由
    if _pigpio_lib is not None:
        return _pigpio_lib.gpioRead(pin)
    
    # Pythonインスタンス経由
    if _pigpio_instance is not None and _pigpio_instance.connected:
        return _pigpio_instance.read(pin)
    
    logger.warning(f"GPIO{pin}を読み取れません: pigpioが初期化されていません")
    return -1


def gpio_write(pin: int, value: int) -> bool:
    """GPIOピンに書き込む（pigpio経由）
    
    Args:
        pin: GPIOピン番号（BCM）
        value: 0 または 1
    
    Returns:
        成功時True
    """
    global _pigpio_lib, _pigpio_instance
    
    # Cライブラリ経由
    if _pigpio_lib is not None:
        result = _pigpio_lib.gpioWrite(pin, value)
        return result == 0
    
    # Pythonインスタンス経由
    if _pigpio_instance is not None and _pigpio_instance.connected:
        _pigpio_instance.write(pin, value)
        return True
    
    logger.warning(f"GPIO{pin}に書き込めません: pigpioが初期化されていません")
    return False


def cleanup_pigpio():
    """pigpioをクリーンアップする"""
    global _pigpio_lib, _pigpio_instance, _pigpio_initialized
    
    # Pythonインスタンスのクリーンアップ
    if _pigpio_instance is not None:
        try:
            _pigpio_instance.stop()
        except:
            pass
        _pigpio_instance = None
    
    # Cレベルのgpioをクリーンアップ
    if _pigpio_initialized and _pigpio_lib is not None:
        try:
            _pigpio_lib.gpioTerminate()
            logger.debug("gpioTerminate() 呼び出し完了")
        except Exception as e:
            logger.warning(f"gpioTerminate()エラー: {e}")
        _pigpio_initialized = False


def get_pigpio_lib():
    """pigpio Cライブラリハンドルを取得する
    
    Returns:
        ctypes経由のlibpigpio.soハンドル、未初期化時はNone
    """
    return _pigpio_lib


def is_pigpio_initialized() -> bool:
    """pigpioが初期化されているか確認する
    
    Returns:
        True: 初期化済み
    """
    return _pigpio_initialized


def is_emergency_active() -> bool:
    """非常停止スイッチの状態を確認する
    
    Returns:
        True: 非常停止中、False: 正常
    """
    value = gpio_read(GPIOPin.EMG_SW)
    # GPIO15はLOW(0)で正常、HIGH(1)で非常停止
    return value != 0


from .constants import Axis, AxisMask, GPIOPin, NOVARegister


logger = logging.getLogger(__name__)


# =============================================================================
# Enums and Constants
# =============================================================================

class MotorType(IntEnum):
    """モータータイプ定義"""
    NONE = 0
    IAI = 1          # IAI電動アクチュエータ
    STEPPING = 2     # ステッピングモータ
    ASTEP = 3        # Oriental Motor aSTEP


class MotionCommand(IntEnum):
    """モーション制御コマンド"""
    OPEN = 0
    SET_MODE = 1
    SET_DRIVE_SPEED = 2
    SET_INITIAL_VELOCITY = 3
    SET_ACCELERATION = 4
    SET_DECELERATION = 5
    SET_RET_ORIGIN_MODE = 6
    SET_IO_SIGNAL = 7
    SET_INPUT_SIGNAL_FILTER = 8
    AUTO_ORIGIN = 9
    SET_SOFT_LIMIT = 10
    MOVE_RELATIVE = 11
    MOVE_ABSOLUTE = 12
    MOVE_JOG = 13
    STOP = 14
    DECELERATION_STOP = 15
    LINE_INTERPOLATION = 16
    CIRCLE_INTERPOLATION = 17
    CONTINUE_INTERPOLATION = 18
    GET_LOGICAL_COORD = 19
    GET_RELATIVE_COORD = 20
    SET_LOGICAL_COORD = 21
    SET_RELATIVE_COORD = 22
    GET_GENERAL_IO = 23
    SET_GENERAL_OUTPUT = 24
    SET_GENERAL_OUTPUT_BIT = 25
    GET_AXIS_STATUS = 26
    WRITE_REGISTER = 27
    READ_REGISTER = 28


class AxisIO(IntEnum):
    """軸I/Oポート番号"""
    OUT0 = 0  # サーボON/OFF
    OUT1 = 1  # クリア
    OUT2 = 2  # ホーミング
    OUT3 = 3
    OUT4 = 4
    OUT5 = 5
    OUT6 = 6
    OUT7 = 7
    DCC_OUT = 8


class MoveType(IntEnum):
    """移動タイプ"""
    RELATIVE = 0
    ABSOLUTE = 1
    JOG = 2


class ControllerState(IntEnum):
    """コントローラ状態"""
    UNINITIALIZED = 0
    INITIALIZING = 1
    READY = 2
    MOVING = 3
    HOMING = 4
    ERROR = 5
    STOPPED = 6


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class AxisConfig:
    """軸設定"""
    motor_type: MotorType = MotorType.NONE
    max_speed: int = 1000
    start_speed: int = 100
    max_accel: int = 500
    max_decel: int = 500
    pulse_length: float = 0.01  # mm/pulse
    limit_minus: float = 0.0
    limit_plus: float = 500.0
    in_position: int = 1
    origin_speed: float = 50.0
    origin_dir: int = 1  # 0: CW, 1: CCW
    origin_offset: float = 0.0
    offset_speed: float = 10.0
    origin_sensor: int = 0  # 0: OFF, 1: ON, 2: AUTO
    origin_order: int = 1   # 原点復帰順序 (大きい値が先に実行)


@dataclass
class AxisStatus:
    """軸ステータス"""
    abs_coord: float = 0.0
    is_homing: bool = False
    is_home_completed: bool = False
    is_homing_error: bool = False
    is_servo_on: bool = False
    is_alarm: bool = False
    is_emergency: bool = False
    is_busy: bool = False
    is_in_position: bool = True
    is_origin_sensor: bool = False


@dataclass
class MotionOrder:
    """モーション命令"""
    command: MotionCommand = MotionCommand.OPEN
    axis: int = 0
    target_position: int = 0
    speed: int = 0
    is_ccw: bool = False
    is_abs: bool = True
    is_completed: bool = False
    is_success: bool = False
    read_data: str = ""


@dataclass
class IOExpanderConfig:
    """I/Oエキスパンダ設定
    
    オリジナルのio_expander.pyから:
    - kI2c_bus = 5 (オリジナル、現在のシステムでは存在しない)
    - 利用可能なバス: /dev/i2c-1, /dev/i2c-3, /dev/i2c-20, /dev/i2c-21
    - kExpand_module_address_0 = 0x21 (Input Board 0)
    - kExpand_module_address_1 = 0x24 (Output Board 0)
    - kExpand_module_address_2 = 0x23 (Input Board 1)
    - kExpand_module_address_3 = 0x26 (Output Board 1)
    """
    i2c_bus: int = 3  # 環境に合わせて調整
    input_address: int = 0x21
    output_address: int = 0x24
    board_count: int = 4
    board_bits: int = 16


def load_axis_configs_from_sys_file(sys_file_path: str) -> Dict[int, AxisConfig]:
    """SPLEBO-N.sysファイルから軸設定を読み込む
    
    Args:
        sys_file_path: SPLEBO-N.sysファイルのパス
        
    Returns:
        軸番号をキーとしたAxisConfig辞書
    """
    import configparser
    import os
    
    configs = {}
    
    if not os.path.exists(sys_file_path):
        logger.warning(f"設定ファイルが見つかりません: {sys_file_path}")
        return configs
    
    parser = configparser.ConfigParser()
    parser.read(sys_file_path)
    
    if 'SysParam' not in parser:
        logger.warning("SysParamセクションが見つかりません")
        return configs
    
    def get_list(key: str, default: List = None) -> List[str]:
        if key in parser['SysParam']:
            return parser['SysParam'][key].split(',')
        return default or []
    
    # 各パラメータを読み込み
    motor_types = get_list('MotorType', ['0']*8)
    max_speeds = get_list('MaxSpeed', ['1000']*8)
    start_speeds = get_list('StartSpeed', ['100']*8)
    max_accels = get_list('MaxAccel', ['500']*8)
    max_decels = get_list('MaxDecel', ['500']*8)
    pulse_lengths = get_list('PulseLength', ['0.01']*8)
    limit_pluses = get_list('LimitPlus', ['500']*8)
    limit_minuses = get_list('LimitMinus', ['0']*8)
    origin_speeds = get_list('OriginSpeed', ['10']*8)
    origin_dirs = get_list('OriginDir', ['0']*8)
    origin_offsets = get_list('OriginOffset', ['0']*8)
    origin_sensors = get_list('OriginSensor', ['0']*8)
    origin_orders = get_list('OriginOrder', ['1']*8)
    in_positions = get_list('InPosition', ['1']*8)
    offset_speeds = get_list('OffsetSpeed', ['10']*8)
    
    # 軸ごとにAxisConfigを作成
    for i in range(min(8, len(motor_types))):
        try:
            motor_type_val = int(motor_types[i].strip())
            if motor_type_val == 0:
                motor_type = MotorType.NONE
            elif motor_type_val == 1:
                motor_type = MotorType.IAI
            elif motor_type_val == 2:
                motor_type = MotorType.STEPPING
            elif motor_type_val == 3:
                motor_type = MotorType.ASTEP
            else:
                motor_type = MotorType.NONE
            
            configs[i] = AxisConfig(
                motor_type=motor_type,
                max_speed=int(max_speeds[i].strip()) if i < len(max_speeds) else 1000,
                start_speed=int(start_speeds[i].strip()) if i < len(start_speeds) else 100,
                max_accel=int(max_accels[i].strip()) if i < len(max_accels) else 500,
                max_decel=int(max_decels[i].strip()) if i < len(max_decels) else 500,
                pulse_length=float(pulse_lengths[i].strip()) if i < len(pulse_lengths) else 0.01,
                limit_plus=float(limit_pluses[i].strip()) if i < len(limit_pluses) else 500.0,
                limit_minus=float(limit_minuses[i].strip()) if i < len(limit_minuses) else 0.0,
                origin_speed=float(origin_speeds[i].strip()) if i < len(origin_speeds) else 10.0,
                origin_dir=int(origin_dirs[i].strip()) if i < len(origin_dirs) else 0,
                origin_offset=float(origin_offsets[i].strip()) if i < len(origin_offsets) else 0.0,
                origin_sensor=int(origin_sensors[i].strip()) if i < len(origin_sensors) else 0,
                origin_order=int(origin_orders[i].strip()) if i < len(origin_orders) else 1,
                in_position=int(in_positions[i].strip()) if i < len(in_positions) else 1,
                offset_speed=float(offset_speeds[i].strip()) if i < len(offset_speeds) else 10.0,
            )
            
            if motor_type != MotorType.NONE:
                logger.info(f"軸{i}設定読み込み: type={motor_type.name}, origin_sensor={configs[i].origin_sensor}")
                
        except (ValueError, IndexError) as e:
            logger.warning(f"軸{i}設定読み込みエラー: {e}")
            configs[i] = AxisConfig()
    
    return configs


# =============================================================================
# Native Library Interface
# =============================================================================

class NativeLibrary:
    """
    libcsms_splebo_n.so ネイティブライブラリのctypesラッパー
    
    NOVAモーションコントローラボードへの低レベルアクセスを提供
    
    参照元: TEACHING/motion_control.py L31
        eCsms_lib = ctype.cdll.LoadLibrary("./libcsms_splebo_n.so")
    """
    
    # ライブラリの検索パス
    LIBRARY_SEARCH_PATHS = [
        "./libcsms_splebo_n.so",
        "/home/splebopi/SPLEBO/TEACHING/libcsms_splebo_n.so",
        "/home/splebopi/SPLEBO/AutomatedAssemblyRobot/libcsms_splebo_n.so",
        "/home/splebopi/SPLEBO/AutomatedAssemblyRobot/src/robot/libcsms_splebo_n.so",
        "/usr/local/lib/libcsms_splebo_n.so",
        "/usr/lib/libcsms_splebo_n.so",
    ]
    
    def __init__(self, library_path: Optional[str] = None):
        self.library_path = library_path
        self._lib: Optional[ctypes.CDLL] = None
        self._loaded = False
    
    def load(self) -> bool:
        """ライブラリをロード（複数のパスを検索）"""
        import os
        
        # 指定されたパスがあればそれを優先
        search_paths = [self.library_path] if self.library_path else []
        search_paths.extend(self.LIBRARY_SEARCH_PATHS)
        
        for path in search_paths:
            if path is None:
                continue
            if os.path.exists(path):
                try:
                    self._lib = ctypes.cdll.LoadLibrary(path)
                    self._setup_function_signatures()
                    self._loaded = True
                    self.library_path = path
                    logger.info(f"Native library loaded: {path}")
                    return True
                except OSError as e:
                    logger.warning(f"Failed to load library from {path}: {e}")
                    continue
        
        logger.error(f"Failed to load native library from any path")
        self._loaded = False
        return False
    
    def _setup_function_signatures(self):
        """
        関数シグネチャの設定
        
        libcsms_splebo_n.so で利用可能な関数（nm -D で確認済み）:
            cw_mc_open, cw_mc_close, cw_mc_abs, cw_mc_ptp, cw_mc_jog,
            cw_mc_stop, cw_mc_dcc_stop, cw_mc_org,
            cw_mc_set_mode, cw_mc_set_drive, cw_mc_set_iv, cw_mc_set_acc, cw_mc_set_dec,
            cw_mc_set_org_mode, cw_mc_set_signal_io, cw_mc_set_input_filter, cw_mc_set_slimit,
            cw_mc_set_intrpt_mode, cw_mc_set_logic_cie, cw_mc_set_real_cie,
            cw_mc_set_gen_out, cw_mc_set_gen_bout,
            cw_mc_get_logic_cie, cw_mc_get_sts,
            cw_mc_r_reg, cw_mc_w_reg, cw_mc_r_reg_axis, cw_mc_w_reg_axis, cw_mc_w_reg67,
            cw_mc_line_intrpt, cw_mc_circ_intrpt
        
        注意: cw_mc_get_real_cie, cw_mc_get_gen_io は存在しない
        """
        if not self._lib:
            return
        
        # Board Open/Close
        self._lib.cw_mc_open.restype = c_bool
        self._lib.cw_mc_close.restype = c_bool
        
        # Set Mode
        self._lib.cw_mc_set_mode.argtypes = (c_int, c_int, c_int, c_int, c_bool)
        self._lib.cw_mc_set_mode.restype = c_bool
        
        # Set Drive Speed
        self._lib.cw_mc_set_drive.argtypes = (c_int, c_int, c_bool)
        self._lib.cw_mc_set_drive.restype = c_bool
        
        # Set Initial Velocity
        self._lib.cw_mc_set_iv.argtypes = (c_int, c_int, c_bool)
        self._lib.cw_mc_set_iv.restype = c_bool
        
        # Set Acceleration
        self._lib.cw_mc_set_acc.argtypes = (c_int, c_int, c_bool)
        self._lib.cw_mc_set_acc.restype = c_bool
        
        # Set Deceleration
        self._lib.cw_mc_set_dec.argtypes = (c_int, c_int, c_bool)
        self._lib.cw_mc_set_dec.restype = c_bool
        
        # Set Return Origin Mode
        self._lib.cw_mc_set_org_mode.argtypes = (c_int, c_int, c_int, c_bool)
        self._lib.cw_mc_set_org_mode.restype = c_bool
        
        # Set I/O Signal
        self._lib.cw_mc_set_signal_io.argtypes = (c_int, c_int, c_int, c_bool)
        self._lib.cw_mc_set_signal_io.restype = c_bool
        
        # Set Input Signal Filter
        self._lib.cw_mc_set_input_filter.argtypes = (c_int, c_int, c_bool)
        self._lib.cw_mc_set_input_filter.restype = c_bool
        
        # Auto Origin (参照: motion_control.py L1751 - cw_mc_org)
        self._lib.cw_mc_org.argtypes = (c_int, c_int, c_int)
        self._lib.cw_mc_org.restype = c_bool
        
        # Set Soft Limit
        self._lib.cw_mc_set_slimit.argtypes = (c_int, c_int, c_int)
        self._lib.cw_mc_set_slimit.restype = c_bool
        
        # Move Absolute
        self._lib.cw_mc_abs.argtypes = (c_int, c_int, c_int)
        self._lib.cw_mc_abs.restype = c_bool
        
        # Move Relative (参照: motion_control.py L1777 - cw_mc_ptp)
        self._lib.cw_mc_ptp.argtypes = (c_int, c_int, c_int, c_bool)
        self._lib.cw_mc_ptp.restype = c_bool
        
        # Move JOG
        self._lib.cw_mc_jog.argtypes = (c_int, c_bool, c_int)
        self._lib.cw_mc_jog.restype = c_bool
        
        # Stop
        self._lib.cw_mc_stop.argtypes = (c_int,)
        self._lib.cw_mc_stop.restype = c_bool
        
        # Deceleration Stop
        self._lib.cw_mc_dcc_stop.argtypes = (c_int,)
        self._lib.cw_mc_dcc_stop.restype = c_bool
        
        # Get Logical Coordinate
        self._lib.cw_mc_get_logic_cie.argtypes = (c_int, POINTER(c_int))
        self._lib.cw_mc_get_logic_cie.restype = c_bool
        
        # Set Logical Coordinate
        self._lib.cw_mc_set_logic_cie.argtypes = (c_int, c_int)
        self._lib.cw_mc_set_logic_cie.restype = c_bool
        
        # Set Relative Coordinate (get版は存在しない)
        self._lib.cw_mc_set_real_cie.argtypes = (c_int, c_int)
        self._lib.cw_mc_set_real_cie.restype = c_bool
        
        # Set General Output
        self._lib.cw_mc_set_gen_out.argtypes = (c_int, c_int)
        self._lib.cw_mc_set_gen_out.restype = c_bool
        
        # Set General Output Bit
        self._lib.cw_mc_set_gen_bout.argtypes = (c_int, c_int, c_bool)
        self._lib.cw_mc_set_gen_bout.restype = c_bool
        
        # Get Axis Status
        self._lib.cw_mc_get_sts.argtypes = (c_int, POINTER(c_int), c_int)
        self._lib.cw_mc_get_sts.restype = c_bool
        
        # Write Register
        self._lib.cw_mc_w_reg.argtypes = (c_int, c_int, c_int)
        self._lib.cw_mc_w_reg.restype = c_bool
        
        # Read Register
        self._lib.cw_mc_r_reg.argtypes = (c_int, c_int, POINTER(c_int))
        self._lib.cw_mc_r_reg.restype = c_bool
        
        # Write Register 6/7
        self._lib.cw_mc_w_reg67.argtypes = (c_int, c_int)
        self._lib.cw_mc_w_reg67.restype = c_bool
        
        # Set Interpolation Mode
        self._lib.cw_mc_set_intrpt_mode.argtypes = (c_int, c_int, c_bool)
        self._lib.cw_mc_set_intrpt_mode.restype = c_bool
    
    @property
    def is_loaded(self) -> bool:
        return self._loaded
    
    # =========================================================================
    # Low-level API Methods
    # =========================================================================
    
    def open_board(self) -> bool:
        """ボードを開く"""
        if not self._lib:
            return False
        return bool(self._lib.cw_mc_open())
    
    def set_mode(self, axis: int, wr1: int, wr2: int, wr3: int, lock: bool = False) -> bool:
        """モードを設定"""
        if not self._lib:
            return False
        return bool(self._lib.cw_mc_set_mode(axis, wr1, wr2, wr3, lock))
    
    def set_drive_speed(self, axis: int, speed: int, lock: bool = False) -> bool:
        """駆動速度を設定"""
        if not self._lib:
            return False
        return bool(self._lib.cw_mc_set_drive(axis, speed, lock))
    
    def set_initial_velocity(self, axis: int, velocity: int, lock: bool = False) -> bool:
        """初期速度を設定"""
        if not self._lib:
            return False
        return bool(self._lib.cw_mc_set_iv(axis, velocity, lock))
    
    def set_acceleration(self, axis: int, accel: int, lock: bool = False) -> bool:
        """加速度を設定"""
        if not self._lib:
            return False
        return bool(self._lib.cw_mc_set_acc(axis, accel, lock))
    
    def set_deceleration(self, axis: int, decel: int, lock: bool = False) -> bool:
        """減速度を設定"""
        if not self._lib:
            return False
        return bool(self._lib.cw_mc_set_dec(axis, decel, lock))
    
    def set_origin_mode(self, axis: int, h1m: int, h2m: int, lock: bool = False) -> bool:
        """原点復帰モードを設定
        
        参照: TEACHING/motion_control.py L1713 - cmd_set_ret_origin_mode
        
        Args:
            axis: 軸番号
            h1m: 第1ホーミングモード
            h2m: 第2ホーミングモード
            lock: ロックフラグ
        """
        if not self._lib:
            return False
        return bool(self._lib.cw_mc_set_org_mode(axis, h1m, h2m, lock))
    
    def auto_origin(self, axis: int, hv: int, dv: int) -> bool:
        """オートオリジン（原点復帰）を実行
        
        参照: TEACHING/motion_control.py L1751 - cmd_auto_origin
        
        Args:
            axis: 軸番号
            hv: ホーミング速度
            dv: ドライブ速度
        """
        if not self._lib:
            return False
        return bool(self._lib.cw_mc_org(axis, hv, dv))
    
    def set_soft_limit(self, axis: int, limit_minus: int, limit_plus: int) -> bool:
        """ソフトリミットを設定"""
        if not self._lib:
            return False
        return bool(self._lib.cw_mc_set_slimit(axis, limit_minus, limit_plus))
    
    def move_absolute(self, axis: int, target_position: int, speed: int) -> bool:
        """絶対位置移動"""
        if not self._lib:
            return False
        return bool(self._lib.cw_mc_abs(axis, target_position, speed))
    
    def move_relative(self, axis: int, distance: int, speed: int, abs_mode: bool = False) -> bool:
        """相対位置移動 (参照: motion_control.py L1777 - cw_mc_ptp)"""
        if not self._lib:
            return False
        return bool(self._lib.cw_mc_ptp(axis, distance, speed, abs_mode))
    
    def move_jog(self, axis: int, ccw: bool, speed: int) -> bool:
        """JOG移動"""
        if not self._lib:
            return False
        return bool(self._lib.cw_mc_jog(axis, ccw, speed))
    
    def stop(self, axis: int) -> bool:
        """即時停止"""
        if not self._lib:
            return False
        return bool(self._lib.cw_mc_stop(axis))
    
    def deceleration_stop(self, axis: int) -> bool:
        """減速停止"""
        if not self._lib:
            return False
        return bool(self._lib.cw_mc_dcc_stop(axis))
    
    def get_logical_coordinate(self, axis: int) -> Optional[int]:
        """論理座標を取得"""
        if not self._lib:
            return None
        buffer = (c_int * 16)()
        ptr = cast(buffer, POINTER(c_int))
        if self._lib.cw_mc_get_logic_cie(axis, ptr):
            return ptr.contents.value
        return None
    
    def set_logical_coordinate(self, axis: int, coord: int) -> bool:
        """論理座標を設定"""
        if not self._lib:
            return False
        return bool(self._lib.cw_mc_set_logic_cie(axis, coord))
    
    def set_relative_coordinate(self, axis: int, coord: int) -> bool:
        """相対座標を設定"""
        if not self._lib:
            return False
        return bool(self._lib.cw_mc_set_real_cie(axis, coord))
    
    def get_axis_status(self, axis: int, sts_no: int) -> Optional[int]:
        """
        軸ステータスを取得
        
        ライブラリにcw_mc_get_gen_ioが存在しないため、
        cw_mc_get_stsを使用してステータスを取得します。
        """
        if not self._lib:
            return None
        buffer = (c_int * 16)()
        ptr = cast(buffer, POINTER(c_int))
        if self._lib.cw_mc_get_sts(axis, ptr, sts_no):
            return ptr.contents.value
        return None
    
    def set_general_output_bit(self, axis: int, bit: int, on: bool) -> bool:
        """汎用出力ビットを設定"""
        if not self._lib:
            return False
        return bool(self._lib.cw_mc_set_gen_bout(axis, bit, on))
    
    def read_register(self, axis: int, reg_no: int) -> Optional[int]:
        """レジスタを読み取り"""
        if not self._lib:
            return None
        buffer = (c_int * 16)()
        ptr = cast(buffer, POINTER(c_int))
        if self._lib.cw_mc_r_reg(axis, reg_no, ptr):
            return ptr.contents.value
        return None
    
    def write_register(self, axis: int, reg_no: int, data: int) -> bool:
        """レジスタに書き込み"""
        if not self._lib:
            return False
        return bool(self._lib.cw_mc_w_reg(axis, reg_no, data))


# =============================================================================
# I/O Expander (I2C)
# =============================================================================

class I2CIOExpander:
    """
    I2C接続のI/Oエキスパンダ制御
    
    MCP23017チップを使用したI/Oエキスパンダの制御を行います。
    motion_control.pyのI/Oエキスパンダ機能を非同期化したものです。
    """
    
    # MCP23017 レジスタアドレス (BANK0モード)
    IODIRA = 0x00
    IODIRB = 0x01
    IPOLA = 0x02
    IPOLB = 0x03
    GPIOA = 0x12
    GPIOB = 0x13
    OLATA = 0x14
    OLATB = 0x15
    
    def __init__(self, config: Optional[IOExpanderConfig] = None, simulation_mode: bool = False):
        self.config = config or IOExpanderConfig()
        self._simulation_mode = simulation_mode
        self._smbus: Optional[Any] = None
        self._initialized = False
        self._read_data: List[int] = [0] * self.config.board_count
        self._write_data: List[int] = [0] * self.config.board_count
        self._lock = asyncio.Lock()
    
    async def initialize(self) -> bool:
        """I/Oエキスパンダを初期化"""
        if self._simulation_mode or not HAS_SMBUS:
            logger.warning("I/O expander running in simulation mode")
            self._initialized = True
            return True
        
        try:
            self._smbus = smbus.SMBus(self.config.i2c_bus)
            
            # Input Board: Set as input (0xFF), inverted logic
            self._smbus.write_byte_data(
                self.config.input_address, self.IODIRA, 0xFF)
            self._smbus.write_byte_data(
                self.config.input_address, self.IODIRB, 0xFF)
            self._smbus.write_byte_data(
                self.config.input_address, self.IPOLA, 0xFF)
            self._smbus.write_byte_data(
                self.config.input_address, self.IPOLB, 0xFF)
            
            # Output Board: Set as output (0x00)
            self._smbus.write_byte_data(
                self.config.output_address, self.IODIRA, 0x00)
            self._smbus.write_byte_data(
                self.config.output_address, self.IODIRB, 0x00)
            self._smbus.write_byte_data(
                self.config.output_address, self.IPOLA, 0x00)
            self._smbus.write_byte_data(
                self.config.output_address, self.IPOLB, 0x00)
            
            self._initialized = True
            logger.info("I/O expander initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize I/O expander: {e}")
            return False
    
    async def write_bit(self, board_no: int, bit_no: int, on: bool) -> None:
        """ビットを設定"""
        async with self._lock:
            if 0 <= board_no < self.config.board_count:
                if on:
                    self._write_data[board_no] |= (1 << bit_no)
                else:
                    self._write_data[board_no] &= ~(1 << bit_no)
    
    async def read_board(self, board_no: int) -> Optional[int]:
        """ボードを読み取り"""
        if not self._smbus:
            return self._read_data[board_no] if board_no < len(self._read_data) else None
        
        async with self._lock:
            try:
                address = self.config.input_address if board_no == 0 else self.config.output_address
                side_a = await asyncio.to_thread(
                    self._smbus.read_byte_data, address, self.GPIOA)
                side_b = await asyncio.to_thread(
                    self._smbus.read_byte_data, address, self.GPIOB)
                data = side_a | (side_b << 8)
                self._read_data[board_no] = data
                return data
            except Exception as e:
                logger.error(f"Failed to read I/O board {board_no}: {e}")
                return None
    
    async def write_board(self, board_no: int) -> bool:
        """ボードに書き込み"""
        if not self._smbus:
            return True  # Simulation mode
        
        async with self._lock:
            try:
                address = self.config.output_address
                data = self._write_data[board_no]
                side_a = data & 0xFF
                side_b = (data >> 8) & 0xFF
                await asyncio.to_thread(
                    self._smbus.write_byte_data, address, self.OLATA, side_a)
                await asyncio.to_thread(
                    self._smbus.write_byte_data, address, self.OLATB, side_b)
                return True
            except Exception as e:
                logger.error(f"Failed to write I/O board {board_no}: {e}")
                return False
    
    async def io_cycle(self) -> None:
        """I/Oサイクルを実行（読み書き）"""
        await self.write_board(0)
        await asyncio.sleep(0.001)
        await self.read_board(0)
        await asyncio.sleep(0.001)


# =============================================================================
# Motion Controller
# =============================================================================

class MotionController:
    """
    非同期モーションコントローラ
    
    libcsms_splebo_n.so ネイティブライブラリを使用して
    NOVAモーションコントローラボードを制御します。
    
    オリジナルのmotion_control.pyのスレッドベース実装を
    asyncioベースに変換したものです。
    
    使用例:
        controller = MotionController()
        await controller.initialize()
        
        # 軸を移動
        await controller.move_absolute(Axis.X, 100.0, speed_percent=50)
        await controller.wait_motion_complete(Axis.X)
        
        # 原点復帰
        await controller.home_axis(Axis.X)
        
        # シャットダウン
        await controller.shutdown()
    """
    
    # デフォルト軸数
    DEFAULT_AXIS_COUNT = 8
    
    def __init__(
        self,
        library_path: str = "./libcsms_splebo_n.so",
        simulation_mode: bool = False,
        axis_count: int = DEFAULT_AXIS_COUNT
    ):
        """
        Args:
            library_path: ネイティブライブラリのパス
            simulation_mode: シミュレーションモード（ハードウェアなし）
            axis_count: 軸数
        """
        self.library_path = library_path
        self.simulation_mode = simulation_mode
        self.axis_count = axis_count
        
        # Components
        self._native_lib = NativeLibrary(library_path)
        self._io_expander = I2CIOExpander(simulation_mode=simulation_mode)
        
        # State
        self._state = ControllerState.UNINITIALIZED
        self._initialized = False
        self._running = False
        
        # Axis configuration and status
        self._axis_configs: Dict[int, AxisConfig] = {}
        self._axis_status: Dict[int, AxisStatus] = {}
        for i in range(axis_count):
            self._axis_configs[i] = AxisConfig()
            self._axis_status[i] = AxisStatus()
        
        # Motor type function dispatch
        self._homing_functions: Dict[int, Dict[str, Callable]] = {}
        
        # Tasks
        self._control_loop_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()
        
        # GPIO
        self._gpio_initialized = False
    
    @property
    def state(self) -> ControllerState:
        """現在の状態"""
        return self._state
    
    @property
    def is_ready(self) -> bool:
        """準備完了かどうか"""
        return self._state == ControllerState.READY
    
    def get_axis_config(self, axis: int) -> Optional[AxisConfig]:
        """軸設定を取得"""
        return self._axis_configs.get(axis)
    
    def set_axis_config(self, axis: int, config: AxisConfig) -> None:
        """軸設定を設定"""
        self._axis_configs[axis] = config
    
    def get_axis_status(self, axis: int) -> Optional[AxisStatus]:
        """軸ステータスを取得"""
        return self._axis_status.get(axis)
    
    # =========================================================================
    # Initialization
    # =========================================================================
    
    async def initialize(self) -> bool:
        """
        モーションコントローラを初期化
        
        Returns:
            成功した場合True
        """
        if self._initialized:
            logger.warning("Motion controller already initialized")
            return True
        
        self._state = ControllerState.INITIALIZING
        logger.info("Initializing motion controller...")
        
        try:
            # Initialize pigpio first (required by libcsms_splebo_n.so)
            if not self.simulation_mode:
                if not initialize_pigpio():
                    logger.warning("pigpio initialization failed - I2C functions may not work")
                    logger.info("pigpiodデーモンを起動してください: sudo pigpiod")
            
            # Initialize GPIO
            if not self.simulation_mode:
                await self._initialize_gpio()
            
            # Load native library
            if not self.simulation_mode:
                if not self._native_lib.load():
                    logger.error("Failed to load native library")
                    self._state = ControllerState.ERROR
                    return False
            
            # Initialize I/O expander
            await self._io_expander.initialize()
            
            # Open motion board (MUST be done before starting control loop)
            # cw_mc_open() initializes I2C handles and GPIO
            if not self.simulation_mode:
                if not await self._open_board():
                    logger.error("Failed to open motion board")
                    self._state = ControllerState.ERROR
                    return False
            
            # Configure axes
            await self._configure_axes()
            
            # Start control loop (after board is opened)
            self._running = True
            self._control_loop_task = asyncio.create_task(self._control_loop())
            
            # Wait a bit for the control loop to start
            await asyncio.sleep(0.1)
            
            # Initialize I/O expander hardware
            if not self.simulation_mode:
                await self._io_expander.initialize()
            
            self._initialized = True
            self._state = ControllerState.READY
            logger.info("Motion controller initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Motion controller initialization failed: {e}")
            self._state = ControllerState.ERROR
            return False
    
    async def _initialize_gpio(self) -> None:
        """GPIO初期化
        
        注意: cw_mc_open()が内部でpigpioを使用してGPIO12/14を設定するため、
        ここではRPi.GPIOを使用しない（競合を防ぐため）。
        詳細: docs/GPIO_CONFLICT_ISSUE.md 参照
        """
        # cw_mc_open()が以下を実行する:
        #   gpioInitialise()
        #   gpioSetMode(12, OUTPUT)  # NOVA_POWER
        #   gpioSetMode(14, OUTPUT)  # NOVA_RESET  
        #   gpioWrite(12, HIGH)      # 電源ON
        #   gpioWrite(14, LOW)       # リセット解除
        # 
        # したがって、ここでのGPIO初期化は不要
        # RPi.GPIOを使用すると、pigpioの設定を上書きしてI2C通信が失敗する
        
        self._gpio_initialized = True
        logger.info("GPIO initialization delegated to cw_mc_open()")
    
    async def _open_board(self) -> bool:
        """モーションボードを開く"""
        async with self._lock:
            return await asyncio.to_thread(self._native_lib.open_board)
    
    async def _configure_axes(self) -> None:
        """全軸の設定を適用"""
        for axis in range(self.axis_count):
            config = self._axis_configs[axis]
            if config.motor_type == MotorType.NONE:
                continue
            
            await self._configure_axis(axis, config)
            self._setup_motor_functions(axis, config.motor_type)
    
    async def _configure_axis(self, axis: int, config: AxisConfig) -> None:
        """単一軸を設定"""
        if self.simulation_mode:
            return
        
        # Set mode based on motor type
        wr2 = 0xA384
        if config.in_position == 0:
            wr2 &= 0xFF7F
        
        if config.motor_type == MotorType.IAI:
            wr3 = 0x0B40
        else:
            wr3 = 0x0F90
        
        await asyncio.to_thread(
            self._native_lib.set_mode, axis, 0, wr2, wr3, False)
        
        # Set speed
        await asyncio.to_thread(
            self._native_lib.set_drive_speed, axis, config.max_speed, False)
        
        # Set initial velocity
        sv = int(config.start_speed / config.pulse_length)
        await asyncio.to_thread(
            self._native_lib.set_initial_velocity, axis, sv, False)
        
        # Set acceleration
        await asyncio.to_thread(
            self._native_lib.set_acceleration, axis, config.max_accel, False)
        
        # Set deceleration
        await asyncio.to_thread(
            self._native_lib.set_deceleration, axis, config.max_decel, False)
        
        # Set soft limits
        limit_minus = self._mm_to_pulse(axis, config.limit_minus)
        limit_plus = self._mm_to_pulse(axis, config.limit_plus)
        await asyncio.to_thread(
            self._native_lib.set_soft_limit, axis, limit_minus, limit_plus)
        
        # Set logical coordinate to 0
        await asyncio.to_thread(
            self._native_lib.set_logical_coordinate, axis, 0)
        
        # Reset actuator (clear errors)
        # 参照: TEACHING/motion_control.py L399-401
        await self._write_axis_io(axis, AxisIO.OUT1, True)   # Reset ON
        await asyncio.sleep(0.1)
        await self._write_axis_io(axis, AxisIO.OUT1, False)  # Reset OFF
        await asyncio.sleep(0.1)
        
        # Servo ON
        # 参照: TEACHING/motion_control.py L403
        await self._write_axis_io(axis, AxisIO.OUT0, True)
        await asyncio.sleep(0.5)  # Wait for servo to stabilize
        self._axis_status[axis].is_servo_on = True
        
        logger.debug(f"Axis {axis} configured: motor_type={config.motor_type.name}")
    
    def _setup_motor_functions(self, axis: int, motor_type: MotorType) -> None:
        """モータータイプに応じた関数を設定"""
        if motor_type == MotorType.IAI:
            self._homing_functions[axis] = {
                'home_start': self._homing_start_iai,
                'home_check': self._homing_check_iai,
                'servo_on_off': self._servo_on_off_iai,
                'clear_on_off': self._clear_on_off_iai,
                'homing_on_off': self._homing_on_off_iai,
            }
        elif motor_type == MotorType.STEPPING:
            self._homing_functions[axis] = {
                'home_start': self._homing_start_step,
                'home_check': self._homing_check_step,
                'servo_on_off': self._servo_on_off_step,
                'clear_on_off': self._clear_on_off_step,
                'homing_on_off': self._homing_on_off_step,
            }
        elif motor_type == MotorType.ASTEP:
            self._homing_functions[axis] = {
                'home_start': self._homing_start_astep,
                'home_check': self._homing_check_astep,
                'servo_on_off': self._servo_on_off_astep,
                'clear_on_off': self._clear_on_off_astep,
                'homing_on_off': self._homing_on_off_astep,
            }
    
    # =========================================================================
    # Control Loop
    # =========================================================================
    
    async def _control_loop(self) -> None:
        """メイン制御ループ"""
        logger.info("Motion control loop started")
        
        while self._running:
            try:
                # I/O expander cycle
                await self._io_expander.io_cycle()
                
                # Update axis status
                for axis in range(self.axis_count):
                    if self._axis_configs[axis].motor_type != MotorType.NONE:
                        await self._update_axis_status(axis)
                
                await asyncio.sleep(0.01)  # 10ms cycle
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Control loop error: {e}")
                await asyncio.sleep(0.1)
        
        logger.info("Motion control loop stopped")
    
    async def _update_axis_status(self, axis: int) -> None:
        """軸ステータスを更新
        
        参照: TEACHING/motion_control.py L1095-1240 read_axis_io()
        レジスタRR0からBusyビット、RR2からAlarm/EMG、RR3からInPositionを読み取る
        """
        if self.simulation_mode:
            return
        
        try:
            # Get coordinate
            coord = await asyncio.to_thread(
                self._native_lib.get_logical_coordinate, axis)
            if coord is not None:
                config = self._axis_configs[axis]
                self._axis_status[axis].abs_coord = round(
                    coord * config.pulse_length, 2)
            
            # Read Register RR0 for busy/error status
            # 参照: TEACHING/motion_control.py L1106-1132
            reg0 = await asyncio.to_thread(
                self._native_lib.read_register, axis, NOVARegister.RR0)
            if reg0 is not None:
                status = self._axis_status[axis]
                # 軸ごとに異なるビット位置
                # 軸0(X): bit0, 軸1(Y): bit1, 軸2(Z): bit2, 軸3(U): bit3
                drv_bits = [NOVARegister.RR0_XDRV, NOVARegister.RR0_YDRV, 
                           NOVARegister.RR0_ZDRV, NOVARegister.RR0_UDRV]
                err_bits = [NOVARegister.RR0_XERR, NOVARegister.RR0_YERR,
                           NOVARegister.RR0_ZERR, NOVARegister.RR0_UERR]
                
                if axis < len(drv_bits):
                    status.is_busy = bool(reg0 & drv_bits[axis])
                    is_error = bool(reg0 & err_bits[axis])
                    if is_error:
                        status.is_alarm = True
            
            # Read Register RR2 for alarm/emergency
            reg2 = await asyncio.to_thread(
                self._native_lib.read_register, axis, NOVARegister.RR2)
            if reg2 is not None:
                status = self._axis_status[axis]
                # bit 10: Alarm, bit 20: Emergency
                status.is_alarm = status.is_alarm or bool(reg2 & (1 << 10))
                status.is_emergency = bool(reg2 & (1 << 20))
            
            # Read Register RR3 for in-position
            reg3 = await asyncio.to_thread(
                self._native_lib.read_register, axis, NOVARegister.RR3)
            if reg3 is not None:
                status = self._axis_status[axis]
                reg3_low = reg3 & 0xFFFF
                status.is_in_position = bool(reg3_low & NOVARegister.RR3_INPOS)
                status.is_origin_sensor = bool(reg3_low & NOVARegister.RR3_STOP1)
                
        except Exception as e:
            logger.error(f"Failed to update axis {axis} status: {e}")
    
    # =========================================================================
    # Coordinate Conversion
    # =========================================================================
    
    def _mm_to_pulse(self, axis: int, mm: float) -> int:
        """mm→パルス変換"""
        config = self._axis_configs[axis]
        return int((mm * 100) / (config.pulse_length * 100))
    
    def _pulse_to_mm(self, axis: int, pulse: int) -> float:
        """パルス→mm変換"""
        config = self._axis_configs[axis]
        return round(pulse * config.pulse_length, 2)
    
    def _speed_percent_to_pulse(self, axis: int, speed_percent: float) -> int:
        """速度%→パルス/sec変換"""
        config = self._axis_configs[axis]
        speed_percent = max(1.0, min(100.0, speed_percent))
        speed = int(config.max_speed * (speed_percent / 100.0))
        return int(speed / config.pulse_length)
    
    # =========================================================================
    # Motion Commands
    # =========================================================================
    
    async def move_absolute(
        self,
        axis: int,
        position_mm: float,
        speed_percent: float = 100.0
    ) -> bool:
        """
        絶対位置移動
        
        Args:
            axis: 軸番号
            position_mm: 目標位置 [mm]
            speed_percent: 速度 [%] (1-100)
            
        Returns:
            コマンド発行成功
        """
        if not self.is_ready:
            logger.warning("Controller not ready")
            return False
        
        target_pulse = self._mm_to_pulse(axis, position_mm)
        speed_pulse = self._speed_percent_to_pulse(axis, speed_percent)
        
        self._state = ControllerState.MOVING
        
        # シミュレーションモードでは即座に成功を返す
        if self.simulation_mode:
            logger.debug(f"[Simulation] Move absolute: axis={axis}, pos={position_mm}mm, speed={speed_percent}%")
            self._axis_status[axis].current_position = target_pulse
            self._axis_status[axis].is_moving = False
            self._state = ControllerState.READY
            return True
        
        async with self._lock:
            result = await asyncio.to_thread(
                self._native_lib.move_absolute, axis, target_pulse, speed_pulse)
        
        if result:
            logger.debug(f"Move absolute: axis={axis}, pos={position_mm}mm, speed={speed_percent}%")
        else:
            logger.error(f"Failed to move axis {axis}")
            self._state = ControllerState.ERROR
        
        return result
    
    async def move_relative(
        self,
        axis: int,
        distance_mm: float,
        speed_percent: float = 100.0
    ) -> bool:
        """
        相対位置移動
        
        Args:
            axis: 軸番号
            distance_mm: 移動距離 [mm]
            speed_percent: 速度 [%]
            
        Returns:
            コマンド発行成功
        """
        if not self.is_ready:
            return False
        
        distance_pulse = self._mm_to_pulse(axis, distance_mm)
        speed_pulse = self._speed_percent_to_pulse(axis, speed_percent)
        
        self._state = ControllerState.MOVING
        
        # シミュレーションモードでは即座に成功を返す
        if self.simulation_mode:
            logger.debug(f"[Simulation] Move relative: axis={axis}, dist={distance_mm}mm")
            current = self._axis_status[axis].current_position
            self._axis_status[axis].current_position = current + distance_pulse
            self._axis_status[axis].is_moving = False
            self._state = ControllerState.READY
            return True
        
        async with self._lock:
            result = await asyncio.to_thread(
                self._native_lib.move_relative, axis, distance_pulse, speed_pulse, False)
        
        if result:
            logger.debug(f"Move relative: axis={axis}, dist={distance_mm}mm")
        
        return result
    
    async def move_jog(
        self,
        axis: int,
        direction_ccw: bool,
        speed_percent: float = 10.0
    ) -> bool:
        """
        JOG移動（連続移動）
        
        Args:
            axis: 軸番号
            direction_ccw: CCW方向
            speed_percent: 速度 [%]
            
        Returns:
            コマンド発行成功
        """
        if not self.is_ready:
            return False
        
        speed_pulse = self._speed_percent_to_pulse(axis, speed_percent)
        
        self._state = ControllerState.MOVING
        
        async with self._lock:
            result = await asyncio.to_thread(
                self._native_lib.move_jog, axis, direction_ccw, speed_pulse)
        
        return result
    
    async def stop(self, axis: int) -> bool:
        """
        即時停止
        
        Args:
            axis: 軸番号
            
        Returns:
            コマンド発行成功
        """
        async with self._lock:
            result = await asyncio.to_thread(
                self._native_lib.stop, axis)
        
        if result:
            self._state = ControllerState.STOPPED
            logger.debug(f"Axis {axis} stopped")
        
        return result
    
    async def stop_all(self) -> bool:
        """全軸停止"""
        results = []
        for axis in range(self.axis_count):
            if self._axis_configs[axis].motor_type != MotorType.NONE:
                results.append(await self.stop(axis))
        return all(results)
    
    async def deceleration_stop(self, axis: int) -> bool:
        """
        減速停止
        
        Args:
            axis: 軸番号
            
        Returns:
            コマンド発行成功
        """
        async with self._lock:
            result = await asyncio.to_thread(
                self._native_lib.deceleration_stop, axis)
        
        if result:
            self._state = ControllerState.STOPPED
        
        return result
    
    async def wait_motion_complete(
        self,
        axis: int,
        timeout: float = 30.0
    ) -> bool:
        """
        動作完了を待機
        
        Args:
            axis: 軸番号
            timeout: タイムアウト [秒]
            
        Returns:
            完了した場合True、タイムアウトの場合False
        """
        # シミュレーションモードでは即座に完了
        if self.simulation_mode:
            self._state = ControllerState.READY
            return True
        
        start_time = asyncio.get_event_loop().time()
        
        while (asyncio.get_event_loop().time() - start_time) < timeout:
            status = self._axis_status.get(axis)
            if status and status.is_in_position and not status.is_busy:
                self._state = ControllerState.READY
                return True
            await asyncio.sleep(0.05)
        
        logger.warning(f"Motion timeout: axis={axis}")
        return False
    
    # =========================================================================
    # Coordinate Commands
    # =========================================================================
    
    async def get_position(self, axis: int) -> Optional[float]:
        """
        現在位置を取得 [mm]
        
        Args:
            axis: 軸番号
            
        Returns:
            現在位置 [mm]
        """
        status = self._axis_status.get(axis)
        return status.abs_coord if status else None
    
    async def get_all_positions(self) -> Dict[int, float]:
        """全軸の現在位置を取得"""
        positions = {}
        for axis in range(self.axis_count):
            if self._axis_configs[axis].motor_type != MotorType.NONE:
                pos = await self.get_position(axis)
                if pos is not None:
                    positions[axis] = pos
        return positions
    
    async def set_position(self, axis: int, position_mm: float) -> bool:
        """
        現在位置を設定（座標リセット）
        
        Args:
            axis: 軸番号
            position_mm: 設定する位置 [mm]
            
        Returns:
            成功した場合True
        """
        pulse = self._mm_to_pulse(axis, position_mm)
        
        async with self._lock:
            return await asyncio.to_thread(
                self._native_lib.set_logical_coordinate, axis, pulse)
    
    # =========================================================================
    # Homing
    # =========================================================================
    
    async def home_axis(self, axis: int) -> bool:
        """
        単一軸の原点復帰
        
        Args:
            axis: 軸番号
            
        Returns:
            成功した場合True
        """
        if not self.is_ready:
            return False
        
        config = self._axis_configs.get(axis)
        if not config or config.motor_type == MotorType.NONE:
            return False
        
        self._state = ControllerState.HOMING
        self._axis_status[axis].is_homing = True
        self._axis_status[axis].is_home_completed = False
        
        try:
            funcs = self._homing_functions.get(axis)
            if not funcs:
                return False
            
            # Execute homing sequence
            await funcs['home_start'](axis)
            
            # ホーミング開始後、最初にBusyになるのを待つ (最大2秒)
            busy_wait_start = asyncio.get_event_loop().time()
            while (asyncio.get_event_loop().time() - busy_wait_start) < 2.0:
                await self._update_axis_status(axis)
                if self._axis_status[axis].is_busy:
                    logger.debug(f"Axis {axis} is now busy (homing started)")
                    break
                await asyncio.sleep(0.05)
            else:
                # Busyにならなかった場合でも続行（既に完了の可能性）
                logger.warning(f"Axis {axis} did not become busy, may have completed instantly")
            
            # Wait for homing to complete (Busyがfalseになるまで待つ)
            timeout = 60.0  # 60 second timeout
            start_time = asyncio.get_event_loop().time()
            
            while (asyncio.get_event_loop().time() - start_time) < timeout:
                if await funcs['home_check'](axis):
                    break
                await asyncio.sleep(0.1)
            else:
                logger.error(f"Homing timeout: axis={axis}")
                self._axis_status[axis].is_homing_error = True
                return False
            
            # Set position to 0 after homing
            await self.set_position(axis, 0.0)
            
            self._axis_status[axis].is_homing = False
            self._axis_status[axis].is_home_completed = True
            self._state = ControllerState.READY
            
            logger.info(f"Axis {axis} homing completed")
            return True
            
        except Exception as e:
            logger.error(f"Homing error: axis={axis}, error={e}")
            self._axis_status[axis].is_homing_error = True
            self._state = ControllerState.ERROR
            return False
    
    async def home_all_axes(self) -> bool:
        """全軸の原点復帰"""
        results = []
        for axis in range(self.axis_count):
            if self._axis_configs[axis].motor_type != MotorType.NONE:
                results.append(await self.home_axis(axis))
        return all(results)
    
    # =========================================================================
    # Motor Type Specific Functions - IAI
    # =========================================================================
    
    async def _homing_start_iai(self, axis: int) -> None:
        """IAI原点復帰開始"""
        await self._homing_on_off_iai(axis, True)
        await asyncio.sleep(0.1)
        await self._homing_on_off_iai(axis, False)
    
    async def _homing_check_iai(self, axis: int) -> bool:
        """IAI原点復帰チェック"""
        if self.simulation_mode:
            return True
        reg = await asyncio.to_thread(
            self._native_lib.read_register, axis, NOVARegister.RR3)
        if reg is not None:
            reg3_0 = reg & 0xFFFF
            return (reg3_0 & 0x0002) == 0  # STOP2 bit
        return False
    
    async def _servo_on_off_iai(self, axis: int, on: bool) -> None:
        """IAIサーボON/OFF"""
        await self._write_axis_io(axis, AxisIO.OUT0, on)
        self._axis_status[axis].is_servo_on = on
    
    async def _clear_on_off_iai(self, axis: int, on: bool) -> None:
        """IAIクリアON/OFF"""
        await self._write_axis_io(axis, AxisIO.OUT1, on)
    
    async def _homing_on_off_iai(self, axis: int, on: bool) -> None:
        """IAI原点復帰信号ON/OFF"""
        await self._write_axis_io(axis, AxisIO.OUT2, on)
    
    # =========================================================================
    # Motor Type Specific Functions - STEP
    # =========================================================================
    
    async def _homing_start_step(self, axis: int) -> None:
        """ステッピング原点復帰開始
        
        参照: TEACHING/motion_control.py L1484-1489 homing_move_start_STEP
        
        注意: origin_sensor == 0 (OFF) の場合、物理的なホーミングは行わず、
        パラメータ設定のみ行います。オートオリジン(cw_mc_org)は
        origin_sensor == 2 (AUTO) の場合のみ使用されます。
        """
        config = self._axis_configs[axis]
        
        # origin_sensor == AUTO(2) の場合のみオートオリジンを実行
        if config.origin_sensor == 2:  # AUTO
            await self._nova_homing_start_step(axis)
        else:
            # パラメータ設定のみ（物理的なホーミングなし）
            await self._homing_parameter_set(axis)
            logger.info(f"Axis {axis}: OriginSensor=OFF, skipping physical homing")
    
    async def _nova_homing_start_step(self, axis: int) -> None:
        """ステッピング NOVAオートホーミング開始
        
        参照: TEACHING/motion_control.py L1491-1540 nova_homing_move_start_STEP
        origin_sensor == AUTO の場合のみ呼ばれる
        """
        config = self._axis_configs[axis]
        
        # 1. ドライブ速度を設定
        origin_speed_pulse = self._mm_to_pulse(axis, config.origin_speed)
        await asyncio.to_thread(
            self._native_lib.set_drive_speed, axis, origin_speed_pulse, False)
        
        # 2. ソフトリミット解除（ホーミング中は0に設定）
        await asyncio.to_thread(
            self._native_lib.set_soft_limit, axis, 0, 0)
        
        # 3. オートホーミングモードを設定
        # origin_dir == 0 → orgn_dir = 0x02 (CW方向)
        # origin_dir == 1 → orgn_dir = 0x00 (CCW方向)
        orgn_dir = 0x02 if config.origin_dir == 0 else 0x00
        h1m = 0x315 | orgn_dir
        h2m = 0x686
        await asyncio.to_thread(
            self._native_lib.set_origin_mode, axis, h1m, h2m, False)
        
        # 4. オートオリジンコマンド発行
        hv = origin_speed_pulse - 1
        dv = origin_speed_pulse
        result = await asyncio.to_thread(
            self._native_lib.auto_origin, axis, hv, dv)
        
        if not result:
            logger.error(f"STEP auto origin failed: axis={axis}")
    
    async def _homing_parameter_set(self, axis: int) -> None:
        """ホーミングパラメータ設定
        
        参照: TEACHING/motion_control.py L1315-1352 homing_parameter_set
        物理的なホーミングなしで座標を0にリセットする
        """
        config = self._axis_configs[axis]
        
        # 1. ドライブ速度を設定
        await asyncio.to_thread(
            self._native_lib.set_drive_speed, axis, config.max_speed, False)
        
        # 2. 論理座標を0に設定
        await asyncio.to_thread(
            self._native_lib.set_logical_coordinate, axis, 0)
        
        # 3. 相対座標を0に設定
        await asyncio.to_thread(
            self._native_lib.set_relative_coordinate, axis, 0)
        
        # 4. ソフトリミット設定
        limit_minus = self._mm_to_pulse(axis, config.limit_minus)
        limit_plus = self._mm_to_pulse(axis, config.limit_plus)
        await asyncio.to_thread(
            self._native_lib.set_soft_limit, axis, limit_minus, limit_plus)
    
    async def _homing_check_step(self, axis: int) -> bool:
        """ステッピング原点復帰チェック"""
        if self.simulation_mode:
            return True
        status = self._axis_status.get(axis)
        return status and not status.is_busy if status else False
    
    async def _servo_on_off_step(self, axis: int, on: bool) -> None:
        """ステッピングサーボON/OFF"""
        await self._write_axis_io(axis, AxisIO.OUT0, on)
        self._axis_status[axis].is_servo_on = on
    
    async def _clear_on_off_step(self, axis: int, on: bool) -> None:
        """ステッピングクリアON/OFF"""
        await self._write_axis_io(axis, AxisIO.OUT1, on)
    
    async def _homing_on_off_step(self, axis: int, on: bool) -> None:
        """ステッピング原点復帰信号ON/OFF"""
        await self._write_axis_io(axis, AxisIO.OUT2, on)
    
    # =========================================================================
    # Motor Type Specific Functions - aSTEP
    # =========================================================================
    
    async def _homing_start_astep(self, axis: int) -> None:
        """aSTEP原点復帰開始
        
        参照: TEACHING/motion_control.py L1569-1609 nova_homing_move_start_aSTEP
        
        注意: origin_sensor == 0 (OFF) の場合、物理的なホーミングは行わず、
        パラメータ設定のみ行います。
        """
        config = self._axis_configs[axis]
        
        # origin_sensor == AUTO(2) の場合のみオートオリジンを実行
        if config.origin_sensor == 2:  # AUTO
            await self._nova_homing_start_astep(axis)
        else:
            # パラメータ設定のみ（物理的なホーミングなし）
            await self._homing_parameter_set(axis)
            logger.info(f"Axis {axis} (aSTEP): OriginSensor=OFF, skipping physical homing")
    
    async def _nova_homing_start_astep(self, axis: int) -> None:
        """aSTEP NOVAオートホーミング開始
        
        参照: TEACHING/motion_control.py L1569-1609 nova_homing_move_start_aSTEP
        origin_sensor == AUTO の場合のみ呼ばれる
        """
        config = self._axis_configs[axis]
        
        # 1. ドライブ速度を設定
        origin_speed_pulse = self._mm_to_pulse(axis, config.origin_speed)
        await asyncio.to_thread(
            self._native_lib.set_drive_speed, axis, origin_speed_pulse, False)
        
        # 2. オートホーミングモードを設定
        # orgn_dir: 0x02 for CW, 0x00 for CCW
        orgn_dir = 0x02 if config.origin_dir == 0 else 0x00
        h1m = 0x315 | orgn_dir
        h2m = 0x686
        await asyncio.to_thread(
            self._native_lib.set_origin_mode, axis, h1m, h2m, False)
        
        # 3. オートオリジンコマンド発行
        hv = origin_speed_pulse - 1
        dv = origin_speed_pulse
        result = await asyncio.to_thread(
            self._native_lib.auto_origin, axis, hv, dv)
        
        if not result:
            logger.error(f"aSTEP auto origin failed: axis={axis}")
    
    async def _homing_check_astep(self, axis: int) -> bool:
        """aSTEP原点復帰チェック
        
        参照: TEACHING/motion_control.py L1611 nova_homing_move_check_aSTEP
        is_busy = False のとき完了
        """
        if self.simulation_mode:
            return True
        
        # ステータスを更新してからチェック
        await self._update_axis_status(axis)
        status = self._axis_status.get(axis)
        
        if status is None:
            return False
        
        # Busyでなければ完了
        # ただし、ホーミング開始直後はまだBusyになっていない可能性があるので
        # 少し待ってからチェックする
        return not status.is_busy
    
    async def _servo_on_off_astep(self, axis: int, on: bool) -> None:
        """aSTEPサーボON/OFF"""
        await self._write_axis_io(axis, AxisIO.OUT0, on)
        self._axis_status[axis].is_servo_on = on
    
    async def _clear_on_off_astep(self, axis: int, on: bool) -> None:
        """aSTEPクリアON/OFF"""
        await self._write_axis_io(axis, AxisIO.OUT1, on)
    
    async def _homing_on_off_astep(self, axis: int, on: bool) -> None:
        """aSTEP原点復帰信号ON/OFF"""
        await self._write_axis_io(axis, AxisIO.OUT2, on)
    
    # =========================================================================
    # Axis I/O
    # =========================================================================
    
    async def _write_axis_io(self, axis: int, io_no: AxisIO, on: bool) -> bool:
        """軸I/Oに書き込み"""
        if self.simulation_mode:
            return True
        
        async with self._lock:
            return await asyncio.to_thread(
                self._native_lib.set_general_output_bit, axis, io_no, on)
    
    async def servo_on(self, axis: int) -> bool:
        """サーボON"""
        funcs = self._homing_functions.get(axis)
        if funcs and 'servo_on_off' in funcs:
            await funcs['servo_on_off'](axis, True)
            return True
        return False
    
    async def servo_off(self, axis: int) -> bool:
        """サーボOFF"""
        funcs = self._homing_functions.get(axis)
        if funcs and 'servo_on_off' in funcs:
            await funcs['servo_on_off'](axis, False)
            return True
        return False
    
    # =========================================================================
    # Shutdown
    # =========================================================================
    
    async def shutdown(self) -> None:
        """コントローラをシャットダウン"""
        logger.info("Shutting down motion controller...")
        
        # Stop control loop
        self._running = False
        if self._control_loop_task:
            self._control_loop_task.cancel()
            try:
                await self._control_loop_task
            except asyncio.CancelledError:
                pass
        
        # Stop all axes
        if self._initialized:
            await self.stop_all()
            
            # Turn off all servos
            for axis in range(self.axis_count):
                if self._axis_configs[axis].motor_type != MotorType.NONE:
                    await self.servo_off(axis)
        
        # Cleanup pigpio
        cleanup_pigpio()
        
        self._initialized = False
        self._state = ControllerState.UNINITIALIZED
        
        logger.info("Motion controller shutdown complete")
