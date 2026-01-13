"""
I/Oエキスパンダー制御モジュール

CAN経由でI/Oエキスパンダーボードを制御する。
入力センサーの読み取り、出力ポートの制御、ブザー等の機能を提供。

参照元ファイル:
    - TEACHING/splebo_n.py: io_ex_input_class (L430-550), io_ex_output_class (L550-700)
    - TEACHING/constant.py: INPUT_*, OUTPUT_* 定数

参照元の主要クラス/関数:
    - splebo_n.io_ex_input_class → IOExpander.get_input(), is_*_active()
    - splebo_n.io_ex_output_class → IOExpander.set_output(), buzzer_*()
    - splebo_n.check_*() 関数群 → IOExpander.check_*() メソッド

移植時の変更点:
    - CANController経由でI/Oアクセス（直接アクセスではなく抽象化）
    - async/await対応
    - 入出力状態のキャッシュ機能追加
"""
import asyncio
import logging
from typing import Dict, Optional
from dataclasses import dataclass

from src.robot.can_controller import CANController
from src.robot.constants import InputPort, OutputPort

logger = logging.getLogger(__name__)


@dataclass
class IOStatus:
    """I/O状態"""
    inputs: Dict[str, bool]
    outputs: Dict[str, bool]


class IOExpander:
    """
    I/Oエキスパンダー制御クラス
    
    CAN経由でI/Oボードの入出力を制御する。
    """
    
    # I/Oボード設定
    IO_BOARD_ID = 0  # 主要I/Oボード
    
    def __init__(self, can_controller: CANController, simulation_mode: bool = False):
        """
        初期化
        
        Args:
            can_controller: CANコントローラインスタンス
            simulation_mode: シミュレーションモード
        """
        self.can = can_controller
        self._simulation_mode = simulation_mode or (can_controller and can_controller._simulation_mode)
        self._output_cache: Dict[int, bool] = {}
        self._input_cache: Dict[int, bool] = {}
        self._lock = asyncio.Lock()
    
    async def get_input(self, port: int) -> bool:
        """
        入力ポート読み取り
        
        Args:
            port: ポート番号 (InputPort enum値)
        
        Returns:
            ポート状態 (True=ON, False=OFF)
        """
        if self._simulation_mode:
            # シミュレーション: キャッシュ値を返す（デフォルトFalse）
            return self._input_cache.get(port, False)
        return self.can.get_input_bit(self.IO_BOARD_ID, port)
    
    async def set_output(self, port: int, value: bool) -> None:
        """
        出力ポート設定
        
        Args:
            port: ポート番号 (OutputPort enum値、100-115)
            value: True=ON, False=OFF
        """
        async with self._lock:
            # OutputPortは100番台、実際のビット位置に変換
            bit = port - 100 if port >= 100 else port
            
            if not self._simulation_mode:
                self.can.set_output_bit(self.IO_BOARD_ID, bit, value)
            
            self._output_cache[port] = value
            
            logger.debug(f"Output port {port} set to {value}")
    
    async def get_output(self, port: int) -> bool:
        """
        出力ポート状態取得（キャッシュから）
        
        Args:
            port: ポート番号
        
        Returns:
            現在の出力状態
        """
        return self._output_cache.get(port, False)
    
    async def wait_input(
        self,
        port: int,
        expected: bool = True,
        timeout: float = 0.5
    ) -> bool:
        """
        入力ポートが期待値になるまで待機
        
        Args:
            port: ポート番号
            expected: 期待する値
            timeout: タイムアウト時間（秒）
        
        Returns:
            成功時True、タイムアウト時False
        """
        deadline = asyncio.get_event_loop().time() + timeout
        
        while asyncio.get_event_loop().time() < deadline:
            value = await self.get_input(port)
            if value == expected:
                return True
            await asyncio.sleep(0.005)
        
        logger.warning(f"入力ポート{port}がタイムアウト（期待値: {expected}）")
        return False
    
    async def get_all_inputs(self) -> Dict[str, bool]:
        """
        全入力ポート状態取得
        
        Returns:
            ポート名と状態のディクショナリ
        """
        result = {}
        for port in InputPort:
            result[port.name] = await self.get_input(port.value)
        return result
    
    async def get_all_outputs(self) -> Dict[str, bool]:
        """
        全出力ポート状態取得
        
        Returns:
            ポート名と状態のディクショナリ
        """
        result = {}
        for port in OutputPort:
            result[port.name] = self._output_cache.get(port.value, False)
        return result
    
    async def get_status(self) -> IOStatus:
        """
        全I/O状態取得
        
        Returns:
            IOStatusオブジェクト
        """
        return IOStatus(
            inputs=await self.get_all_inputs(),
            outputs=await self.get_all_outputs()
        )
    
    async def initialize_outputs(self) -> None:
        """全出力を初期化（OFF）"""
        logger.info("全出力ポートを初期化中...")
        
        for port in OutputPort:
            await self.set_output(port.value, False)
        
        logger.info("全出力ポート初期化完了")
    
    async def buzzer_beep(self, duration: float = 0.15) -> None:
        """
        ブザー鳴動
        
        Args:
            duration: 鳴動時間（秒）
        """
        await self.set_output(OutputPort.BUZZER.value, True)
        await asyncio.sleep(duration)
        await self.set_output(OutputPort.BUZZER.value, False)
    
    async def blink_start_leds(self, interval: float = 0.5) -> None:
        """
        スタートLED点滅（1回）
        
        Args:
            interval: 点滅間隔（秒）
        """
        # ON
        await self.set_output(OutputPort.START_LEFT.value, True)
        await self.set_output(OutputPort.START_RIGHT.value, True)
        await asyncio.sleep(interval)
        
        # OFF
        await self.set_output(OutputPort.START_LEFT.value, False)
        await self.set_output(OutputPort.START_RIGHT.value, False)
    
    async def check_driver_position(self) -> Dict[str, bool]:
        """
        ドライバーシリンダー位置確認
        
        Returns:
            {'up': bool, 'down': bool}
        """
        return {
            'up': await self.get_input(InputPort.DRIVER_UP.value),
            'down': await self.get_input(InputPort.DRIVER_DOWN.value)
        }
    
    async def check_screw_guide(self) -> Dict[str, bool]:
        """
        ネジガイド位置確認
        
        Returns:
            {'open': bool, 'close': bool}
        """
        return {
            'open': await self.get_input(InputPort.SCREW_GUIDE_OPEN.value),
            'close': await self.get_input(InputPort.SCREW_GUIDE_CLOSE.value)
        }
    
    async def check_work_lock(self) -> Dict[str, bool]:
        """
        ワークロック状態確認
        
        Returns:
            {'locked': bool, 'unlocked': bool}
        """
        return {
            'locked': await self.get_input(InputPort.WORK_LOCK_LOCK.value),
            'unlocked': await self.get_input(InputPort.WORK_LOCK_ORG.value)
        }
    
    async def check_start_switches(self) -> Dict[str, bool]:
        """
        スタートスイッチ状態確認
        
        Returns:
            {'left': bool, 'right': bool, 'both': bool}
        """
        left = await self.get_input(InputPort.START_LEFT_SW.value)
        right = await self.get_input(InputPort.START_RIGHT_SW.value)
        return {
            'left': left,
            'right': right,
            'both': left and right
        }
    
    async def has_screw(self) -> bool:
        """ネジ有無確認"""
        return await self.get_input(InputPort.SCREW_DETECT.value)
    
    async def has_feeder_screw(self) -> bool:
        """フィーダーネジ有無確認"""
        return await self.get_input(InputPort.FEEDER_SCREW.value)
    
    async def has_work(self) -> bool:
        """ワーク有無確認"""
        return await self.get_input(InputPort.WORK_ENABLE.value)
    
    async def is_emergency_active(self) -> bool:
        """
        非常停止スイッチ状態確認
        
        Returns:
            True: 非常停止中, False: 正常
        """
        return await self.get_input(InputPort.EMG_SW.value)
    
    async def is_torque_up(self) -> bool:
        """トルクアップ確認"""
        return await self.get_input(InputPort.DRIVER_TORQUE_UP.value)
    
    async def get_displacement_sensor(self) -> Dict[str, bool]:
        """
        変位センサー状態取得
        
        Returns:
            {'high': bool, 'ok': bool, 'low': bool}
        """
        return {
            'high': await self.get_input(InputPort.DS_HIGH.value),
            'ok': await self.get_input(InputPort.DS_OK.value),
            'low': await self.get_input(InputPort.DS_LOW.value)
        }
    
    async def displacement_sensor_reset(self) -> None:
        """変位センサーリセット"""
        await self.set_output(OutputPort.DS_RESET.value, True)
        await asyncio.sleep(0.02)
        await self.set_output(OutputPort.DS_RESET.value, False)
    
    async def displacement_sensor_timing(self) -> None:
        """変位センサータイミング信号送信"""
        await self.set_output(OutputPort.DS_TIMING.value, True)
        await asyncio.sleep(0.02)
        await self.set_output(OutputPort.DS_TIMING.value, False)
        await asyncio.sleep(0.01)
