"""Camera Service - カメラストリーミングとスナップショット管理"""
import sys
import os
import signal
import asyncio
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# 親ディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import cv2
import numpy as np
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
from av import VideoFrame

from shared.config import load_config
from shared.logger import setup_logger
from shared.schemas import HealthCheck, SnapshotInfo, CameraControl


# 設定とロガーの初期化
config = load_config("camera")
logger = setup_logger(
    service_name=config.get("service.name", "camera"),
    log_level=config.get("logging.level", "INFO"),
    log_dir=config.get("logging.directory")
)

# FastAPIアプリ
app = FastAPI(title="Camera Service", version=config.get("service.version", "1.0.0"))

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# グローバル変数
camera = None
shared_frame = None
pcs = set()  # RTCPeerConnection set

# カメラデバイス設定
CAMERA_DEVICE = config.get_int("camera.device", 0)
CAMERA_WIDTH = config.get_int("camera.width", 640)
CAMERA_HEIGHT = config.get_int("camera.height", 480)
CAMERA_FPS = config.get_int("camera.fps", 30)
SNAPSHOTS_DIR = Path(config.get("snapshots.directory", "./snapshots"))
SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)


class CameraVideoTrack(VideoStreamTrack):
    """WebRTC用カメラビデオトラック"""
    
    def __init__(self):
        super().__init__()
        self.counter = 0
    
    async def recv(self):
        global shared_frame
        pts, time_base = await self.next_timestamp()
        
        if shared_frame is not None:
            frame = shared_frame.copy()
        else:
            # フレームがない場合は黒フレームを返す
            frame = np.zeros((CAMERA_HEIGHT, CAMERA_WIDTH, 3), dtype=np.uint8)
        
        # BGRからRGBに変換
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # VideoFrameに変換
        video_frame = VideoFrame.from_ndarray(frame, format="rgb24")
        video_frame.pts = pts
        video_frame.time_base = time_base
        
        return video_frame


async def camera_capture_loop():
    """カメラキャプチャループ"""
    global camera, shared_frame
    
    logger.info(f"カメラ起動: device={CAMERA_DEVICE}, {CAMERA_WIDTH}x{CAMERA_HEIGHT}@{CAMERA_FPS}fps")
    
    camera = cv2.VideoCapture(CAMERA_DEVICE)
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
    camera.set(cv2.CAP_PROP_FPS, CAMERA_FPS)
    
    # コーデック設定
    codec = config.get("camera.codec", "MJPEG")
    if codec == "MJPEG":
        camera.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
    
    if not camera.isOpened():
        logger.error(f"カメラを開けませんでした: /dev/video{CAMERA_DEVICE}")
        return
    
    logger.info("カメラキャプチャループ開始")
    
    try:
        while True:
            ret, frame = camera.read()
            if ret:
                shared_frame = frame
            await asyncio.sleep(1 / CAMERA_FPS)  # フレームレート制御
    except asyncio.CancelledError:
        logger.info("カメラキャプチャループ停止")
    finally:
        if camera:
            camera.release()
            logger.info("カメラリリース完了")


def reset_camera_parameters():
    """カメラパラメータをデフォルト値にリセット"""
    logger.info("カメラパラメータをリセット中...")
    try:
        params_to_reset = {
            'brightness': 128,
            'contrast': 128,
            'saturation': 128,
            'hue': 0,
            'white_balance_temperature_auto': 1,
            'gamma': 100,
            'power_line_frequency': 1,
            'white_balance_temperature': 4000,
            'sharpness': 128,
            'backlight_compensation': 1,
            'exposure_auto': 3,
            'exposure_absolute': 166,
            'exposure_auto_priority': 0,
            'pan_absolute': 0,
            'tilt_absolute': 0,
            'zoom_absolute': 100,
            'focus_auto': 1
        }
        
        for param, value in params_to_reset.items():
            try:
                subprocess.run(
                    ['v4l2-ctl', '-d', f'/dev/video{CAMERA_DEVICE}', '--set-ctrl', f'{param}={value}'],
                    check=False,
                    capture_output=True
                )
            except Exception as e:
                logger.warning(f"パラメータ {param} のリセット失敗: {e}")
        
        logger.info("カメラパラメータリセット完了")
    except Exception as e:
        logger.error(f"カメラリセットエラー: {e}")


def signal_handler(signum, frame):
    """シグナルハンドラ（SIGTERM/SIGINT）"""
    logger.info(f"シグナル受信: {signum}")
    reset_camera_parameters()
    sys.exit(0)


# シグナルハンドラ登録
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)


@app.on_event("startup")
async def startup_event():
    """起動時処理"""
    logger.info("Camera Service起動")
    asyncio.create_task(camera_capture_loop())


@app.on_event("shutdown")
async def shutdown_event():
    """終了時処理"""
    logger.info("Camera Service終了")
    reset_camera_parameters()
    
    # WebRTC接続を閉じる
    coros = [pc.close() for pc in pcs]
    await asyncio.gather(*coros)
    pcs.clear()


@app.get("/health", response_model=HealthCheck)
async def health_check():
    """ヘルスチェック"""
    return HealthCheck(
        service=config.get("service.name", "camera"),
        status="healthy" if camera and camera.isOpened() else "unhealthy",
        version=config.get("service.version", "1.0.0"),
        timestamp=datetime.now()
    )


@app.post("/offer")
async def offer(params: dict):
    """WebRTC Offer処理"""
    offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])
    
    pc = RTCPeerConnection()
    pcs.add(pc)
    
    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        logger.info(f"Connection state: {pc.connectionState}")
        if pc.connectionState == "failed" or pc.connectionState == "closed":
            await pc.close()
            pcs.discard(pc)
    
    # カメラトラックを追加
    video_track = CameraVideoTrack()
    pc.addTrack(video_track)
    
    await pc.setRemoteDescription(offer)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)
    
    return JSONResponse({
        "sdp": pc.localDescription.sdp,
        "type": pc.localDescription.type
    })


@app.post("/snapshot")
async def take_snapshot():
    """スナップショット撮影"""
    global shared_frame
    
    if shared_frame is None:
        raise HTTPException(status_code=500, detail="カメラフレームが利用できません")
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"snapshot_{timestamp}.jpg"
    filepath = SNAPSHOTS_DIR / filename
    
    cv2.imwrite(str(filepath), shared_frame)
    logger.info(f"スナップショット保存: {filename}")
    
    return SnapshotInfo(
        filename=filename,
        timestamp=timestamp,
        url=f"/snapshots/{filename}"
    )


@app.get("/snapshots", response_model=List[SnapshotInfo])
async def list_snapshots():
    """スナップショット一覧"""
    snapshots = []
    for filepath in sorted(SNAPSHOTS_DIR.glob("*.jpg"), reverse=True):
        snapshots.append(SnapshotInfo(
            filename=filepath.name,
            timestamp=filepath.stem.replace("snapshot_", ""),
            url=f"/snapshots/{filepath.name}"
        ))
    return snapshots


@app.get("/snapshots/{filename}")
async def get_snapshot(filename: str):
    """スナップショット取得"""
    filepath = SNAPSHOTS_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="ファイルが見つかりません")
    return FileResponse(filepath)


@app.get("/controls", response_model=List[CameraControl])
async def get_camera_controls():
    """カメラコントロール一覧取得"""
    try:
        result = subprocess.run(
            ['v4l2-ctl', '-d', f'/dev/video{CAMERA_DEVICE}', '--list-ctrls'],
            capture_output=True,
            text=True,
            check=True
        )
        
        controls = []
        for line in result.stdout.split('\n'):
            if ':' in line:
                # パース処理（簡略化）
                # 実際には既存のweb_app/main_webrtc_fixed.pyのロジックを使用
                pass
        
        return controls
    except Exception as e:
        logger.error(f"コントロール取得エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/control/{name}/{value}")
async def set_camera_control(name: str, value: int):
    """カメラコントロール設定"""
    try:
        subprocess.run(
            ['v4l2-ctl', '-d', f'/dev/video{CAMERA_DEVICE}', '--set-ctrl', f'{name}={value}'],
            check=True,
            capture_output=True
        )
        logger.info(f"カメラコントロール設定: {name}={value}")
        return {"status": "ok", "name": name, "value": value}
    except subprocess.CalledProcessError as e:
        logger.error(f"コントロール設定エラー: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/resolution")
async def set_resolution(width: int, height: int, fps: int = 30):
    """解像度変更（再起動が必要）"""
    global CAMERA_WIDTH, CAMERA_HEIGHT, CAMERA_FPS
    
    CAMERA_WIDTH = width
    CAMERA_HEIGHT = height
    CAMERA_FPS = fps
    
    # カメラを再初期化
    if camera:
        camera.release()
    
    logger.info(f"解像度変更: {width}x{height}@{fps}fps（再起動してください）")
    return {"status": "ok", "message": "サービスを再起動してください"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=config.get("service.host", "0.0.0.0"),
        port=config.get_int("service.port", 8001),
        log_level=config.get("logging.level", "info").lower()
    )
