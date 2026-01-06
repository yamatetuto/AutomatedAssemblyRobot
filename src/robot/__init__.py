"""
SPLEBO-N ロボット制御モジュール

TEACHING統合パッケージ - 非同期モーション制御

このモジュールは以下の主要コンポーネントを提供します:

- RobotManager: ロボット統合管理クラス（メインエントリーポイント）
- MotionController: モーション制御（libcsms_splebo_n.soラッパー）
- CANController: CAN通信制御
- IOExpander: I/O制御
- PositionManager: ティーチングポジション管理

使用例:
    from src.robot import RobotManager, create_robot_manager
    
    # コンテキストマネージャ使用
    async with RobotManager() as robot:
        await robot.home_all()
        await robot.move_to_position("P001")
    
    # 手動制御
    robot = create_robot_manager(simulation_mode=True)
    await robot.initialize()
    await robot.move_axis(0, 100.0, speed_percent=50)
    await robot.shutdown()
"""
from .constants import (
    Axis,
    AxisMask,
    InputPort,
    OutputPort,
    RobotState,
    ErrorCode,
    Led7Seg,
    NOVARegister,
    GPIOPin,
    CANConfig,
    MCP2515,
)

from .can_controller import CANController
from .io_expander import IOExpander
from .position_manager import PositionManager, Position

from .motion_controller import (
    MotionController,
    MotorType,
    AxisConfig,
    AxisStatus,
    ControllerState,
    MoveType,
    AxisIO,
)

from .robot_manager import (
    RobotManager,
    RobotConfig,
    RobotStatus,
    RobotMode,
    SafetyState,
    MoveCommand,
    RobotEventType,
    RobotEvent,
    create_robot_manager,
)

from .api import create_robot_router
from .websocket_handler import RobotWebSocketManager
from .sequence_manager import (
    SequenceManager,
    SequenceState,
    SequenceProgress,
    SequenceConfig,
    SequenceError,
    SequenceType,
)

__all__ = [
    # 定数
    "Axis",
    "AxisMask",
    "InputPort",
    "OutputPort",
    "RobotState",
    "ErrorCode",
    "Led7Seg",
    "NOVARegister",
    "GPIOPin",
    "CANConfig",
    "MCP2515",
    # モーション制御
    "MotionController",
    "MotorType",
    "AxisConfig",
    "AxisStatus",
    "ControllerState",
    "MoveType",
    "AxisIO",
    # CANコントローラ
    "CANController",
    # I/Oエキスパンダ
    "IOExpander",
    # ポジション管理
    "PositionManager",
    "Position",
    # ロボット管理（メインエントリーポイント）
    "RobotManager",
    "RobotConfig",
    "RobotStatus",
    "RobotMode",
    "SafetyState",
    "MoveCommand",
    "RobotEventType",
    "RobotEvent",
    "create_robot_manager",
    # API
    "create_robot_router",
    "RobotWebSocketManager",
    # シーケンス管理
    "SequenceManager",
    "SequenceState",
    "SequenceProgress",
    "SequenceConfig",
    "SequenceError",
    "SequenceType",
]
