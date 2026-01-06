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

try:
    import RPi.GPIO as GPIO
    HAS_GPIO = True
except ImportError:
    HAS_GPIO = False
    GPIO = None

try:
    import smbus
    HAS_SMBUS = True
except ImportError:
    HAS_SMBUS = False
    smbus = None

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
    """I/Oエキスパンダ設定"""
    i2c_bus: int = 3
    input_address: int = 0x21
    output_address: int = 0x24
    board_count: int = 4
    board_bits: int = 16


# =============================================================================
# Native Library Interface
# =============================================================================

class NativeLibrary:
    """
    libcsms_splebo_n.so ネイティブライブラリのctypesラッパー
    
    NOVAモーションコントローラボードへの低レベルアクセスを提供
    """
    
    def __init__(self, library_path: str = "./libcsms_splebo_n.so"):
        self.library_path = library_path
        self._lib: Optional[ctypes.CDLL] = None
        self._loaded = False
    
    def load(self) -> bool:
        """ライブラリをロード"""
        try:
            self._lib = ctypes.cdll.LoadLibrary(self.library_path)
            self._setup_function_signatures()
            self._loaded = True
            logger.info(f"Native library loaded: {self.library_path}")
            return True
        except OSError as e:
            logger.error(f"Failed to load native library: {e}")
            self._loaded = False
            return False
    
    def _setup_function_signatures(self):
        """関数シグネチャの設定"""
        if not self._lib:
            return
        
        # Board Open
        self._lib.cw_mc_open.restype = c_bool
        
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
        self._lib.cw_mc_set_return_org.argtypes = (c_int, c_int, c_int, c_bool)
        self._lib.cw_mc_set_return_org.restype = c_bool
        
        # Set I/O Signal
        self._lib.cw_mc_set_pio.argtypes = (c_int, c_int, c_int, c_bool)
        self._lib.cw_mc_set_pio.restype = c_bool
        
        # Set Input Signal Filter
        self._lib.cw_mc_set_input_filter.argtypes = (c_int, c_int, c_bool)
        self._lib.cw_mc_set_input_filter.restype = c_bool
        
        # Auto Origin
        self._lib.cw_mc_auto_home.argtypes = (c_int, c_int, c_int)
        self._lib.cw_mc_auto_home.restype = c_bool
        
        # Set Soft Limit
        self._lib.cw_mc_set_soft_limit.argtypes = (c_int, c_int, c_int)
        self._lib.cw_mc_set_soft_limit.restype = c_bool
        
        # Move Absolute
        self._lib.cw_mc_abs.argtypes = (c_int, c_int, c_int)
        self._lib.cw_mc_abs.restype = c_bool
        
        # Move Relative
        self._lib.cw_mc_rel.argtypes = (c_int, c_int, c_int, c_bool)
        self._lib.cw_mc_rel.restype = c_bool
        
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
        
        # Get Relative Coordinate
        self._lib.cw_mc_get_real_cie.argtypes = (c_int, POINTER(c_int))
        self._lib.cw_mc_get_real_cie.restype = c_bool
        
        # Set Logical Coordinate
        self._lib.cw_mc_set_logic_cie.argtypes = (c_int, c_int)
        self._lib.cw_mc_set_logic_cie.restype = c_bool
        
        # Set Relative Coordinate
        self._lib.cw_mc_set_real_cie.argtypes = (c_int, c_int)
        self._lib.cw_mc_set_real_cie.restype = c_bool
        
        # Get General I/O
        self._lib.cw_mc_get_gen_io.argtypes = (c_int, POINTER(c_int))
        self._lib.cw_mc_get_gen_io.restype = c_bool
        
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
    
    def set_soft_limit(self, axis: int, limit_minus: int, limit_plus: int) -> bool:
        """ソフトリミットを設定"""
        if not self._lib:
            return False
        return bool(self._lib.cw_mc_set_soft_limit(axis, limit_minus, limit_plus))
    
    def move_absolute(self, axis: int, target_position: int, speed: int) -> bool:
        """絶対位置移動"""
        if not self._lib:
            return False
        return bool(self._lib.cw_mc_abs(axis, target_position, speed))
    
    def move_relative(self, axis: int, distance: int, speed: int, abs_mode: bool = False) -> bool:
        """相対位置移動"""
        if not self._lib:
            return False
        return bool(self._lib.cw_mc_rel(axis, distance, speed, abs_mode))
    
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
    
    def get_general_io(self, axis: int) -> Optional[int]:
        """汎用I/Oを取得"""
        if not self._lib:
            return None
        buffer = (c_int * 16)()
        ptr = cast(buffer, POINTER(c_int))
        if self._lib.cw_mc_get_gen_io(axis, ptr):
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
    
    def __init__(self, config: Optional[IOExpanderConfig] = None):
        self.config = config or IOExpanderConfig()
        self._smbus: Optional[Any] = None
        self._initialized = False
        self._read_data: List[int] = [0] * self.config.board_count
        self._write_data: List[int] = [0] * self.config.board_count
        self._lock = asyncio.Lock()
    
    async def initialize(self) -> bool:
        """I/Oエキスパンダを初期化"""
        if not HAS_SMBUS:
            logger.warning("smbus not available - I/O expander will be simulated")
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
        self._io_expander = I2CIOExpander()
        
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
            
            # Start control loop
            self._running = True
            self._control_loop_task = asyncio.create_task(self._control_loop())
            
            # Wait a bit for the control loop to start
            await asyncio.sleep(0.1)
            
            # Open motion board
            if not self.simulation_mode:
                if not await self._open_board():
                    logger.error("Failed to open motion board")
                    self._state = ControllerState.ERROR
                    return False
            
            # Configure axes
            await self._configure_axes()
            
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
        """GPIO初期化"""
        if not HAS_GPIO:
            logger.warning("RPi.GPIO not available")
            return
        
        try:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            
            # Power pin
            GPIO.setup(GPIOPin.NOVA_POWER, GPIO.OUT, initial=GPIO.HIGH)
            # Reset pin
            GPIO.setup(GPIOPin.NOVA_RESET, GPIO.OUT, initial=GPIO.LOW)
            
            # Power on sequence
            GPIO.output(GPIOPin.NOVA_POWER, True)
            await asyncio.sleep(0.1)
            GPIO.output(GPIOPin.NOVA_RESET, False)
            await asyncio.sleep(0.1)
            
            self._gpio_initialized = True
            logger.info("GPIO initialized")
            
        except Exception as e:
            logger.error(f"GPIO initialization failed: {e}")
    
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
        """軸ステータスを更新"""
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
            
            # Get I/O status
            io_data = await asyncio.to_thread(
                self._native_lib.get_general_io, axis)
            if io_data is not None:
                status = self._axis_status[axis]
                # Parse I/O bits (motor-type dependent)
                # This is a simplified version
                status.is_busy = bool(io_data & 0x01)
                status.is_alarm = bool(io_data & 0x02)
                status.is_in_position = bool(io_data & 0x04)
                
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
            
            # Wait for homing to complete
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
        """ステッピング原点復帰開始"""
        pass  # No special start sequence
    
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
        """aSTEP原点復帰開始"""
        pass
    
    async def _homing_check_astep(self, axis: int) -> bool:
        """aSTEP原点復帰チェック"""
        if self.simulation_mode:
            return True
        status = self._axis_status.get(axis)
        return status and not status.is_busy if status else False
    
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
        
        # Cleanup GPIO
        if self._gpio_initialized and HAS_GPIO:
            GPIO.cleanup()
        
        self._initialized = False
        self._state = ControllerState.UNINITIALIZED
        
        logger.info("Motion controller shutdown complete")
