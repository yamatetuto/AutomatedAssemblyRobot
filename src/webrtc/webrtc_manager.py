"""
WebRTC管理モジュール
aiortcを使ったWebRTC接続管理を提供
"""
import asyncio
import logging
from typing import Set
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from av import VideoFrame
import numpy as np

logger = logging.getLogger(__name__)


class VideoTrack(VideoStreamTrack):
    """カメラフレームをWebRTCで配信するためのVideoTrack"""
    
    def __init__(self, camera_manager):
        super().__init__()
        self.camera_manager = camera_manager
    
    async def recv(self):
        """フレームを取得してWebRTCに送信"""
        pts, time_base = await self.next_timestamp()
        
        frame = self.camera_manager.get_frame()
        if frame is None:
            # ダミーフレーム（黒画面）を返す
            img = np.zeros((480, 640, 3), dtype=np.uint8)
        else:
            img = frame
        
        # OpenCV (BGR) -> VideoFrame (RGB)
        img_rgb = img[:, :, ::-1]
        video_frame = VideoFrame.from_ndarray(img_rgb, format="rgb24")
        video_frame.pts = pts
        video_frame.time_base = time_base
        
        return video_frame


class WebRTCManager:
    """WebRTC接続管理クラス"""
    
    def __init__(self, camera_manager):
        self.camera_manager = camera_manager
        self.peer_connections: Set[RTCPeerConnection] = set()
    
    async def create_offer(self, sdp: str, type: str) -> dict:
        """
        WebRTC Offerを処理してAnswerを返す
        
        Args:
            sdp: Session Description Protocol
            type: "offer"
        
        Returns:
            dict: {"sdp": str, "type": "answer"}
        """
        offer = RTCSessionDescription(sdp=sdp, type=type)
        
        # RTCPeerConnection作成（引数なし）
        pc = RTCPeerConnection()
        self.peer_connections.add(pc)
        
        @pc.on("connectionstatechange")
        async def on_connectionstatechange():
            logger.info(f"WebRTC接続状態: {pc.connectionState}")
            if pc.connectionState in ["failed", "closed"]:
                await self.close_peer_connection(pc)
        
        # VideoTrackを追加
        video_track = VideoTrack(self.camera_manager)
        pc.addTrack(video_track)
        
        # Offerを設定
        await pc.setRemoteDescription(offer)
        
        # Answerを生成
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)
        
        logger.info("WebRTC Answerを生成しました")
        
        return {
            "sdp": pc.localDescription.sdp,
            "type": pc.localDescription.type
        }
    
    async def close_peer_connection(self, pc: RTCPeerConnection):
        """特定のPeerConnectionを閉じる"""
        try:
            await pc.close()
            self.peer_connections.discard(pc)
            logger.info("WebRTC接続を閉じました")
        except Exception as e:
            logger.error(f"WebRTC接続終了エラー: {e}")
    
    async def close_all(self):
        """すべてのPeerConnectionを閉じる"""
        coros = [pc.close() for pc in self.peer_connections]
        await asyncio.gather(*coros, return_exceptions=True)
        self.peer_connections.clear()
        logger.info("すべてのWebRTC接続を閉じました")
