# *********************************************************************#
# File Name : sequence_manager.py
# Explanation : Simplified Sequence Execution Manager for XYZ Control
# Project : AutomatedAssemblyRobot - SPLEBO-N Integration
# ----------------------------------------------------------------------
# Based on : TEACHING/sample.py (構造のみ参照)
# 
# 注記:
#   このバージョンはXYZ軸移動とI/O制御に特化した汎用シーケンスマネージャです。
#   TEACHING/sample.pyのねじ締め機能は本プロジェクトでは使用しないため削除。
#
# 変更点 (2026-01-07):
#   - ねじ締めシーケンス（ScrewPickup, ScrewTight）削除
#   - XYZ軸移動に特化したシンプルな構成に変更
#   - ポイント移動シーケンス追加
#   - カスタムシーケンスコールバック機構追加
#
# History :
#           ver0.0.1 2026.1.7 New Create - Async sequence manager
#           ver0.0.2 2026.1.7 Simplified for XYZ control only
# *********************************************************************#

"""
シーケンスマネージャ - XYZ軸移動・I/O制御シーケンスの管理

SPLEBO-Nロボットの自動運転シーケンスを管理します。
ティーチングポイントへの順次移動やカスタムシーケンスの実行をサポート。

主なシーケンス:
    1. ポイント移動シーケンス (ティーチングポイント順次移動)
    2. 原点復帰シーケンス
    3. カスタムシーケンス (ユーザー定義コールバック)

使用例:
    from src.robot.sequence_manager import SequenceManager
    
    seq_manager = SequenceManager(robot_manager)
    
    # ポイント移動シーケンス
    await seq_manager.run_point_sequence(["P001", "P002", "P003"])
    
    # カスタムシーケンス
    async def my_sequence(robot, step):
        if step == 1:
            await robot.move_axis(0, 100.0)
        elif step == 2:
            await robot.set_output(0, True)
    
    await seq_manager.run_custom_sequence(my_sequence, total_steps=2)
"""

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto
from typing import Optional, Dict, List, Callable, Any, Awaitable

from .robot_manager import RobotManager, RobotMode

logger = logging.getLogger(__name__)


# =============================================================================
# 状態定義
# =============================================================================

class SequenceState(Enum):
    """シーケンス全体状態"""
    IDLE = auto()           # 待機中
    RUNNING = auto()        # 実行中
    PAUSED = auto()         # 一時停止
    COMPLETED = auto()      # 完了
    ERROR = auto()          # エラー
    ABORTED = auto()        # 中断


class SequenceType(Enum):
    """シーケンスタイプ"""
    HOMING = auto()         # 原点復帰
    POINT_MOVE = auto()     # ポイント移動
    CUSTOM = auto()         # カスタム


class SequenceError(Enum):
    """シーケンスエラーコード"""
    NONE = 0
    MOVE_FAILED = 1         # 移動失敗
    POSITION_NOT_FOUND = 2  # ポジション未発見
    TIMEOUT = 3             # タイムアウト
    IO_ERROR = 4            # I/Oエラー
    ROBOT_ERROR = 5         # ロボットエラー
    CANCELLED = 6           # キャンセル
    UNKNOWN = 99            # 不明


# =============================================================================
# データクラス
# =============================================================================

@dataclass
class SequenceProgress:
    """シーケンス進捗状態"""
    sequence_type: SequenceType
    state: SequenceState
    current_step: int
    total_steps: int
    step_name: str
    start_time: datetime
    elapsed_time: float = 0.0
    error: SequenceError = SequenceError.NONE
    error_message: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'sequence_type': self.sequence_type.name,
            'state': self.state.name,
            'current_step': self.current_step,
            'total_steps': self.total_steps,
            'step_name': self.step_name,
            'start_time': self.start_time.isoformat(),
            'elapsed_time': self.elapsed_time,
            'error': self.error.name,
            'error_message': self.error_message,
        }


@dataclass
class SequenceConfig:
    """シーケンス設定"""
    # タイムアウト設定
    move_timeout: float = 60.0              # 移動タイムアウト [秒]
    io_timeout: float = 5.0                 # I/O確認タイムアウト [秒]
    
    # 速度設定
    default_speed: float = 50.0             # デフォルト移動速度 [%]
    z_down_speed: float = 30.0              # Z軸下降速度 [%]
    z_up_speed: float = 50.0                # Z軸上昇速度 [%]
    xy_speed: float = 50.0                  # XY移動速度 [%]
    
    # ポイント間待機
    step_delay: float = 0.1                 # ステップ間待機時間 [秒]


# =============================================================================
# イベントエミッター
# =============================================================================

class SequenceEventEmitter:
    """シーケンスイベントエミッター"""
    
    def __init__(self):
        self._listeners: Dict[str, List[Callable]] = {}
    
    def on(self, event: str, callback: Callable) -> None:
        """イベントリスナー登録"""
        if event not in self._listeners:
            self._listeners[event] = []
        self._listeners[event].append(callback)
    
    def off(self, event: str, callback: Callable) -> None:
        """イベントリスナー解除"""
        if event in self._listeners:
            self._listeners[event].remove(callback)
    
    def emit(self, event: str, *args, **kwargs) -> None:
        """イベント発火"""
        if event in self._listeners:
            for callback in self._listeners[event]:
                try:
                    result = callback(*args, **kwargs)
                    if asyncio.iscoroutine(result):
                        asyncio.create_task(result)
                except Exception as e:
                    logger.error(f"Event callback error ({event}): {e}")


# =============================================================================
# シーケンスマネージャ
# =============================================================================

class SequenceManager:
    """
    シーケンスマネージャ
    
    XYZ軸移動・I/O制御のシーケンス実行を管理します。
    
    Attributes:
        robot: RobotManagerインスタンス
        config: シーケンス設定
        events: イベントエミッター
    
    使用例:
        seq = SequenceManager(robot_manager)
        
        # イベントリスナー登録
        seq.events.on('progress', lambda p: print(f"Step: {p.step_name}"))
        seq.events.on('complete', lambda: print("Done!"))
        
        # ポイント移動シーケンス
        await seq.run_point_sequence(["P001", "P002", "P003"])
    """
    
    def __init__(
        self,
        robot: RobotManager,
        config: Optional[SequenceConfig] = None
    ):
        """
        初期化
        
        Args:
            robot: RobotManagerインスタンス
            config: シーケンス設定（省略時はデフォルト）
        """
        self.robot = robot
        self.config = config or SequenceConfig()
        self.events = SequenceEventEmitter()
        
        # 状態管理
        self._state = SequenceState.IDLE
        self._sequence_type = SequenceType.CUSTOM
        self._current_step = 0
        self._total_steps = 0
        self._step_name = ""
        self._error = SequenceError.NONE
        self._error_message = ""
        
        # 実行管理
        self._running = False
        self._pause_event = asyncio.Event()
        self._pause_event.set()
        self._stop_requested = False
        self._sequence_task: Optional[asyncio.Task] = None
        self._start_time: Optional[datetime] = None
        
        logger.info("SequenceManager initialized (XYZ control mode)")
    
    # =========================================================================
    # パブリックAPI
    # =========================================================================
    
    async def run_point_sequence(
        self,
        positions: List[str],
        speed_percent: Optional[float] = None
    ) -> bool:
        """
        ティーチングポイント順次移動シーケンス
        
        Args:
            positions: ポジション名リスト（順番に移動）
            speed_percent: 移動速度（省略時はconfig設定を使用）
        
        Returns:
            成功したかどうか
        """
        if self._running:
            logger.warning("Sequence already running")
            return False
        
        if not self.robot.status.is_initialized:
            logger.error("Robot not initialized")
            return False
        
        speed = speed_percent or self.config.default_speed
        
        self._start_sequence(SequenceType.POINT_MOVE, len(positions))
        
        try:
            for i, pos_name in enumerate(positions):
                if self._stop_requested:
                    break
                
                await self._update_step(i + 1, f"移動: {pos_name}")
                
                success = await self.robot.move_to_position(pos_name, speed_percent=speed)
                if not success:
                    await self._set_error(
                        SequenceError.MOVE_FAILED, 
                        f"ポジション '{pos_name}' への移動失敗"
                    )
                    return False
                
                await asyncio.sleep(self.config.step_delay)
            
            if self._state != SequenceState.ERROR:
                self._state = SequenceState.COMPLETED
                self.events.emit('complete')
            
            return self._state == SequenceState.COMPLETED
            
        except asyncio.CancelledError:
            logger.info("Point sequence cancelled")
            return False
        except Exception as e:
            await self._set_error(SequenceError.UNKNOWN, str(e))
            return False
        finally:
            self._running = False
    
    async def run_homing_sequence(self) -> bool:
        """
        原点復帰シーケンス
        
        Returns:
            成功したかどうか
        """
        if self._running:
            logger.warning("Sequence already running")
            return False
        
        if not self.robot.status.is_initialized:
            logger.error("Robot not initialized")
            return False
        
        self._start_sequence(SequenceType.HOMING, 3)
        
        try:
            await self._update_step(1, "原点復帰開始")
            
            await self._update_step(2, "原点復帰中")
            success = await self.robot.home_all()
            
            if not success:
                await self._set_error(SequenceError.MOVE_FAILED, "原点復帰失敗")
                return False
            
            await self._update_step(3, "原点復帰完了")
            self._state = SequenceState.COMPLETED
            self.events.emit('complete')
            
            return True
            
        except asyncio.CancelledError:
            logger.info("Homing sequence cancelled")
            return False
        except Exception as e:
            await self._set_error(SequenceError.UNKNOWN, str(e))
            return False
        finally:
            self._running = False
    
    async def run_custom_sequence(
        self,
        callback: Callable[[RobotManager, int], Awaitable[bool]],
        total_steps: int
    ) -> bool:
        """
        カスタムシーケンス実行
        
        Args:
            callback: ステップ実行コールバック (robot, step_number) -> success
            total_steps: 総ステップ数
        
        Returns:
            成功したかどうか
        
        使用例:
            async def my_callback(robot, step):
                if step == 1:
                    await robot.move_axis(0, 100.0)
                elif step == 2:
                    await robot.set_output(0, True)
                return True
            
            await seq.run_custom_sequence(my_callback, total_steps=2)
        """
        if self._running:
            logger.warning("Sequence already running")
            return False
        
        if not self.robot.status.is_initialized:
            logger.error("Robot not initialized")
            return False
        
        self._start_sequence(SequenceType.CUSTOM, total_steps)
        
        try:
            for step in range(1, total_steps + 1):
                if self._stop_requested:
                    break
                
                await self._pause_event.wait()
                
                await self._update_step(step, f"カスタムステップ {step}")
                
                success = await callback(self.robot, step)
                if not success:
                    await self._set_error(
                        SequenceError.UNKNOWN,
                        f"ステップ {step} 失敗"
                    )
                    return False
                
                await asyncio.sleep(self.config.step_delay)
            
            if self._state != SequenceState.ERROR:
                self._state = SequenceState.COMPLETED
                self.events.emit('complete')
            
            return self._state == SequenceState.COMPLETED
            
        except asyncio.CancelledError:
            logger.info("Custom sequence cancelled")
            return False
        except Exception as e:
            await self._set_error(SequenceError.UNKNOWN, str(e))
            return False
        finally:
            self._running = False
    
    async def stop_sequence(self) -> None:
        """シーケンスを停止"""
        if not self._running:
            return
        
        self._stop_requested = True
        self._pause_event.set()
        
        if self._sequence_task:
            self._sequence_task.cancel()
            try:
                await self._sequence_task
            except asyncio.CancelledError:
                pass
        
        await self.robot.stop()
        
        self._running = False
        self._state = SequenceState.ABORTED
        
        logger.info("Sequence stopped")
        self.events.emit('stopped')
    
    def pause(self) -> None:
        """シーケンスを一時停止"""
        if self._running and self._state == SequenceState.RUNNING:
            self._pause_event.clear()
            self._state = SequenceState.PAUSED
            logger.info("Sequence paused")
            self.events.emit('paused')
    
    def resume(self) -> None:
        """シーケンスを再開"""
        if self._state == SequenceState.PAUSED:
            self._pause_event.set()
            self._state = SequenceState.RUNNING
            logger.info("Sequence resumed")
            self.events.emit('resumed')
    
    def get_progress(self) -> SequenceProgress:
        """現在の進捗状態を取得"""
        elapsed = 0.0
        if self._start_time:
            elapsed = (datetime.now() - self._start_time).total_seconds()
        
        return SequenceProgress(
            sequence_type=self._sequence_type,
            state=self._state,
            current_step=self._current_step,
            total_steps=self._total_steps,
            step_name=self._step_name,
            start_time=self._start_time or datetime.now(),
            elapsed_time=elapsed,
            error=self._error,
            error_message=self._error_message,
        )
    
    # =========================================================================
    # プロパティ
    # =========================================================================
    
    @property
    def is_running(self) -> bool:
        return self._running
    
    @property
    def state(self) -> SequenceState:
        return self._state
    
    # =========================================================================
    # 内部メソッド
    # =========================================================================
    
    def _start_sequence(self, seq_type: SequenceType, total_steps: int) -> None:
        """シーケンス開始処理"""
        self._running = True
        self._stop_requested = False
        self._state = SequenceState.RUNNING
        self._sequence_type = seq_type
        self._total_steps = total_steps
        self._current_step = 0
        self._error = SequenceError.NONE
        self._error_message = ""
        self._start_time = datetime.now()
        
        logger.info(f"Sequence started: {seq_type.name}")
        self.events.emit('started', seq_type.name)
    
    async def _update_step(self, step: int, name: str) -> None:
        """ステップ更新"""
        self._current_step = step
        self._step_name = name
        
        self.events.emit('progress', self.get_progress())
        
        await self._pause_event.wait()
        
        if self._stop_requested:
            raise asyncio.CancelledError("Stop requested")
    
    async def _set_error(self, error: SequenceError, message: str) -> None:
        """エラー設定"""
        self._error = error
        self._error_message = message
        self._state = SequenceState.ERROR
        
        logger.error(f"Sequence error: {error.name} - {message}")
        self.events.emit('error', error, message)
