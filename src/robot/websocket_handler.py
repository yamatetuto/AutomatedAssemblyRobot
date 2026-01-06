# *********************************************************************#
# File Name : websocket_handler.py
# Explanation : WebSocket Handler for Real-time Robot Status
# Project : AutomatedAssemblyRobot - SPLEBO-N Integration
# ----------------------------------------------------------------------
# Based on : 新規作成（TEACHINGにはWebSocket機能なし）
# History :
#           ver0.0.1 2026.1.7 New Create - WebSocket handler
# *********************************************************************#

"""
WebSocket ハンドラー - リアルタイムロボット状態配信

SPLEBO-Nロボットの状態をリアルタイムでWebSocketクライアントに配信します。
フロントエンド（React/Vue等）からの状態監視に使用されます。

機能:
    - 周期的な状態配信（100msごと）
    - イベント駆動型通知（移動完了、エラー発生等）
    - 複数クライアント同時接続対応
    - 自動再接続サポート

メッセージタイプ:
    サーバー → クライアント:
        - status: 現在の状態（位置、エラー、モード等）
        - event: イベント通知（移動完了、原点復帰完了等）
        - error: エラー通知
    
    クライアント → サーバー:
        - subscribe: 購読開始（特定の情報のみ受信）
        - unsubscribe: 購読解除
        - ping: 接続確認

使用例:
    from src.robot.websocket_handler import RobotWebSocketManager
    
    ws_manager = RobotWebSocketManager(robot_manager)
    
    @app.websocket("/ws/robot")
    async def websocket_endpoint(websocket: WebSocket):
        await ws_manager.handle_connection(websocket)
"""

import asyncio
import json
import logging
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum, auto
from typing import Dict, Set, Optional, Any, Callable
from weakref import WeakSet

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


# =============================================================================
# メッセージタイプ
# =============================================================================

class MessageType(str, Enum):
    """WebSocketメッセージタイプ"""
    STATUS = "status"
    EVENT = "event"
    ERROR = "error"
    PONG = "pong"
    ACK = "ack"


class EventType(str, Enum):
    """イベントタイプ"""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    INITIALIZED = "initialized"
    SHUTDOWN = "shutdown"
    HOMING_STARTED = "homing_started"
    HOMING_COMPLETE = "homing_complete"
    MOVE_STARTED = "move_started"
    MOVE_COMPLETE = "move_complete"
    POSITION_TAUGHT = "position_taught"
    ERROR_OCCURRED = "error_occurred"
    ERROR_CLEARED = "error_cleared"
    MODE_CHANGED = "mode_changed"
    STATE_CHANGED = "state_changed"
    IO_CHANGED = "io_changed"


class SubscriptionType(str, Enum):
    """購読タイプ"""
    ALL = "all"
    STATUS = "status"
    EVENTS = "events"
    POSITIONS = "positions"
    IO = "io"


# =============================================================================
# データクラス
# =============================================================================

@dataclass
class WebSocketMessage:
    """WebSocketメッセージ"""
    type: str
    data: Dict[str, Any]
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
    
    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)


@dataclass
class ClientInfo:
    """クライアント情報"""
    id: str
    connected_at: datetime
    subscriptions: Set[SubscriptionType]
    last_ping: datetime
    
    def is_subscribed(self, sub_type: SubscriptionType) -> bool:
        """指定タイプを購読しているかどうか"""
        return SubscriptionType.ALL in self.subscriptions or sub_type in self.subscriptions


# =============================================================================
# WebSocket Manager
# =============================================================================

class RobotWebSocketManager:
    """
    ロボットWebSocket管理クラス
    
    複数のWebSocketクライアントへのリアルタイム状態配信を管理します。
    
    Attributes:
        robot_manager: RobotManagerインスタンス
        broadcast_interval: 状態配信間隔 [秒]
    """
    
    def __init__(
        self,
        robot_manager: 'RobotManager',
        broadcast_interval: float = 0.1
    ):
        """
        初期化
        
        Args:
            robot_manager: RobotManagerインスタンス
            broadcast_interval: 状態配信間隔 [秒]（デフォルト: 100ms）
        """
        self.robot_manager = robot_manager
        self.broadcast_interval = broadcast_interval
        
        # 接続管理
        self._connections: Dict[str, WebSocket] = {}
        self._client_info: Dict[str, ClientInfo] = {}
        self._client_counter = 0
        
        # タスク管理
        self._broadcast_task: Optional[asyncio.Task] = None
        self._running = False
        
        # イベントリスナー登録
        self._setup_event_listeners()
    
    def _setup_event_listeners(self) -> None:
        """イベントリスナーを設定"""
        # RobotManagerからのイベントをWebSocketに転送
        if hasattr(self.robot_manager, 'events'):
            events = self.robot_manager.events
            events.on('initialized', lambda: self._emit_event(EventType.INITIALIZED, {}))
            events.on('shutdown', lambda: self._emit_event(EventType.SHUTDOWN, {}))
            events.on('homing_started', lambda axis: self._emit_event(
                EventType.HOMING_STARTED, {'axis': axis}))
            events.on('homing_complete', lambda axis: self._emit_event(
                EventType.HOMING_COMPLETE, {'axis': axis}))
            events.on('move_started', lambda data: self._emit_event(
                EventType.MOVE_STARTED, data))
            events.on('move_complete', lambda data: self._emit_event(
                EventType.MOVE_COMPLETE, data))
            events.on('error', lambda code, msg: self._emit_event(
                EventType.ERROR_OCCURRED, {'code': code, 'message': msg}))
            events.on('error_cleared', lambda: self._emit_event(EventType.ERROR_CLEARED, {}))
            events.on('mode_changed', lambda mode: self._emit_event(
                EventType.MODE_CHANGED, {'mode': mode}))
    
    # =========================================================================
    # 接続管理
    # =========================================================================
    
    async def handle_connection(self, websocket: WebSocket) -> None:
        """
        WebSocket接続を処理
        
        Args:
            websocket: WebSocket接続
        """
        await websocket.accept()
        
        # クライアントID生成
        self._client_counter += 1
        client_id = f"client_{self._client_counter}"
        
        # 接続登録
        self._connections[client_id] = websocket
        self._client_info[client_id] = ClientInfo(
            id=client_id,
            connected_at=datetime.now(),
            subscriptions={SubscriptionType.ALL},
            last_ping=datetime.now()
        )
        
        logger.info(f"WebSocket client connected: {client_id}")
        
        # 接続通知を送信
        await self._send_to_client(client_id, WebSocketMessage(
            type=MessageType.EVENT,
            data={
                'event': EventType.CONNECTED,
                'client_id': client_id,
                'message': 'Connected to robot WebSocket'
            }
        ))
        
        # ブロードキャストタスク開始（最初の接続時）
        if len(self._connections) == 1 and not self._running:
            self._start_broadcast()
        
        try:
            # メッセージ受信ループ
            await self._receive_loop(client_id, websocket)
        except WebSocketDisconnect:
            logger.info(f"WebSocket client disconnected: {client_id}")
        except Exception as e:
            logger.error(f"WebSocket error for {client_id}: {e}")
        finally:
            # クリーンアップ
            self._disconnect_client(client_id)
    
    def _disconnect_client(self, client_id: str) -> None:
        """クライアントを切断"""
        if client_id in self._connections:
            del self._connections[client_id]
        if client_id in self._client_info:
            del self._client_info[client_id]
        
        logger.debug(f"Client {client_id} removed. Active connections: {len(self._connections)}")
        
        # 最後の接続が切れたらブロードキャスト停止
        if len(self._connections) == 0:
            self._stop_broadcast()
    
    async def _receive_loop(self, client_id: str, websocket: WebSocket) -> None:
        """
        メッセージ受信ループ
        
        Args:
            client_id: クライアントID
            websocket: WebSocket接続
        """
        while True:
            try:
                data = await websocket.receive_json()
                await self._handle_message(client_id, data)
            except json.JSONDecodeError:
                await self._send_error(client_id, "Invalid JSON format")
    
    async def _handle_message(self, client_id: str, data: Dict) -> None:
        """
        クライアントからのメッセージを処理
        
        Args:
            client_id: クライアントID
            data: メッセージデータ
        """
        msg_type = data.get('type', '').lower()
        
        if msg_type == 'ping':
            # Ping応答
            if client_id in self._client_info:
                self._client_info[client_id].last_ping = datetime.now()
            await self._send_to_client(client_id, WebSocketMessage(
                type=MessageType.PONG,
                data={'message': 'pong'}
            ))
        
        elif msg_type == 'subscribe':
            # 購読開始
            subscriptions = data.get('subscriptions', ['all'])
            if client_id in self._client_info:
                self._client_info[client_id].subscriptions = {
                    SubscriptionType(s) for s in subscriptions if s in SubscriptionType._value2member_map_
                }
                await self._send_to_client(client_id, WebSocketMessage(
                    type=MessageType.ACK,
                    data={'action': 'subscribe', 'subscriptions': subscriptions}
                ))
        
        elif msg_type == 'unsubscribe':
            # 購読解除
            to_remove = data.get('subscriptions', [])
            if client_id in self._client_info:
                for sub in to_remove:
                    self._client_info[client_id].subscriptions.discard(
                        SubscriptionType(sub) if sub in SubscriptionType._value2member_map_ else None
                    )
                await self._send_to_client(client_id, WebSocketMessage(
                    type=MessageType.ACK,
                    data={'action': 'unsubscribe', 'subscriptions': to_remove}
                ))
        
        elif msg_type == 'get_status':
            # 即座にステータスを送信
            await self._send_status(client_id)
        
        else:
            await self._send_error(client_id, f"Unknown message type: {msg_type}")
    
    # =========================================================================
    # ブロードキャスト
    # =========================================================================
    
    def _start_broadcast(self) -> None:
        """ブロードキャストタスクを開始"""
        if self._running:
            return
        
        self._running = True
        self._broadcast_task = asyncio.create_task(self._broadcast_loop())
        logger.info("WebSocket broadcast started")
    
    def _stop_broadcast(self) -> None:
        """ブロードキャストタスクを停止"""
        self._running = False
        if self._broadcast_task:
            self._broadcast_task.cancel()
            self._broadcast_task = None
        logger.info("WebSocket broadcast stopped")
    
    async def _broadcast_loop(self) -> None:
        """状態ブロードキャストループ"""
        while self._running:
            try:
                await self._broadcast_status()
                await asyncio.sleep(self.broadcast_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Broadcast error: {e}")
                await asyncio.sleep(1.0)  # エラー時は少し待機
    
    async def _broadcast_status(self) -> None:
        """全クライアントにステータスをブロードキャスト"""
        if not self._connections:
            return
        
        status_data = self._get_status_data()
        message = WebSocketMessage(
            type=MessageType.STATUS,
            data=status_data
        )
        
        # 購読しているクライアントにのみ送信
        for client_id, info in self._client_info.items():
            if info.is_subscribed(SubscriptionType.STATUS):
                await self._send_to_client(client_id, message)
    
    def _get_status_data(self) -> Dict[str, Any]:
        """現在のステータスデータを取得"""
        status = self.robot_manager.get_status()
        
        return {
            'state': status.state.name if hasattr(status.state, 'name') else str(status.state),
            'mode': status.mode.name if hasattr(status.mode, 'name') else str(status.mode),
            'is_initialized': status.is_initialized,
            'is_homing_complete': status.is_homing_complete,
            'is_moving': status.is_moving,
            'is_error': status.is_error,
            'error_code': status.error_code.value if hasattr(status.error_code, 'value') else int(status.error_code),
            'error_message': status.error_message,
            'current_position_name': status.current_position_name,
            'axis_positions': status.axis_positions
        }
    
    # =========================================================================
    # イベント送信
    # =========================================================================
    
    def _emit_event(self, event_type: EventType, data: Dict[str, Any]) -> None:
        """
        イベントを送信（非同期で実行）
        
        Args:
            event_type: イベントタイプ
            data: イベントデータ
        """
        asyncio.create_task(self._broadcast_event(event_type, data))
    
    async def _broadcast_event(self, event_type: EventType, data: Dict[str, Any]) -> None:
        """イベントを全クライアントにブロードキャスト"""
        message = WebSocketMessage(
            type=MessageType.EVENT,
            data={
                'event': event_type.value,
                **data
            }
        )
        
        for client_id, info in self._client_info.items():
            if info.is_subscribed(SubscriptionType.EVENTS):
                await self._send_to_client(client_id, message)
    
    # =========================================================================
    # ユーティリティ
    # =========================================================================
    
    async def _send_to_client(self, client_id: str, message: WebSocketMessage) -> bool:
        """
        クライアントにメッセージを送信
        
        Args:
            client_id: クライアントID
            message: メッセージ
            
        Returns:
            成功したかどうか
        """
        if client_id not in self._connections:
            return False
        
        try:
            await self._connections[client_id].send_text(message.to_json())
            return True
        except Exception as e:
            logger.warning(f"Failed to send to {client_id}: {e}")
            return False
    
    async def _send_status(self, client_id: str) -> None:
        """クライアントにステータスを送信"""
        message = WebSocketMessage(
            type=MessageType.STATUS,
            data=self._get_status_data()
        )
        await self._send_to_client(client_id, message)
    
    async def _send_error(self, client_id: str, error_message: str) -> None:
        """クライアントにエラーを送信"""
        message = WebSocketMessage(
            type=MessageType.ERROR,
            data={'message': error_message}
        )
        await self._send_to_client(client_id, message)
    
    # =========================================================================
    # プロパティ
    # =========================================================================
    
    @property
    def connection_count(self) -> int:
        """アクティブな接続数"""
        return len(self._connections)
    
    @property
    def is_broadcasting(self) -> bool:
        """ブロードキャスト中かどうか"""
        return self._running
    
    async def shutdown(self) -> None:
        """シャットダウン処理"""
        self._stop_broadcast()
        
        # 全クライアントに切断通知
        for client_id in list(self._connections.keys()):
            try:
                await self._send_to_client(client_id, WebSocketMessage(
                    type=MessageType.EVENT,
                    data={
                        'event': EventType.DISCONNECTED,
                        'message': 'Server shutting down'
                    }
                ))
                await self._connections[client_id].close()
            except Exception:
                pass
        
        self._connections.clear()
        self._client_info.clear()
        logger.info("WebSocket manager shut down")
