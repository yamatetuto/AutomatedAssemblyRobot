# *********************************************************************#
# File Name : robot_manager.py
# Explanation : Robot Manager - Unified Robot Control Interface
# Project : AutomatedAssemblyRobot - SPLEBO-N Integration
# ----------------------------------------------------------------------
# Based on : TEACHING/splebo_n.py (2246 lines)
# History :
#           ver0.0.1 2026.1.7 New Create - Unified control interface
# *********************************************************************#

"""
RobotManager - ロボット統合管理クラス

SPLEBO-Nテーブルロボットの全機能を統合的に制御するための
高レベルインターフェースを提供します。

参照元ファイル:
    - TEACHING/splebo_n.py: メイン制御ロジック、状態管理、初期化処理
    - TEACHING/sample.py: シーケンス実行パターン

参照元の主要クラス/関数 (行番号はsplebo_n.pyを参照):
    - initialize() (L1400-1600):
        - GPIO初期化 → RobotManager._initialize_gpio()
        - motion_class初期化 → RobotManager.motion.initialize()
        - can初期化 → RobotManager.can.initialize()
    
    - axis_move_class (L700-800):
        - move_axis() → RobotManager.move_axis()
        - move_to_position() → RobotManager.move_to_position()
    
    - homing_class (L240-300):
        - init() → RobotManager.home_all()内で初期化
    
    - io_ex_input_class, io_ex_output_class (L430-700):
        - → RobotManager.io (IOExpander経由)
    
    - posi_data_class (L800-900):
        - → RobotManager.positions (PositionManager経由)

    - sample.py (TEACHING/sample.py):
        - main_sequence() → RobotManagerでのシーケンス実行パターンの参考

移植時の変更点:
    - グローバル変数 → RobotManagerインスタンスに集約
    - 各クラスの直接参照 → RobotManager経由のアクセス
    - コールバック → EventEmitterによるイベントシステム
    - threading → asyncio
    - コンテキストマネージャ対応 (async with)

主な機能:
    - モーション制御（MotionController）
    - CAN通信（CANController）
    - I/O制御（IOExpander）
    - ポジション管理（PositionManager）
    - シーケンス実行
    - 状態監視・通知

使用例:
    robot = RobotManager()
    await robot.initialize()
    
    # ティーチングポイントへ移動
    await robot.move_to_position("P001")
    
    # ホーミング
    await robot.home_all()
    
    # シャットダウン
    await robot.shutdown()
"""

import asyncio
import logging
from dataclasses import dataclass, field
from enum import IntEnum
import os
from typing import Optional, Dict, List, Callable, Any, Tuple
from pathlib import Path
import json
from datetime import datetime

from .constants import (
    Axis, AxisMask, InputPort, OutputPort, 
    RobotState, ErrorCode, GPIOPin
)
from .motion_controller import (
    MotionController, MotorType, AxisConfig, AxisStatus,
    ControllerState
)
from .can_controller import CANController
from .io_expander import IOExpander
from .position_manager import PositionManager, Position

logger = logging.getLogger(__name__)


# =============================================================================
# Enums and Constants
# =============================================================================

class RobotMode(IntEnum):
    """ロボット動作モード"""
    MANUAL = 0      # 手動モード
    AUTO = 1        # 自動モード
    TEACHING = 2    # ティーチングモード
    MAINTENANCE = 3 # メンテナンスモード


class SafetyState(IntEnum):
    """安全状態"""
    SAFE = 0
    DOOR_OPEN = 1
    EMERGENCY_STOP = 2
    ALARM = 3


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class RobotConfig:
    """ロボット設定"""
    # Library path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    motion_lib_path: str = os.path.join(current_dir, "libcsms_splebo_n.so")
    # motion_lib_path: str = "./libcsms_splebo_n.so"
    
    # CAN settings
    can_spi_bus: int = 0
    can_spi_device: int = 0
    can_speed_hz: int = 10000000
    can_cs_pin: int = GPIOPin.CAN_CS
    
    # Axes
    axis_count: int = 8
    enabled_axes: List[int] = field(default_factory=lambda: [0, 1, 2, 3])
    
    # Paths
    data_dir: str = "data/robot"
    position_file: str = "positions.json"
    sequences_file: str = "sequences.json"
    config_file: str = "config.json"
    
    # Safety
    enable_safety_checks: bool = True
    emergency_decel_time: float = 0.5  # seconds
    
    # Simulation
    simulation_mode: bool = False


@dataclass
class RobotStatus:
    """ロボット状態"""
    state: RobotState = RobotState.INITIALIZING
    mode: RobotMode = RobotMode.MANUAL
    safety_state: SafetyState = SafetyState.SAFE
    
    is_initialized: bool = False
    is_homing_complete: bool = False
    is_moving: bool = False
    is_error: bool = False
    
    error_code: ErrorCode = ErrorCode.NONE
    error_message: str = ""
    
    current_position_name: str = ""
    current_sequence_name: str = ""
    current_sequence_step: int = 0
    
    # Axis positions (mm)
    axis_positions: Dict[int, float] = field(default_factory=dict)
    
    # Timestamps
    last_update: Optional[datetime] = None
    last_move: Optional[datetime] = None
    last_error: Optional[datetime] = None


@dataclass
class MoveCommand:
    """移動コマンド"""
    axis: int
    target_mm: float
    speed_percent: float = 100.0
    is_absolute: bool = True
    wait_complete: bool = True


# =============================================================================
# Event System
# =============================================================================

class RobotEventType(IntEnum):
    """ロボットイベントタイプ"""
    STATE_CHANGED = 0
    POSITION_REACHED = 1
    HOMING_COMPLETE = 2
    MOTION_COMPLETE = 3
    ERROR_OCCURRED = 4
    SAFETY_TRIGGERED = 5
    IO_CHANGED = 6
    SEQUENCE_STARTED = 7
    SEQUENCE_COMPLETED = 8
    SEQUENCE_STEP = 9


@dataclass
class RobotEvent:
    """ロボットイベント"""
    event_type: RobotEventType
    timestamp: datetime
    data: Dict[str, Any] = field(default_factory=dict)


class EventEmitter:
    """イベントエミッタ"""
    
    def __init__(self):
        self._handlers: Dict[RobotEventType, List[Callable]] = {}
    
    def on(self, event_type: RobotEventType, handler: Callable) -> None:
        """イベントハンドラを登録"""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
    
    def off(self, event_type: RobotEventType, handler: Callable) -> None:
        """イベントハンドラを解除"""
        if event_type in self._handlers:
            self._handlers[event_type].remove(handler)
    
    async def emit(self, event: RobotEvent) -> None:
        """イベントを発行"""
        handlers = self._handlers.get(event.event_type, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.error(f"Event handler error: {e}")


# =============================================================================
# Robot Manager
# =============================================================================

class RobotManager:
    """
    ロボット統合管理クラス
    
    SPLEBO-Nテーブルロボットの全機能を統合的に制御します。
    
    Attributes:
        motion: MotionController - モーション制御
        can: CANController - CAN通信制御
        io: IOExpander - I/O制御
        positions: PositionManager - ポジション管理
        status: RobotStatus - 現在の状態
        events: EventEmitter - イベント発行
    
    使用例:
        robot = RobotManager(config)
        await robot.initialize()
        
        # イベントハンドラ登録
        robot.events.on(RobotEventType.MOTION_COMPLETE, on_motion_complete)
        
        # 移動
        await robot.move_axis(Axis.X, 100.0, speed_percent=50)
        await robot.wait_motion_complete()
        
        # ポジションへ移動
        await robot.move_to_position("P001")
        
        # シャットダウン
        await robot.shutdown()
    """
    
    def __init__(self, config: Optional[RobotConfig] = None):
        """
        Args:
            config: ロボット設定（省略時はデフォルト）
        """
        self.config = config or RobotConfig()
        
        # Components
        self.motion: Optional[MotionController] = None
        self.can: Optional[CANController] = None
        self.io: Optional[IOExpander] = None
        self.positions: Optional[PositionManager] = None
        
        # State
        self.status = RobotStatus()
        self.events = EventEmitter()
        
        # Internal
        self._monitor_task: Optional[asyncio.Task] = None
        self._running = False
        self._lock = asyncio.Lock()
        
        # Axis configurations
        self._axis_configs: Dict[int, AxisConfig] = {}
    
    # =========================================================================
    # Initialization
    # =========================================================================
    
    async def initialize(self) -> bool:
        """
        ロボットを初期化
        
        Returns:
            成功した場合True
        """
        logger.info("Initializing robot manager...")
        self.status.state = RobotState.INITIALIZING
        
        try:
            # Load axis configurations
            await self._load_axis_configs()
            
            # Initialize motion controller
            self.motion = MotionController(
                library_path=self.config.motion_lib_path,
                simulation_mode=self.config.simulation_mode,
                axis_count=self.config.axis_count
            )
            
            # Apply axis configurations
            for axis, axis_config in self._axis_configs.items():
                self.motion.set_axis_config(axis, axis_config)
            
            # Initialize motion controller
            if not await self.motion.initialize():
                logger.error("Failed to initialize motion controller")
                self.status.is_error = True
                self.status.error_code = ErrorCode.INIT_FAILED
                self.status.error_message = "Motion controller initialization failed"
                return False
            
            # Initialize CAN controller
            self.can = CANController(
                spi_bus=self.config.can_spi_bus,
                spi_device=self.config.can_spi_device,
                gpio_cs_pin=self.config.can_cs_pin,
                simulation_mode=self.config.simulation_mode
            )
            
            if not await self.can.initialize():
                logger.error("Failed to initialize CAN controller")
                self.status.is_error = True
                self.status.error_code = ErrorCode.INIT_FAILED
                self.status.error_message = "CAN controller initialization failed"
                return False
            
            # Initialize I/O expander
            self.io = IOExpander(self.can, simulation_mode=self.config.simulation_mode)
            
            # Initialize position manager
            position_path = Path(self.config.data_dir) / self.config.position_file
            self.positions = PositionManager(str(position_path))
            await self.positions.load()
            
            # Start monitoring
            self._running = True
            self._monitor_task = asyncio.create_task(self._monitor_loop())
            
            # Update status
            self.status.is_initialized = True
            self.status.state = RobotState.IDLE
            self.status.last_update = datetime.now()
            
            # Emit event
            await self.events.emit(RobotEvent(
                event_type=RobotEventType.STATE_CHANGED,
                timestamp=datetime.now(),
                data={"state": RobotState.IDLE}
            ))
            
            logger.info("Robot manager initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Robot initialization failed: {e}")
            self.status.is_error = True
            self.status.error_code = ErrorCode.INIT_FAILED
            self.status.error_message = str(e)
            return False
    
    async def _load_axis_configs(self) -> None:
        """軸設定をロード"""
        config_path = Path(self.config.data_dir) / self.config.config_file
        
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    data = json.load(f)
                
                for axis_data in data.get('axes', []):
                    axis = axis_data.get('axis', 0)
                    self._axis_configs[axis] = AxisConfig(
                        motor_type=MotorType(axis_data.get('motor_type', 0)),
                        max_speed=axis_data.get('max_speed', 800),
                        start_speed=axis_data.get('start_speed', 200),
                        max_accel=axis_data.get('max_accel', 2940),
                        max_decel=axis_data.get('max_decel', 2940),
                        pulse_length=axis_data.get('pulse_length', 0.01),
                        limit_minus=axis_data.get('limit_minus', -0.5),
                        limit_plus=axis_data.get('limit_plus', 800.5),
                        in_position=axis_data.get('in_position', 1),
                        origin_speed=axis_data.get('origin_speed', 10.0),
                        origin_dir=axis_data.get('origin_dir', 0),
                        origin_offset=axis_data.get('origin_offset', 0.0),
                        offset_speed=axis_data.get('offset_speed', 10.0),
                        origin_sensor=axis_data.get('origin_sensor', 0),
                        origin_order=axis_data.get('origin_order', 2),
                    )
                    
                logger.info(f"Loaded axis configurations from {config_path}")
                
            except Exception as e:
                logger.warning(f"Failed to load axis config: {e}")
        
        # Set defaults for missing axes
        for axis in self.config.enabled_axes:
            if axis not in self._axis_configs:
                self._axis_configs[axis] = AxisConfig(motor_type=MotorType.IAI)
    
    # =========================================================================
    # Monitoring
    # =========================================================================
    
    async def _monitor_loop(self) -> None:
        """状態監視ループ"""
        logger.info("Robot monitor loop started")
        
        while self._running:
            try:
                await self._update_status()
                await self._check_safety()
                await asyncio.sleep(0.05)  # 50ms cycle
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Monitor loop error: {e}")
                await asyncio.sleep(0.1)
        
        logger.info("Robot monitor loop stopped")
    
    async def _update_status(self) -> None:
        """状態を更新"""
        if not self.motion:
            return
        
        # Update motion controller state
        motion_state = self.motion.state
        
        if motion_state == ControllerState.MOVING:
            self.status.is_moving = True
            self.status.state = RobotState.MOVING
        elif motion_state == ControllerState.HOMING:
            self.status.state = RobotState.HOMING
        elif motion_state == ControllerState.ERROR:
            self.status.is_error = True
            self.status.state = RobotState.ERROR
        elif motion_state == ControllerState.READY:
            self.status.is_moving = False
            if self.status.state == RobotState.MOVING:
                self.status.state = RobotState.IDLE
        
        # Update axis positions
        positions = await self.motion.get_all_positions()
        self.status.axis_positions = positions
        
        # Update timestamp
        self.status.last_update = datetime.now()
    
    async def _check_safety(self) -> None:
        """安全チェック"""
        if not self.config.enable_safety_checks:
            return
        
        if not self.io:
            return
        
        # Check emergency stop
        emg_active = await self.io.is_emergency_active()
        if emg_active:
            if self.status.safety_state != SafetyState.EMERGENCY_STOP:
                self.status.safety_state = SafetyState.EMERGENCY_STOP
                await self._handle_emergency_stop()
    
    async def _handle_emergency_stop(self) -> None:
        """非常停止処理"""
        logger.warning("Emergency stop triggered!")
        
        if self.motion:
            await self.motion.stop_all()
        
        self.status.state = RobotState.EMERGENCY_STOP
        
        await self.events.emit(RobotEvent(
            event_type=RobotEventType.SAFETY_TRIGGERED,
            timestamp=datetime.now(),
            data={"safety_state": SafetyState.EMERGENCY_STOP}
        ))
    
    # =========================================================================
    # Motion Commands
    # =========================================================================
    
    async def move_axis(
        self,
        axis: int,
        target_mm: float,
        speed_percent: float = 100.0,
        wait_complete: bool = True
    ) -> bool:
        """
        単一軸を移動
        
        Args:
            axis: 軸番号
            target_mm: 目標位置 [mm]
            speed_percent: 速度 [%]
            wait_complete: 完了を待つかどうか
            
        Returns:
            成功した場合True
        """
        if not self._can_move():
            return False
        
        async with self._lock:
            self.status.state = RobotState.MOVING
            self.status.is_moving = True
            self.status.last_move = datetime.now()
            
            result = await self.motion.move_absolute(axis, target_mm, speed_percent)
            
            if result and wait_complete:
                await self.motion.wait_motion_complete(axis)
                self.status.is_moving = False
                self.status.state = RobotState.IDLE
                
                await self.events.emit(RobotEvent(
                    event_type=RobotEventType.MOTION_COMPLETE,
                    timestamp=datetime.now(),
                    data={"axis": axis, "position": target_mm}
                ))
            
            return result
    
    async def move_axes(
        self,
        moves: List[MoveCommand],
        parallel: bool = True,
        wait_complete: bool = True
    ) -> bool:
        """
        複数軸を移動
        
        Args:
            moves: 移動コマンドリスト
            parallel: 並列実行するかどうか
            wait_complete: 完了を待つかどうか
            
        Returns:
            全て成功した場合True
        """
        if not self._can_move():
            return False
        
        async with self._lock:
            self.status.state = RobotState.MOVING
            self.status.is_moving = True
            
            if parallel:
                # Start all moves simultaneously
                tasks = []
                for move in moves:
                    if move.is_absolute:
                        task = self.motion.move_absolute(
                            move.axis, move.target_mm, move.speed_percent)
                    else:
                        task = self.motion.move_relative(
                            move.axis, move.target_mm, move.speed_percent)
                    tasks.append(task)
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                if wait_complete:
                    # Wait for all axes
                    wait_tasks = [
                        self.motion.wait_motion_complete(move.axis)
                        for move in moves
                    ]
                    await asyncio.gather(*wait_tasks)
                
                success = all(r is True for r in results)
                
            else:
                # Sequential execution
                success = True
                for move in moves:
                    if move.is_absolute:
                        result = await self.motion.move_absolute(
                            move.axis, move.target_mm, move.speed_percent)
                    else:
                        result = await self.motion.move_relative(
                            move.axis, move.target_mm, move.speed_percent)
                    
                    if not result:
                        success = False
                        break
                    
                    if wait_complete:
                        await self.motion.wait_motion_complete(move.axis)
            
            self.status.is_moving = False
            self.status.state = RobotState.IDLE
            
            if success:
                await self.events.emit(RobotEvent(
                    event_type=RobotEventType.MOTION_COMPLETE,
                    timestamp=datetime.now(),
                    data={"moves": len(moves)}
                ))
            
            return success
    
    async def move_to_position(
        self,
        position_name: str,
        speed_percent: float = 100.0,
        wait_complete: bool = True
    ) -> bool:
        """
        ティーチングポイントへ移動
        
        Args:
            position_name: ポジション名
            speed_percent: 速度 [%]
            wait_complete: 完了を待つかどうか
            
        Returns:
            成功した場合True
        """
        if not self.positions:
            logger.error("Position manager not initialized")
            return False
        
        position = self.positions.get_position(position_name)
        if not position:
            logger.error(f"Position not found: {position_name}")
            return False
        
        moves = []
        for axis, coord in position.coordinates.items():
            moves.append(MoveCommand(
                axis=axis,
                target_mm=coord,
                speed_percent=speed_percent,
                is_absolute=True,
                wait_complete=wait_complete
            ))
        
        result = await self.move_axes(moves, parallel=True, wait_complete=wait_complete)
        
        if result:
            self.status.current_position_name = position_name
            await self.events.emit(RobotEvent(
                event_type=RobotEventType.POSITION_REACHED,
                timestamp=datetime.now(),
                data={"position": position_name}
            ))
        
        return result
    
    async def jog(
        self,
        axis: int,
        direction_positive: bool,
        speed_percent: float = 10.0
    ) -> bool:
        """
        JOG移動開始
        
        Args:
            axis: 軸番号
            direction_positive: 正方向
            speed_percent: 速度 [%]
            
        Returns:
            成功した場合True
        """
        if not self._can_move():
            return False
        
        return await self.motion.move_jog(
            axis, not direction_positive, speed_percent)
    
    async def stop(self, axis: Optional[int] = None) -> bool:
        """
        移動停止
        
        Args:
            axis: 軸番号（省略時は全軸）
            
        Returns:
            成功した場合True
        """
        if not self.motion:
            return False
        
        if axis is not None:
            result = await self.motion.stop(axis)
        else:
            result = await self.motion.stop_all()
        
        self.status.is_moving = False
        self.status.state = RobotState.IDLE
        
        return result
    
    def _can_move(self) -> bool:
        """移動可能かチェック"""
        if not self.motion or not self.motion.is_ready:
            logger.warning("Motion controller not ready")
            return False
        
        if self.status.safety_state == SafetyState.EMERGENCY_STOP:
            logger.warning("Cannot move: Emergency stop active")
            return False
        
        return True
    
    # =========================================================================
    # Homing
    # =========================================================================
    
    async def home_axis(self, axis: int) -> bool:
        """
        単一軸を原点復帰
        
        Args:
            axis: 軸番号
            
        Returns:
            成功した場合True
        """
        if not self.motion:
            return False
        
        self.status.state = RobotState.HOMING
        
        result = await self.motion.home_axis(axis)
        
        if result:
            logger.info(f"Axis {axis} homing complete")
        
        self.status.state = RobotState.IDLE
        return result
    
    async def home_all(self) -> bool:
        """
        全軸を原点復帰
        
        Returns:
            成功した場合True
        """
        if not self.motion:
            return False
        
        self.status.state = RobotState.HOMING
        
        result = await self.motion.home_all_axes()
        
        if result:
            self.status.is_homing_complete = True
            await self.events.emit(RobotEvent(
                event_type=RobotEventType.HOMING_COMPLETE,
                timestamp=datetime.now(),
                data={}
            ))
        
        self.status.state = RobotState.IDLE
        return result
    
    # =========================================================================
    # Position Management
    # =========================================================================
    
    async def teach_position(
        self,
        name: str,
        comment: str = ""
    ) -> bool:
        """
        現在位置をティーチング
        
        Args:
            name: ポジション名
            comment: コメント
            
        Returns:
            成功した場合True
        """
        if not self.motion or not self.positions:
            return False
        
        # Get current positions
        coords = await self.motion.get_all_positions()
        
        # Create position
        position = Position(
            name=name,
            coordinates=coords,
            comment=comment
        )
        
        # Save
        self.positions.add_position(position)
        await self.positions.save()
        
        logger.info(f"Position taught: {name} = {coords}")
        return True
    
    async def delete_position(self, name: str) -> bool:
        """
        ポジションを削除
        
        Args:
            name: ポジション名
            
        Returns:
            成功した場合True
        """
        if not self.positions:
            return False
        
        result = self.positions.delete_position(name)
        if result:
            await self.positions.save()
        return result
    
    async def get_positions(self) -> List[Position]:
        """全ポジションを取得"""
        if not self.positions:
            return []
        return self.positions.get_all_positions()
    
    # =========================================================================
    # I/O Control
    # =========================================================================
    
    async def set_output(self, port: int, value: bool) -> bool:
        """
        出力ポートを設定
        
        Args:
            port: ポート番号
            value: 出力値
            
        Returns:
            成功した場合True
        """
        if not self.io:
            return False
        return await self.io.set_output(port, value)
    
    async def get_input(self, port: int) -> Optional[bool]:
        """
        入力ポートを読み取り
        
        Args:
            port: ポート番号
            
        Returns:
            入力値
        """
        if not self.io:
            return None
        return await self.io.get_input(port)
    
    async def buzzer_on(self, duration: float = 0.5) -> None:
        """ブザーを鳴らす"""
        if self.io:
            await self.io.buzzer_beep(duration)
    
    # =========================================================================
    # Mode Control
    # =========================================================================
    
    async def set_mode(self, mode: RobotMode) -> bool:
        """
        動作モードを設定
        
        Args:
            mode: 動作モード
            
        Returns:
            成功した場合True
        """
        if mode == RobotMode.AUTO and not self.status.is_homing_complete:
            logger.warning("Cannot switch to AUTO mode: Homing not complete")
            return False
        
        self.status.mode = mode
        logger.info(f"Mode changed to: {mode.name}")
        return True
    
    # =========================================================================
    # Status
    # =========================================================================
    
    def get_status(self) -> RobotStatus:
        """現在の状態を取得"""
        return self.status
    
    def get_position(self, axis: int) -> Optional[float]:
        """
        軸位置を取得
        
        Args:
            axis: 軸番号
            
        Returns:
            位置 [mm]
        """
        return self.status.axis_positions.get(axis)
    
    def get_all_positions(self) -> Dict[int, float]:
        """全軸位置を取得"""
        return self.status.axis_positions.copy()
    
    async def wait_motion_complete(self, timeout: float = 30.0) -> bool:
        """
        動作完了を待機
        
        Args:
            timeout: タイムアウト [秒]
            
        Returns:
            完了した場合True
        """
        start_time = asyncio.get_event_loop().time()
        
        while (asyncio.get_event_loop().time() - start_time) < timeout:
            if not self.status.is_moving:
                return True
            await asyncio.sleep(0.05)
        
        return False
    
    # =========================================================================
    # Error Handling
    # =========================================================================
    
    async def clear_error(self) -> bool:
        """
        エラーをクリア
        
        Returns:
            成功した場合True
        """
        if self.status.safety_state == SafetyState.EMERGENCY_STOP:
            logger.warning("Cannot clear error: Emergency stop still active")
            return False
        
        self.status.is_error = False
        self.status.error_code = ErrorCode.NONE
        self.status.error_message = ""
        self.status.state = RobotState.IDLE
        
        # Reset motion controller if needed
        if self.motion and self.motion.state == ControllerState.ERROR:
            # Re-initialize might be needed
            pass
        
        logger.info("Error cleared")
        return True
    
    async def reset(self) -> bool:
        """
        ロボットをリセット
        
        Returns:
            成功した場合True
        """
        logger.info("Resetting robot...")
        
        # Stop all motion
        if self.motion:
            await self.motion.stop_all()
        
        # Clear error
        await self.clear_error()
        
        # Reset homing flag
        self.status.is_homing_complete = False
        
        logger.info("Robot reset complete")
        return True
    
    # =========================================================================
    # Shutdown
    # =========================================================================
    
    async def shutdown(self) -> None:
        """ロボットをシャットダウン"""
        logger.info("Shutting down robot manager...")
        
        # Stop monitor
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        # Stop motion
        if self.motion:
            await self.motion.shutdown()
        
        # Stop CAN
        if self.can:
            await self.can.close()
        
        # Save positions
        if self.positions:
            await self.positions.save()
        
        self.status.is_initialized = False
        self.status.state = RobotState.SHUTDOWN
        
        logger.info("Robot manager shutdown complete")
    
    # =========================================================================
    # Context Manager
    # =========================================================================
    
    async def __aenter__(self) -> 'RobotManager':
        await self.initialize()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        await self.shutdown()


# =============================================================================
# Factory Function
# =============================================================================

def create_robot_manager(
    simulation_mode: bool = False,
    data_dir: str = "data/robot",
    **kwargs
) -> RobotManager:
    """
    RobotManagerインスタンスを作成
    
    Args:
        simulation_mode: シミュレーションモード
        data_dir: データディレクトリ
        **kwargs: その他のRobotConfig引数
        
    Returns:
        RobotManager インスタンス
    """
    config = RobotConfig(
        simulation_mode=simulation_mode,
        data_dir=data_dir,
        **kwargs
    )
    return RobotManager(config)
