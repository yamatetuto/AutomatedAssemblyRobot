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
            return True
        except Exception as e:
            logger.error(f"グリッパー接続失敗: {e}")
            self.controller = None
            self.is_connected = False
            return False
    
    async def disconnect(self):
        """グリッパーから切断"""
        if self.controller:
            try:
                self.controller.close()
                logger.info("グリッパーを切断しました")
            except Exception as e:
                logger.error(f"グリッパー切断エラー: {e}")
        
        self.controller = None
        self.is_connected = False
    
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
    
    async def get_current(self) -> int:
        """電流値を取得（リトライ付き）"""
        if not self.is_connected or not self.controller:
            raise RuntimeError("グリッパーが接続されていません")
        
        try:
            # 電流値レジスタ (0x900C) から読み取り（リトライ付き）
            current = await self._modbus_read_with_retry(
                self.controller.instrument.read_register,
                0x900C,
                functioncode=3,
                signed=True
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
                # ステータス読み取り
                status_dss1 = await asyncio.to_thread(
                    self.controller.instrument.read_register,
                    0x9005,
                    functioncode=3
                )

                psfl = await asyncio.to_thread(
                    self.controller.check_status_bit,
                    self.controller.REG_DEVICE_STATUS,
                    self.BIT_PUSH_MISS
                )
                
                # ビット抽出（DSS1レジスタから）
                psfl = bool((status_dss1 >> 11) & 0x1)  # 押付け空振りフラグ
                
                # 拡張ステータス（DSSE）を読み取って移動中フラグを確認
                status_dsse = await asyncio.to_thread(
                    self.controller.instrument.read_register,
                    0x9007,  # 拡張デバイスステータスレジスタ (DSSE)
                    functioncode=3
                )
                move = bool((status_dsse >> 5) & 0x1)  # MOVEビット（移動中信号）
                
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
                
                # 電流値読み取り（直接読み取り - ロック内なのでget_current()を呼ばない）
                current = await asyncio.to_thread(
                    self.controller.get_current_mA
                )
                
                # 現在位置読み取り
                position_raw = await asyncio.to_thread(
                    self.controller.get_current_position
                )
                position_mm = position_raw * 0.01
                
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

