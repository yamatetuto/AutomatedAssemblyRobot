"""Camera-only service for the camera Pi (camera/webrtc/vision)."""
import asyncio
import logging
import signal
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel

from src.camera.camera_manager import CameraManager
from src.webrtc.webrtc_manager import WebRTCManager
from src.vision.manager import VisionManager
from src.config.settings import CAMERA_DEVICE, SNAPSHOTS_DIR

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

camera_manager: Optional[CameraManager] = None
webrtc_manager: Optional[WebRTCManager] = None
vision_manager: Optional[VisionManager] = None
_services_started = False


class WebRTCOffer(BaseModel):
    sdp: str
    type: str


async def _startup_services() -> None:
    global camera_manager, webrtc_manager, vision_manager, _services_started
    if _services_started:
        return
    _services_started = True

    logger.info("🚀 カメラサービスを起動中...")

    try:
        camera_manager = CameraManager()
        await camera_manager.start()
        logger.info("✅ カメラサービス起動")
    except Exception as e:
        logger.error(f"❌ カメラサービス起動失敗: {e}")
        camera_manager = None

    try:
        webrtc_manager = WebRTCManager(camera_manager)
        logger.info("✅ WebRTCサービス起動")
    except Exception as e:
        logger.error(f"❌ WebRTCサービス起動失敗: {e}")
        webrtc_manager = None

    try:
        vision_manager = VisionManager()
        logger.info("✅ 画像処理サービス起動")
    except Exception as e:
        logger.error(f"❌ 画像処理サービス起動失敗: {e}")
        vision_manager = None

    logger.info("🎉 カメラサービス起動完了")


async def _shutdown_services() -> None:
    global camera_manager, webrtc_manager, vision_manager, _services_started
    if not _services_started:
        return
    _services_started = False

    logger.info("🛑 カメラサービスを終了中...")

    if webrtc_manager:
        await webrtc_manager.close_all()

    if camera_manager:
        await camera_manager.stop()

    logger.info("👋 カメラサービスを停止しました")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await _startup_services()
    yield
    await _shutdown_services()


app = FastAPI(title="Camera Service", lifespan=lifespan)


@app.on_event("startup")
async def on_startup() -> None:
    await _startup_services()


@app.on_event("shutdown")
async def on_shutdown() -> None:
    await _shutdown_services()


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "camera": camera_manager.is_opened() if camera_manager else False,
    }


@app.get("/api/camera/status")
async def get_camera_status():
    if not camera_manager:
        raise HTTPException(status_code=503, detail="カメラが起動していません")

    if camera_manager.is_opened():
        frame = camera_manager.get_frame()
        return {
            "status": "ok",
            "device": CAMERA_DEVICE,
            "width": camera_manager.settings["width"],
            "height": camera_manager.settings["height"],
            "fps": camera_manager.settings["fps"],
            "fourcc": camera_manager.settings["fourcc"],
            "has_frame": frame is not None,
        }

    raise HTTPException(status_code=503, detail="カメラ未接続")


@app.get("/api/camera/resolutions")
async def get_camera_resolutions():
    common_resolutions = [
        {"width": 320, "height": 240, "label": "QVGA (320x240)"},
        {"width": 640, "height": 480, "label": "VGA (640x480)"},
        {"width": 800, "height": 600, "label": "SVGA (800x600)"},
        {"width": 1280, "height": 720, "label": "HD (1280x720)"},
        {"width": 1920, "height": 1080, "label": "Full HD (1920x1080)"},
    ]

    return {
        "status": "ok",
        "resolutions": common_resolutions,
        "current": camera_manager.settings if camera_manager else {},
    }


@app.get("/api/camera/controls")
async def get_camera_controls():
    if not camera_manager or not camera_manager.is_opened():
        raise HTTPException(status_code=503, detail="カメラが接続されていません")

    controls = camera_manager.get_controls()
    return {"status": "ok", "controls": controls}


@app.post("/api/camera/control/{name}/{value}")
async def set_camera_control(name: str, value: int):
    if not camera_manager or not camera_manager.is_opened():
        raise HTTPException(status_code=503, detail="カメラが接続されていません")

    camera_manager.set_control(name, value)
    return {"status": "ok", "name": name, "value": value}


@app.post("/api/camera/control/reset/{name}")
async def reset_camera_control(name: str):
    if not camera_manager or not camera_manager.is_opened():
        raise HTTPException(status_code=503, detail="カメラが接続されていません")

    camera_manager.reset_control(name)
    return {"status": "ok", "name": name, "message": f"{name}をデフォルト値にリセットしました"}


@app.post("/api/camera/controls/reset_all")
async def reset_all_camera_controls():
    if not camera_manager or not camera_manager.is_opened():
        raise HTTPException(status_code=503, detail="カメラが接続されていません")

    results = camera_manager.reset_all_controls()
    success_count = sum(results.values())
    total_count = len(results)
    return {
        "status": "ok",
        "message": f"{success_count}/{total_count}個のコントロールをリセットしました",
        "results": results,
    }


@app.post("/api/camera/snapshot")
async def take_snapshot():
    if not camera_manager:
        raise HTTPException(status_code=503, detail="カメラが起動していません")

    result = await camera_manager.take_snapshot()
    if result is None:
        raise HTTPException(status_code=500, detail="スナップショット撮影に失敗しました")

    return result


@app.get("/api/camera/snapshots/{filename}")
async def get_snapshot(filename: str):
    filepath = SNAPSHOTS_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="ファイルが見つかりません")

    return FileResponse(filepath)


@app.get("/api/camera/snapshots")
async def list_snapshots():
    if not SNAPSHOTS_DIR.exists():
        return {"status": "ok", "snapshots": []}

    snapshots = []
    for filepath in sorted(SNAPSHOTS_DIR.glob("*.jpg"), reverse=True):
        stat = filepath.stat()
        snapshots.append({
            "filename": filepath.name,
            "size": stat.st_size,
            "timestamp": stat.st_mtime,
        })

    return {"status": "ok", "snapshots": snapshots}


@app.post("/api/webrtc/offer")
async def webrtc_offer(offer: WebRTCOffer):
    if not webrtc_manager:
        raise HTTPException(status_code=503, detail="WebRTCサービスが起動していません")

    answer = await webrtc_manager.create_offer(offer.sdp, offer.type)
    return answer


@app.post("/api/camera/resolution")
async def set_camera_resolution(request: dict):
    if not camera_manager:
        raise HTTPException(status_code=503, detail="カメラが起動していません")

    width = request.get("width")
    height = request.get("height")
    fps = request.get("fps", camera_manager.settings.get("fps", 30))

    if width and height:
        await camera_manager.update_settings(width, height, fps)
        return {
            "status": "ok",
            "message": f"解像度を{width}x{height}@{fps}fpsに変更しました",
            "settings": camera_manager.settings,
        }

    raise HTTPException(status_code=400, detail="widthとheightが必要です")


@app.post("/api/camera/codec")
async def change_codec(request: Request):
    data = await request.json()
    codec = data.get("codec", "MJPG")

    if codec not in ["MJPG", "YUYV"]:
        raise HTTPException(status_code=400, detail="サポートされていないコーデックです")

    if not camera_manager:
        raise HTTPException(status_code=503, detail="カメラが起動していません")

    camera_manager.settings["fourcc"] = codec
    await camera_manager.stop()
    await camera_manager.start()

    return {"status": "ok", "message": f"コーデックを{codec}に変更しました"}


@app.post("/api/vision/detect/fiber")
async def detect_fiber():
    if not camera_manager or not vision_manager:
        raise HTTPException(status_code=503, detail="サービスが利用できません")

    frame = camera_manager.get_frame()
    if frame is None:
        raise HTTPException(status_code=500, detail="画像の取得に失敗しました")

    return vision_manager.detect_fiber(frame)


@app.post("/api/vision/detect/bead")
async def detect_bead():
    if not camera_manager or not vision_manager:
        raise HTTPException(status_code=503, detail="サービスが利用できません")

    frame = camera_manager.get_frame()
    if frame is None:
        raise HTTPException(status_code=500, detail="画像の取得に失敗しました")

    return vision_manager.detect_bead(frame)


# シグナルハンドラー
def signal_handler(signum, frame):
    logger.info("終了シグナルを受信しました")
    raise SystemExit(0)


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8080,
        log_level="info",
    )
