"""
グリッパー管理モジュール
IAI製グリッパーの制御を提供（CONControllerをラップ）
"""
import asyncio
import logging
from typing import Optional, Dict
from pathlib import Path

from src.gripper.controller import CONController
from src.config.settings import GRIPPER_PORT, GRIPPER_SLAVE_ADDR, GRIPPER_BAUDRATE

logger = logging.getLogger(__name__)


class GripperManager:
    """グリッパー管理クラス"""
    
    async def _modbus_read_with_retry(self, func, *args, max_retries=3, **kwargs):
        """
        Modbus読み取りをリトライ付きで実行
        
        半二重通信の仕様:
        - マスターはクエリー送信後、レスポンス受信まで待機
        - タイムアウト後は最大3回までリトライ
        
        Args:
            func: 読み取り関数
            max_retries: 最大リトライ回数（デフォルト3）
        
        Returns:
            読み取り結果
        """
        last_exception = None
        for attempt in range(max_retries):
            try:
                async with self._modbus_lock:
                    result = await asyncio.to_thread(func, *args, **kwargs)
                    return result
            except Exception as e:
                last_exception = e
                if attempt < max_retries - 1:
                    # リトライ前に短時間待機（通信の安定化）
                    await asyncio.sleep(0.01)
                    logger.warning(f"Modbus読み取りリトライ {attempt + 1}/{max_retries}: {e}")
        
        # 全てのリトライ失敗
        logger.error(f"Modbus読み取り失敗（{max_retries}回リトライ後）: {last_exception}")
        raise last_exception

    async def _modbus_write_with_retry(self, func, *args, max_retries=3, **kwargs):
        """
        Modbus書き込みをリトライ付きで実行
        
        半二重通信の仕様:
        - マスターはクエリー送信後、レスポンス受信まで待機
        - 書き込みは読み取りより内部処理時間が長い（最大18ms）
        - タイムアウト後は最大3回までリトライ
        
        Args:
            func: 書き込み関数
            max_retries: 最大リトライ回数（デフォルト3）
        
        Returns:
            書き込み結果
        """
        last_exception = None
        for attempt in range(max_retries):
            try:
                async with self._modbus_lock:
                    result = await asyncio.to_thread(func, *args, **kwargs)
                    # 書き込み後、RC コントローラーが次のクエリー受信に備えるまで待機（1ms）
                    await asyncio.sleep(0.002)  # 安全のため2ms待機
                    return result
            except Exception as e:
                last_exception = e
                if attempt < max_retries - 1:
                    # リトライ前に短時間待機
                    await asyncio.sleep(0.01)
                    logger.warning(f"Modbus書き込みリトライ {attempt + 1}/{max_retries}: {e}")
        
        # 全てのリトライ失敗
        logger.error(f"Modbus書き込み失敗（{max_retries}回リトライ後）: {last_exception}")
        raise last_exception

    def __init__(self):
        self._modbus_lock = asyncio.Lock()  # Modbus通信の排他制御
        self.controller: Optional[CONController] = None
        self.is_connected = False
        
        # キャッシュ用変数（定期的にバックグラウンドで更新）
        self._cached_current: Optional[int] = None  # 電流値 (mA)
        self._cached_position: Optional[float] = None  # 位置 (mm)
        self._cache_timestamp: float = 0  # キャッシュ更新時刻
        self._monitor_task: Optional[asyncio.Task] = None  # モニタータスク
    
    async def connect(self):
        """グリッパーに接続"""
        if self.is_connected:
            logger.warning("グリッパーは既に接続されています")
            return True
        
        try:
            logger.info(f"グリッパー接続中: {GRIPPER_PORT}")
            self.controller = CONController(
                port=GRIPPER_PORT,
                slave_address=GRIPPER_SLAVE_ADDR,
                baudrate=GRIPPER_BAUDRATE
            )
            self.is_connected = True
            logger.info(f"✅ グリッパー接続成功: {GRIPPER_PORT}")
            await self._start_monitor()
            return True
        except Exception as e:
            logger.error(f"グリッパー接続失敗: {e}")
            self.controller = None
            self.is_connected = False
            return False
    
    async def disconnect(self):
        """グリッパーから切断"""
        await self._stop_monitor()
        if self.controller:
            try:
                self.controller.close()
                logger.info("グリッパーを切断しました")
            except Exception as e:
                logger.error(f"グリッパー切断エラー: {e}")
        
        self.controller = None
        self.is_connected = False
    

    async def _monitor_loop(self):
        """バックグラウンドで電流値と位置を定期的に更新"""
        logger.info("グリッパーモニタータスクを開始")
        try:
            while self.is_connected:
                try:
                    # 電流値を取得
                    current = await self._modbus_read_with_retry(
                        self.controller.get_current_mA
                    )
                    # 位置を取得
                    position = await self._modbus_read_with_retry(
                        self.controller.get_current_position
                    )
                    
                    # キャッシュを更新
                    self._cached_current = current
                    self._cached_position = position
                    self._cache_timestamp = time.time()
                    
                except Exception as e:
                    logger.warning(f"モニター更新エラー: {e}")
                
                # 200ms待機
                await asyncio.sleep(0.2)
        except asyncio.CancelledError:
            logger.info("グリッパーモニタータスクをキャンセル")
        except Exception as e:
            logger.error(f"モニタータスクエラー: {e}")
    
    async def _start_monitor(self):
        """モニタータスクを開始"""
        if self._monitor_task is None or self._monitor_task.done():
            self._monitor_task = asyncio.create_task(self._monitor_loop())
            logger.info("グリッパーモニターを開始しました")
    
    async def _stop_monitor(self):
        """モニタータスクを停止"""
        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            self._monitor_task = None
            logger.info("グリッパーモニターを停止しました")

    async def get_status(self) -> Dict:
        """グリッパーステータスを取得（非同期読み取り、ロック使用）"""
        if not self.is_connected or not self.controller:
            raise RuntimeError("グリッパーが接続されていません")
        
        async with self._modbus_lock:
            try:
                # controller.pyのメソッドを使用（非同期実行）
                position_mm = await asyncio.to_thread(
                    self.controller.get_current_position
                )
                alarm = await asyncio.to_thread(
                    self.controller.get_current_alarm
                )
                servo_on = await asyncio.to_thread(
                    self.controller.check_status_bit,
                    self.controller.REG_DEVICE_STATUS,
                    self.controller.BIT_SERVO_READY
                )
                
                position = int(position_mm * 100)  # mm -> 0.01mm単位に変換
                
                return {
                    "status": "ok",
                    "position": position,
                    "position_mm": position_mm,
                    "alarm": alarm,
                    "servo_on": servo_on
                }
            except Exception as e:
                logger.error(f"ステータス取得エラー: {e}")
                # エラー時もレスポンスを返す（main_webrtc_fixed.py方式）
                return {
                    "status": "error",
                    "message": str(e),
                    "position": 0,
                    "position_mm": 0.0,
                    "alarm": 0,
                    "servo_on": False
                }
    
    async def servo_on(self):
        """サーボON"""
        if not self.is_connected or not self.controller:
            raise RuntimeError("グリッパーが接続されていません")
        
        async with self._modbus_lock:
            # 別スレッドで実行してイベントループをブロックしない
            await asyncio.to_thread(self.controller.servo_on)
        logger.info("サーボON")
    
    async def servo_off(self):
        """サーボOFF"""
        if not self.is_connected or not self.controller:
            raise RuntimeError("グリッパーが接続されていません")
        
        async with self._modbus_lock:
            # 別スレッドで実行してイベントループをブロックしない
            await asyncio.to_thread(self.controller.servo_off)
        logger.info("サーボOFF")
    
    async def home(self):
        """原点復帰"""
        if not self.is_connected or not self.controller:
            raise RuntimeError("グリッパーが接続されていません")
        
        async with self._modbus_lock:
            # 別スレッドで実行してイベントループをブロックしない
            await asyncio.to_thread(self.controller.home)
        logger.info("原点復帰を実行")
    
    async def move_to_position(self, position_number: int):
        """指定ポジションに移動"""
        if not self.is_connected or not self.controller:
            raise RuntimeError("グリッパーが接続されていません")
        
        if position_number < 0 or position_number > 63:
            raise ValueError("ポジション番号は0-63の範囲で指定してください")
        
        async with self._modbus_lock:
            # 別スレッドで実行してイベントループをブロックしない
            await asyncio.to_thread(self.controller.move_to_pos, position_number)
        logger.info(f"ポジション{position_number}に移動")
    
    async def get_position_table(self, position_number: int) -> Optional[Dict]:
        """ポジションテーブルのデータを取得"""
        if not self.is_connected or not self.controller:
            raise RuntimeError("グリッパーが接続されていません")
        
        if position_number < 0 or position_number > 63:
            raise ValueError("ポジション番号は0-63の範囲で指定してください")
        
        async with self._modbus_lock:
            try:
                data = await asyncio.to_thread(self.controller.get_position_data, position_number)
                return data
            except Exception as e:
                logger.error(f"ポジションデータ取得エラー: {e}")
                raise
    
    async def update_position_table(self, position_number: int, data: Dict):
        """ポジションテーブルのデータを更新"""
        if not self.is_connected or not self.controller:
            raise RuntimeError("グリッパーが接続されていません")
        
        if position_number < 0 or position_number > 63:
            raise ValueError("ポジション番号は0-63の範囲で指定してください")
        
        async with self._modbus_lock:
            await asyncio.to_thread(
                self.controller.set_position_data,
                position_number,
                position_mm=data.get("position"),
                width_mm=data.get("width"),
                speed_mm_s=data.get("speed"),
                accel_g=data.get("accel"),
                decel_g=data.get("decel"),
                push_current_percent=data.get("push_current", 0)
            )
        logger.info(f"ポジション{position_number}のデータを更新")
    
    async def get_cached_current(self, max_age: float = 1.0) -> Optional[int]:
        """
        キャッシュされた電流値を取得（max_age秒以内のキャッシュ）
        
        Args:
            max_age: キャッシュの有効期限（秒）。デフォルト1秒
        
        Returns:
            電流値 (mA)。キャッシュが古い場合はNone
        """
        import time
        if self._cached_current is not None:
            age = time.time() - self._cache_timestamp
            if age <= max_age:
                return self._cached_current
        return None
    
    async def get_cached_position(self, max_age: float = 1.0) -> Optional[float]:
        """
        キャッシュされた位置を取得（max_age秒以内のキャッシュ）
        
        Args:
            max_age: キャッシュの有効期限（秒）。デフォルト1秒
        
        Returns:
            位置 (mm)。キャッシュが古い場合はNone
        """
        import time
        if self._cached_position is not None:
            age = time.time() - self._cache_timestamp
            if age <= max_age:
                return self._cached_position
        return None
    
    async def get_current(self) -> int:
        """電流値を取得（キャッシュ優先、古い場合は再取得）"""
        if not self.is_connected or not self.controller:
            raise RuntimeError("グリッパーが接続されていません")
        
        # キャッシュ確認（1秒以内）
        cached = await self.get_cached_current(max_age=1.0)
        if cached is not None:
            return cached
        
        # キャッシュが古い場合は直接取得
        try:
            current = await self._modbus_read_with_retry(
                self.controller.get_current_mA
            )
            return current
        except Exception as e:
            logger.error(f"電流値取得エラー: {e}")
            raise

    async def check_grip_status(self, target_position: Optional[int] = None) -> Dict:
        """
        把持状態を判定
        
        Args:
            target_position: 目標ポジション番号（位置差分判定に使用）
        
        Returns:
            {
                "status": "success" | "failure" | "warning" | "moving",
                "reason": str,
                "current": int,
                "position_mm": float,
                "psfl": bool,
                "confidence": "high" | "medium" | "low"
            }
        """
        if not self.is_connected or not self.controller:
            raise RuntimeError("グリッパーが接続されていません")
        
        async with self._modbus_lock:
            try:
                # 電流値読み取り（キャッシュ優先）
                cached_current = await self.get_cached_current(max_age=0.5)
                current = cached_current if cached_current is not None else await asyncio.to_thread(
                    self.controller.get_current_mA
                )
                
                # 現在位置読み取り（キャッシュ優先、既にmm単位）
                cached_position = await self.get_cached_position(max_age=0.5)
                position_mm = cached_position if cached_position is not None else await asyncio.to_thread(
                    self.controller.get_current_position
                )
                
                # MOVEビット（移動中信号）をcontroller.check_status_bitで確認
                move = await asyncio.to_thread(
                    self.controller.check_status_bit,
                    self.controller.REG_EXT_STATUS,
                    self.controller.BIT_MOVE
                )
                move = bool(move)
                
                # PSFL（押付け空振りフラグ）をcontroller.check_status_bitで確認
                psfl = await asyncio.to_thread(
                    self.controller.check_status_bit,
                    self.controller.REG_DEVICE_STATUS,
                    self.controller.BIT_PUSH_MISS
                )
                psfl = bool(psfl)
                
                # 移動中チェック（MOVEビットで判定）
                if move:
                    return {
                        "status": "moving",
                        "reason": "positioning",
                        "current": 0,
                        "position_mm": 0.0,
                        "psfl": False,
                        "confidence": "high"
                    }
                
                # 空振りフラグチェック（最優先）
                if psfl:
                    return {
                        "status": "failure",
                        "reason": "empty_grip",
                        "current": current,
                        "position_mm": position_mm,
                        "psfl": True,
                        "confidence": "high"
                    }
                
                # 電流値閾値判定（基本判定）
                GRIP_CURRENT_THRESHOLD = 100  # TODO: 実機で調整
                
                if current > GRIP_CURRENT_THRESHOLD:
                    return {
                        "status": "success",
                        "reason": "normal",
                        "current": current,
                        "position_mm": position_mm,
                        "psfl": False,
                        "confidence": "high"
                    }
                else:
                    return {
                        "status": "warning",
                        "reason": "low_current",
                        "current": current,
                        "position_mm": position_mm,
                        "psfl": False,
                        "confidence": "medium"
                    }
                        
            except Exception as e:
                logger.error(f"把持状態判定エラー: {e}")
                raise

