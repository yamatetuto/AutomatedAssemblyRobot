"""
CAN通信コントローラモジュール（非同期対応）

MCP2515 CANコントローラをSPI経由で制御し、I/Oエキスパンダボードと通信する。

参照元ファイル:
    - TEACHING/can.py: MCP2515制御、SPI通信、ポーリング処理
    - TEACHING/splebo_n.py: io_ex_input_class, io_ex_output_class

参照元の主要関数:
    - can.py::polling() → CANController._polling_task()
    - can.py::send_can_data() → CANController.send_can_data()
    - can.py::receive_can_data() → CANController.receive_can_data()
    - can.py::spi_write() → CANController._spi_transfer()

移植時の変更点:
    - threading.Thread → asyncio.Task に変換
    - グローバル変数 → インスタンス変数に変換
    - シミュレーションモード追加（ハードウェアなしでテスト可能）
    - RPi.GPIO → pigpio に変更（GPIO競合回避、docs/GPIO_CONFLICT_ISSUE.md参照）
"""
import asyncio
import logging
from typing import Optional, List, Dict
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# ハードウェア依存モジュール（実行時にインポート）
# 注意: RPi.GPIOはpigpioと競合するため使用しない
try:
    import spidev
    HAS_SPIDEV = True
except ImportError:
    HAS_SPIDEV = False
    spidev = None
    logger.warning("spidevが見つかりません。シミュレーションモードで動作します。")

# pigpio経由でGPIOを制御（motion_controllerからインポート）
from src.robot.motion_controller import (
    initialize_pigpio, gpio_read, gpio_write,
    get_pigpio_lib, is_pigpio_initialized
)

from src.robot.constants import MCP2515, CANConfig, GPIOPin


@dataclass
class CANMessage:
    """CANメッセージデータ構造"""
    id: int = 0
    extended_id: bool = False
    buffer_num: int = 0
    data: bytearray = field(default_factory=lambda: bytearray(8))
    length: int = 0


class CANController:
    """
    MCP2515 CANコントローラ（非同期対応）
    
    SPI経由でMCP2515を制御し、I/Oエキスパンダーとの通信を行う。
    """
    
    WRITE_CAN_ID_BASE = 0xC0
    WRITE_DATA_SIZE = 8
    READ_DATA_SIZE = 4
    
    def __init__(
        self,
        spi_bus: int = None,
        spi_device: int = None,
        spi_speed_hz: int = None,
        gpio_cs_pin: int = None,
        simulation_mode: bool = False,
    ):
        """
        初期化
        
        Args:
            spi_bus: SPIバス番号
            spi_device: SPIデバイス番号
            spi_speed_hz: SPI通信速度
            gpio_cs_pin: チップセレクトGPIOピン
            simulation_mode: シミュレーションモード
        """
        # 設定読み込み
        from src.config.settings import (
            ROBOT_CAN_SPI_BUS, ROBOT_CAN_SPI_DEVICE,
            ROBOT_CAN_SPEED_HZ, ROBOT_GPIO_CAN_CS
        )
        
        self.simulation_mode = simulation_mode
        self.spi_bus = spi_bus if spi_bus is not None else ROBOT_CAN_SPI_BUS
        self.spi_device = spi_device if spi_device is not None else ROBOT_CAN_SPI_DEVICE
        self.spi_speed_hz = spi_speed_hz if spi_speed_hz is not None else ROBOT_CAN_SPEED_HZ
        self.gpio_cs_pin = gpio_cs_pin if gpio_cs_pin is not None else ROBOT_GPIO_CAN_CS
        
        # SPI/GPIOデバイス
        self._spi: Optional[object] = None
        self._gpio_initialized = False
        
        # バッファ（最大16ボード対応）
        self._write_buffers: List[List[int]] = [
            [0] * self.WRITE_DATA_SIZE for _ in range(CANConfig.MAX_BOARDS)
        ]
        self._read_buffers: List[List[int]] = [
            [0] * self.READ_DATA_SIZE for _ in range(CANConfig.MAX_BOARDS)
        ]
        self._valid_boards: List[bool] = [True] * CANConfig.MAX_BOARDS
        
        # ポーリングタスク
        self._poll_task: Optional[asyncio.Task] = None
        self._polling = False
        
        # 排他制御
        self._spi_lock = asyncio.Lock()
        
        # 状態
        self.is_initialized = False
        # simulation_modeが明示的に指定されていればそれを使用、
        # そうでなければハードウェア有無で判定
        self._simulation_mode = simulation_mode or not HAS_SPIDEV
    
    async def initialize(self) -> bool:
        """
        CANコントローラを初期化
        
        Returns:
            成功時True
        """
        if self.is_initialized:
            logger.warning("CANコントローラは既に初期化されています")
            return True
        
        if self._simulation_mode:
            logger.info("シミュレーションモードでCAN初期化")
            self.is_initialized = True
            return True
        
        try:
            # GPIO初期化
            await asyncio.to_thread(self._init_gpio)
            
            # SPI初期化
            await asyncio.to_thread(self._init_spi)
            
            # MCP2515初期化
            await self._init_mcp2515()
            
            self.is_initialized = True
            logger.info("✅ CANコントローラ初期化完了")
            return True
            
        except Exception as e:
            logger.error(f"CANコントローラ初期化失敗: {e}")
            return False
    
    def _init_gpio(self) -> None:
        """GPIO初期化（同期処理）
        
        注意: RPi.GPIOではなくpigpioを使用する（GPIO競合回避）
        pigpioはmotion_controller.pyのinitialize_pigpio()で初期化済み
        """
        # pigpioでCSピンを出力に設定し、HIGHに設定
        # gpioSetModeの引数: 0=INPUT, 1=OUTPUT
        pigpio_lib = get_pigpio_lib()
        if pigpio_lib is not None:
            pigpio_lib.gpioSetMode(self.gpio_cs_pin, 1)  # OUTPUT
            gpio_write(self.gpio_cs_pin, 1)  # HIGH
            self._gpio_initialized = True
            logger.debug(f"GPIO CS pin {self.gpio_cs_pin} initialized (pigpio)")
        else:
            logger.warning(f"GPIO CS pin {self.gpio_cs_pin} initialization skipped: pigpio not loaded")
    
    def _init_spi(self) -> None:
        """SPI初期化（同期処理）"""
        self._spi = spidev.SpiDev()
        self._spi.open(self.spi_bus, self.spi_device)
        self._spi.mode = 3
        self._spi.max_speed_hz = self.spi_speed_hz
        logger.debug(f"SPI initialized: bus={self.spi_bus}, device={self.spi_device}, speed={self.spi_speed_hz}")
    
    async def _init_mcp2515(self) -> None:
        """MCP2515初期化"""
        # リセット
        await self._spi_transfer([MCP2515.CMD_RESET])
        await asyncio.sleep(0.03)
        
        # コンフィグモード設定
        await self._write_config(
            MCP2515.REG_CAN_CTRL,
            0xE0,
            MCP2515.MODE_CONFIG << 5
        )
        
        # コンフィグモード確認
        while True:
            status = await self._read_register(MCP2515.REG_CANSTAT)
            if status & (MCP2515.MODE_CONFIG << 5):
                break
            await asyncio.sleep(0.001)
        
        # ボーレート設定（16MHz, 500kbps）
        await self._write_register(MCP2515.REG_CAN_CNF1, 0x00)
        await self._write_register(MCP2515.REG_CAN_CNF2, 0x80)
        await self._write_register(MCP2515.REG_CAN_CNF3, 0x01)
        
        # 受信バッファ設定（マスクなし）
        await self._write_register(MCP2515.REG_RXB0CTRL, MCP2515.RX_NO_MASK)
        await self._write_register(MCP2515.REG_RXB1CTRL, MCP2515.RX_NO_MASK)
        
        # ノーマルモード設定
        await self._write_config(
            MCP2515.REG_CAN_CTRL,
            0xE0,
            MCP2515.MODE_NORMAL << 5
        )
        
        # ノーマルモード確認
        while True:
            status = await self._read_register(MCP2515.REG_CANSTAT)
            if not (status & (MCP2515.MODE_CONFIG << 5)):
                break
            await asyncio.sleep(0.001)
        
        logger.debug("MCP2515 initialized")
    
    async def _spi_transfer(self, data: List[int]) -> List[int]:
        """
        SPI転送（排他制御あり）
        
        Args:
            data: 送信データ
        
        Returns:
            受信データ
        
        Note:
            pigpio経由でCSピンを制御（RPi.GPIOは使用しない）
        """
        if self._simulation_mode:
            return [0] * len(data)
        
        async with self._spi_lock:
            cs_pin = self.gpio_cs_pin
            
            def _transfer():
                # CSをLOWに設定（pigpio経由）
                gpio_write(cs_pin, 0)
                result = self._spi.xfer2(data)
                # CSをHIGHに設定（pigpio経由）
                gpio_write(cs_pin, 1)
                return result
            
            result = await asyncio.to_thread(_transfer)
            await asyncio.sleep(0.001)  # 転送後の待機
            return result
    
    async def _write_register(self, addr: int, data: int) -> None:
        """レジスタ書き込み"""
        await self._spi_transfer([MCP2515.CMD_WRITE, addr, data])
    
    async def _read_register(self, addr: int) -> int:
        """レジスタ読み取り"""
        result = await self._spi_transfer([MCP2515.CMD_READ, addr, 0])
        return result[2]
    
    async def _write_config(self, addr: int, mask: int, data: int) -> None:
        """ビット変更"""
        await self._spi_transfer([MCP2515.CMD_BITMOD, addr, mask, data])
    
    async def send_can_data(self, board_id: int, data: List[int]) -> bool:
        """
        CANデータ送信
        
        Args:
            board_id: ボードID (0-15)
            data: 送信データ（最大8バイト）
        
        Returns:
            成功時True
        """
        if not self.is_initialized:
            logger.error("CANコントローラが初期化されていません")
            return False
        
        if self._simulation_mode:
            logger.debug(f"[SIM] CAN send to board {board_id}: {data}")
            return True
        
        try:
            msg = CANMessage()
            msg.id = self.WRITE_CAN_ID_BASE + board_id
            msg.length = min(len(data), 8)
            for i in range(msg.length):
                msg.data[i] = data[i]
            
            await self._set_tx_buffer(msg)
            await self._send_rts(0)
            return True
            
        except Exception as e:
            logger.error(f"CAN送信エラー: {e}")
            return False
    
    async def _set_tx_buffer(self, msg: CANMessage) -> None:
        """送信バッファ設定"""
        packet = [0] * 13
        cmd_bit = 1 * min(msg.buffer_num, 2)
        
        if not msg.extended_id:
            packet[0] = ((msg.id & 0x7F8) >> 3) & 0xFF
            packet[1] = ((msg.id & 0x7) << 5) & 0xFF
            packet[2] = 0
            packet[3] = 0
        else:
            packet[0] = (msg.id & 0x1FE00000) >> 21
            packet[1] = 0x08  # EXIDE
            packet[1] |= (msg.id & 0x1C0000) >> 13
            packet[1] |= (msg.id & 0x30000) >> 16
            packet[2] = (msg.id & 0xFF00) >> 8
            packet[3] = (msg.id & 0xFF)
        
        length = min(msg.length, 8)
        packet[4] = length
        
        for i in range(length):
            packet[5 + i] = msg.data[i]
        
        cmd = MCP2515.CMD_LDTXBUF | cmd_bit
        await self._spi_transfer([cmd] + packet[:5 + length])
    
    async def _send_rts(self, buffer_num: int) -> None:
        """送信要求"""
        cmd = MCP2515.CMD_RTS | (0x1 << buffer_num)
        await self._spi_transfer([cmd])
    
    async def receive_can_data(self) -> Optional[List[int]]:
        """
        CANデータ受信
        
        Returns:
            受信データ（データがない場合はNone）
        """
        if not self.is_initialized:
            return None
        
        if self._simulation_mode:
            return None
        
        try:
            # RXステータス確認
            result = await self._spi_transfer([MCP2515.CMD_RXSTATUS, 0])
            status = result[1]
            
            if status & MCP2515.MSK_MSGRX0:
                # RXB0にデータあり - ヘッダー読み取り
                await self._spi_transfer([MCP2515.CMD_RDRXBUF] + [0] * 5)
                
                # データ読み取り
                result = await self._spi_transfer([MCP2515.CMD_RDRXBUF | 0x02] + [0] * 8)
                return result[1:]
            
            return None
            
        except Exception as e:
            logger.error(f"CAN受信エラー: {e}")
            return None
    
    async def poll_board(self, board_id: int) -> bool:
        """
        ボードをポーリング（書き込み＆読み取り）
        
        Args:
            board_id: ボードID
        
        Returns:
            通信成功時True
        """
        if not self._valid_boards[board_id]:
            return False
        
        try:
            # 書き込みバッファを送信
            await self.send_can_data(board_id, self._write_buffers[board_id])
            
            # 応答を読み取り
            read_data = await self.receive_can_data()
            
            if read_data and len(read_data) >= 4:
                self._read_buffers[board_id][:4] = read_data[:4]
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"ボード{board_id}ポーリングエラー: {e}")
            self._valid_boards[board_id] = False
            return False
    
    async def start_polling(self, interval: float = None) -> None:
        """
        I/Oポーリング開始
        
        Args:
            interval: ポーリング間隔（秒）
        """
        if self._polling:
            logger.warning("ポーリングは既に実行中です")
            return
        
        from src.config.settings import ROBOT_IO_POLL_INTERVAL
        interval = interval or ROBOT_IO_POLL_INTERVAL
        
        self._polling = True
        self._poll_task = asyncio.create_task(self._poll_loop(interval))
        logger.info(f"CANポーリング開始（間隔: {interval}秒）")
    
    async def _poll_loop(self, interval: float) -> None:
        """ポーリングループ"""
        while self._polling:
            for board_id in range(CANConfig.MAX_BOARDS):
                if self._valid_boards[board_id]:
                    await self.poll_board(board_id)
                    await asyncio.sleep(0.002)
            
            await asyncio.sleep(interval)
        
        logger.info("CANポーリング停止")
    
    async def stop_polling(self) -> None:
        """ポーリング停止"""
        self._polling = False
        if self._poll_task:
            self._poll_task.cancel()
            try:
                await self._poll_task
            except asyncio.CancelledError:
                pass
            self._poll_task = None
    
    def set_output_bit(self, board_id: int, bit: int, value: bool) -> None:
        """
        出力ビット設定
        
        Args:
            board_id: ボードID
            bit: ビット番号 (0-31)
            value: True=ON, False=OFF
        """
        byte_pos = bit // 8
        bit_pos = bit % 8
        
        if byte_pos >= self.WRITE_DATA_SIZE:
            return
        
        if value:
            self._write_buffers[board_id][byte_pos] |= (1 << bit_pos)
        else:
            self._write_buffers[board_id][byte_pos] &= ~(1 << bit_pos)
    
    def get_input_bit(self, board_id: int, bit: int) -> bool:
        """
        入力ビット取得
        
        Args:
            board_id: ボードID
            bit: ビット番号 (0-31)
        
        Returns:
            ビット値
        """
        byte_pos = bit // 8
        bit_pos = bit % 8
        
        if byte_pos >= self.READ_DATA_SIZE:
            return False
        
        return bool(self._read_buffers[board_id][byte_pos] & (1 << bit_pos))
    
    def get_input_word(self, board_id: int) -> int:
        """
        入力ワード（32ビット）取得
        
        Args:
            board_id: ボードID
        
        Returns:
            32ビット値
        """
        buf = self._read_buffers[board_id]
        return (buf[3] << 24) | (buf[2] << 16) | (buf[1] << 8) | buf[0]
    
    async def close(self) -> None:
        """クローズ処理"""
        await self.stop_polling()
        
        if self._spi and not self._simulation_mode:
            try:
                await asyncio.to_thread(self._spi.close)
            except Exception as e:
                logger.warning(f"SPIクローズエラー: {e}")
        
        self._spi = None
        self.is_initialized = False
        logger.info("CANコントローラをクローズしました")
