"""
自動組み立てロボット統合アプリケーション
src/モジュールを使用したWebアプリケーション
"""
import asyncio
import logging
import time
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager

import aiohttp
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

# src/モジュールをインポート
import sys
sys.path.insert(0, str(Path(__file__).parent))

from src.camera.camera_manager import CameraManager
from src.gripper.gripper_manager import GripperManager
from src.webrtc.webrtc_manager import WebRTCManager
from src.config.settings import (
    CAMERA_DEVICE,
    SNAPSHOTS_DIR,
    OCTOPRINT_URL,
    OCTOPRINT_API_KEY,
    OCTOPRINT_POLL_INTERVAL,
    CAMERA_REMOTE_BASE_URL,
    CAMERA_REMOTE_TIMEOUT,
    CAMERA_REMOTE_HEALTH_TTL,
    ROBOT_REMOTE_BASE_URL,
    ROBOT_REMOTE_TIMEOUT,
    ROBOT_REMOTE_HEALTH_TTL,
    ROBOT_TEACHING_DIR,
    ROBOT_POSITION_FILE,
    ROBOT_JOG_MIN_SPEED_MM_S,
    ROBOT_JOG_MAX_SPEED_MM_S,
    ROBOT_JOG_DEFAULT_SPEED_MM_S,
    ROBOT_JOG_POLL_INTERVAL,
    ROBOT_SOFT_LIMIT_MIN_MM,
    ROBOT_SOFT_LIMIT_MAX_MM,
    ROBOT_POINT_MOVE_SPEED_RATE,
)
from src.printer.octoprint_client import OctoPrintClient, OctoPrintError
from src.printer.printer_manager import PrinterManager
from src.vision.manager import VisionManager
from src.robot.teaching_manager import TeachingRobotManager

import base64
import cv2
import numpy as np
from datetime import datetime

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# グローバルインスタンス
camera_manager: Optional[CameraManager] = None
gripper_manager: Optional[GripperManager] = None
printer_manager: Optional[PrinterManager] = None
vision_manager: Optional[VisionManager] = None
robot_manager: Optional[TeachingRobotManager] = None
_services_started = False
_camera_remote_cache = {"ok": False, "ts": 0.0}
_camera_remote_monitor_task: Optional[asyncio.Task] = None
_robot_remote_cache = {"ok": False, "ts": 0.0}
_robot_remote_monitor_task: Optional[asyncio.Task] = None

def _save_detection_snapshot(image_base64: str, prefix: str) -> Optional[dict]:
    if not image_base64:
        return None
    try:
        SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{prefix}_{ts}.jpg"
        filepath = SNAPSHOTS_DIR / filename
        data = base64.b64decode(image_base64)
        with open(filepath, "wb") as f:
            f.write(data)
        return {
            "filename": filename,
            "timestamp": ts,
            "path": str(filepath),
        }
    except Exception as e:
        logger.warning(f"検出結果スナップショット保存失敗: {e}")
        return None


def _annotate_detection_text(image_base64: str, lines: list[str]) -> str:
    if not image_base64:
        return image_base64
    try:
        img_data = base64.b64decode(image_base64)
        img_array = np.frombuffer(img_data, dtype=np.uint8)
        image = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        if image is None:
            return image_base64

        h, w = image.shape[:2]
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.6
        thickness = 2
        margin = 10
        line_height = int(22 * font_scale)
        y = h - margin

        for line in reversed(lines):
            (text_w, text_h), _ = cv2.getTextSize(line, font, font_scale, thickness)
            x = max(margin, w - text_w - margin)
            cv2.rectangle(
                image,
                (x - 6, y - text_h - 6),
                (x + text_w + 6, y + 6),
                (0, 0, 0),
                -1,
            )
            cv2.putText(image, line, (x, y), font, font_scale, (255, 255, 255), thickness, cv2.LINE_AA)
            y -= (text_h + 10)

        _, buffer = cv2.imencode('.jpg', image)
        return base64.b64encode(buffer).decode('utf-8')
    except Exception:
        return image_base64


async def _check_remote_camera() -> bool:
    if not CAMERA_REMOTE_BASE_URL:
        return False
    now = time.time()
    if now - _camera_remote_cache["ts"] < CAMERA_REMOTE_HEALTH_TTL:
        return _camera_remote_cache["ok"]

    ok = False
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{CAMERA_REMOTE_BASE_URL}/api/camera/status",
                timeout=CAMERA_REMOTE_TIMEOUT,
            ) as resp:
                ok = resp.status == 200
    except Exception:
        ok = False

    _camera_remote_cache["ok"] = ok
    _camera_remote_cache["ts"] = now
    return ok


async def _check_remote_robot() -> bool:
    if not ROBOT_REMOTE_BASE_URL:
        return False
    now = time.time()
    if now - _robot_remote_cache["ts"] < ROBOT_REMOTE_HEALTH_TTL:
        return _robot_remote_cache["ok"]

    ok = False
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{ROBOT_REMOTE_BASE_URL}/health",
                timeout=ROBOT_REMOTE_TIMEOUT,
            ) as resp:
                ok = resp.status == 200
    except Exception:
        ok = False

    _robot_remote_cache["ok"] = ok
    _robot_remote_cache["ts"] = now
    return ok


async def _proxy_request(request: Request, target_path: str) -> Optional[Response]:
    if not CAMERA_REMOTE_BASE_URL:
        return None

    url = f"{CAMERA_REMOTE_BASE_URL}{target_path}"
    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in {"host", "content-length"}
    }
    body = await request.body()
    params = request.query_params

    try:
        async with aiohttp.ClientSession() as session:
            async with session.request(
                request.method,
                url,
                params=params,
                data=body,
                headers=headers,
                timeout=CAMERA_REMOTE_TIMEOUT,
            ) as resp:
                content = await resp.read()
                media_type = resp.headers.get("Content-Type")
                return Response(content=content, status_code=resp.status, media_type=media_type)
    except Exception as e:
        logger.warning(f"リモートカメラへのプロキシ失敗: {e}")
        return None


async def _proxy_robot_request(request: Request, target_path: str) -> Optional[Response]:
    if not ROBOT_REMOTE_BASE_URL:
        return None

    url = f"{ROBOT_REMOTE_BASE_URL}{target_path}"
    headers = {
        key: value
        for key, value in request.headers.items()
        if key.lower() not in {"host", "content-length"}
    }
    body = await request.body()
    params = request.query_params

    try:
        async with aiohttp.ClientSession() as session:
            async with session.request(
                request.method,
                url,
                params=params,
                data=body,
                headers=headers,
                timeout=ROBOT_REMOTE_TIMEOUT,
            ) as resp:
                content = await resp.read()
                media_type = resp.headers.get("Content-Type")
                return Response(content=content, status_code=resp.status, media_type=media_type)
    except Exception as e:
        logger.warning(f"リモートロボットへのプロキシ失敗: {e}")
        return None


# Lifespan context manager
async def _startup_services() -> None:
    global camera_manager, gripper_manager, webrtc_manager, printer_manager, vision_manager, robot_manager, _services_started
    global _camera_remote_monitor_task, _robot_remote_monitor_task

    if _services_started:
        return
    _services_started = True

    logger.info("🚀 アプリケーションを起動中...")

    remote_camera_ok = False
    if CAMERA_REMOTE_BASE_URL:
        remote_camera_ok = await _check_remote_camera()
        if remote_camera_ok:
            logger.info("📡 リモートカメラ接続を使用します（ローカルカメラは起動しません）")

    remote_robot_ok = False
    if ROBOT_REMOTE_BASE_URL:
        remote_robot_ok = await _check_remote_robot()
        logger.info("🧭 リモートロボット接続を使用します（ローカルロボットは起動しません）")

    # カメラ初期化
    if not remote_camera_ok:
        try:
            camera_manager = CameraManager()
            await camera_manager.start()
            logger.info("✅ カメラサービス起動")
        except Exception as e:
            logger.error(f"❌ カメラサービス起動失敗: {e}")
            camera_manager = None
    else:
        camera_manager = None

    # グリッパー初期化
    try:
        gripper_manager = GripperManager()
        await gripper_manager.connect()
        logger.info("✅ グリッパーサービス起動")
    except Exception as e:
        logger.error(f"❌ グリッパーサービス起動失敗: {e}")
        gripper_manager = None

    # WebRTC/画像処理初期化（ローカルカメラ使用時のみ）
    if not remote_camera_ok:
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
    else:
        webrtc_manager = None
        vision_manager = None

    # 3Dプリンター初期化
    if OCTOPRINT_URL and OCTOPRINT_API_KEY:
        printer_client: Optional[OctoPrintClient] = None
        try:
            printer_client = OctoPrintClient(OCTOPRINT_URL, OCTOPRINT_API_KEY)
            printer_manager = PrinterManager(
                printer_client,
                poll_interval=OCTOPRINT_POLL_INTERVAL,
            )
            await printer_manager.start()
            logger.info("✅ 3Dプリンターサービス起動")
        except Exception as e:
            logger.error(f"❌ 3Dプリンターサービス起動失敗: {e}")
            if printer_client:
                try:
                    await printer_client.close()
                except Exception:
                    logger.debug("OctoPrintClientクローズ時に警告", exc_info=True)
            printer_manager = None
    else:
        logger.info("ℹ️ OctoPrint設定が未定義のため3Dプリンターサービスをスキップします")

    # ロボット（TEACHING）初期化
    if not ROBOT_REMOTE_BASE_URL and not remote_robot_ok:
        try:
            robot_manager = TeachingRobotManager(
                teaching_dir=ROBOT_TEACHING_DIR,
                position_file=ROBOT_POSITION_FILE,
                soft_limit_min_mm=ROBOT_SOFT_LIMIT_MIN_MM,
                soft_limit_max_mm=ROBOT_SOFT_LIMIT_MAX_MM,
                jog_speed_min_mm_s=ROBOT_JOG_MIN_SPEED_MM_S,
                jog_speed_max_mm_s=ROBOT_JOG_MAX_SPEED_MM_S,
                jog_speed_default_mm_s=ROBOT_JOG_DEFAULT_SPEED_MM_S,
                jog_poll_interval_s=ROBOT_JOG_POLL_INTERVAL,
            )
            await asyncio.to_thread(robot_manager.connect)
            logger.info("✅ ロボットサービス起動")
        except Exception as e:
            logger.error(f"❌ ロボットサービス起動失敗: {e}")
            robot_manager = None
    else:
        robot_manager = None

    logger.info("🎉 すべてのサービスが起動しました")

    if CAMERA_REMOTE_BASE_URL and _camera_remote_monitor_task is None:
        _camera_remote_monitor_task = asyncio.create_task(_monitor_remote_camera())

    if ROBOT_REMOTE_BASE_URL and _robot_remote_monitor_task is None:
        _robot_remote_monitor_task = asyncio.create_task(_monitor_remote_robot())


async def _shutdown_services() -> None:
    global camera_manager, gripper_manager, webrtc_manager, printer_manager, vision_manager, robot_manager, _services_started
    global _camera_remote_monitor_task, _robot_remote_monitor_task

    if not _services_started:
        return
    _services_started = False

    logger.info("🛑 アプリケーションを終了中...")

    if webrtc_manager:
        await webrtc_manager.close_all()

    if camera_manager:
        await camera_manager.stop()

    if gripper_manager:
        await gripper_manager.disconnect()

    if printer_manager:
        await printer_manager.stop()

    if robot_manager:
        await asyncio.to_thread(robot_manager.close)

    if _camera_remote_monitor_task:
        _camera_remote_monitor_task.cancel()
        _camera_remote_monitor_task = None

    if _robot_remote_monitor_task:
        _robot_remote_monitor_task.cancel()
        _robot_remote_monitor_task = None

    logger.info("👋 すべてのサービスを停止しました")


async def _monitor_remote_camera() -> None:
    global camera_manager, webrtc_manager, vision_manager
    while True:
        try:
            if await _check_remote_camera():
                if camera_manager:
                    logger.info("📡 リモートカメラ接続を検出。ローカルカメラを停止します")
                    await camera_manager.stop()
                    camera_manager = None
                    webrtc_manager = None
                    vision_manager = None
        except Exception:
            pass
        await asyncio.sleep(CAMERA_REMOTE_HEALTH_TTL)


async def _monitor_remote_robot() -> None:
    global robot_manager
    while True:
        try:
            if await _check_remote_robot():
                if robot_manager:
                    logger.info("🧭 リモートロボット接続を検出。ローカルロボットを停止します")
                    await asyncio.to_thread(robot_manager.close)
                    robot_manager = None
        except Exception:
            pass
        await asyncio.sleep(ROBOT_REMOTE_HEALTH_TTL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """アプリケーションのライフサイクル管理"""
    await _startup_services()
    yield
    await _shutdown_services()


# FastAPIアプリ
app = FastAPI(title="自動組み立てロボット制御システム", lifespan=lifespan)


@app.middleware("http")
async def disable_browser_cache(request: Request, call_next):
    response = await call_next(request)
    path = request.url.path
    if path == "/" or path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


@app.on_event("startup")
async def on_startup() -> None:
    await _startup_services()


@app.on_event("shutdown")
async def on_shutdown() -> None:
    await _shutdown_services()

# 静的ファイルとテンプレート
app.mount("/static", StaticFiles(directory="web_app/static"), name="static")
templates = Jinja2Templates(directory="web_app/templates")


# Pydanticモデル
class WebRTCOffer(BaseModel):
    sdp: str
    type: str


class PositionData(BaseModel):
    position: float
    width: float
    speed: int
    accel: int
    decel: int
    push_current: int


class RobotJogRequest(BaseModel):
    axis: int
    direction: str
    speed_mm_s: Optional[float] = None


class RobotJogStopRequest(BaseModel):
    axis: int


class RobotPointRegisterRequest(BaseModel):
    point_no: int
    comment: str = ""


class RobotPointMoveRequest(BaseModel):
    point_no: int


class RobotIOOutputRequest(BaseModel):
    board_id: int
    port_no: int
    on: bool


class RobotIOInputRequest(BaseModel):
    board_id: int
    port_no: int


class RobotPositionUpdateRequest(BaseModel):
    x: float
    y: float
    z: float
    comment: str = ""


# ルート
# システムのトップページ（http://10.xx.xx.xx:8080/ など）にアクセスした際実行される
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """メインページ"""
    return templates.TemplateResponse("index_webrtc_fixed.html", {"request": request})


@app.get("/health")
async def health_check():
    """ヘルスチェック"""
    return {
        "status": "healthy",
        "camera": camera_manager.is_opened() if camera_manager else False,
        "gripper": gripper_manager.is_connected if gripper_manager else False,
        "printer": printer_manager is not None
    }


@app.get("/api/camera/remote_status")
async def camera_remote_status():
    """カメラPi接続状態"""
    connected = await _check_remote_camera()
    return {
        "enabled": bool(CAMERA_REMOTE_BASE_URL),
        "connected": connected,
        "base_url": CAMERA_REMOTE_BASE_URL or None,
    }


# カメラAPI
@app.get("/api/camera/status")
async def get_camera_status(request: Request):
    """カメラ状態取得"""
    if await _check_remote_camera():
        proxied = await _proxy_request(request, "/api/camera/status")
        if proxied:
            return proxied
    if not camera_manager:
        raise HTTPException(status_code=503, detail="カメラが起動していません")
    
    try:
        if camera_manager.is_opened():
            frame = camera_manager.get_frame()
            return {
                "status": "ok",
                "device": CAMERA_DEVICE,
                "width": camera_manager.settings["width"],
                "height": camera_manager.settings["height"],
                "fps": camera_manager.settings["fps"],
                "fourcc": camera_manager.settings["fourcc"],
                "has_frame": frame is not None
            }
        else:
            raise HTTPException(status_code=503, detail="カメラ未接続")
    except Exception as e:
        logger.error(f"カメラステータス取得エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/camera/resolutions")
async def get_camera_resolutions(request: Request):
    """カメラ対応解像度一覧"""
    if await _check_remote_camera():
        proxied = await _proxy_request(request, "/api/camera/resolutions")
        if proxied:
            return proxied
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
        "current": camera_manager.settings if camera_manager else {}
    }


@app.get("/api/camera/controls")
async def get_camera_controls(request: Request):
    """カメラコントロール一覧取得"""
    if await _check_remote_camera():
        proxied = await _proxy_request(request, "/api/camera/controls")
        if proxied:
            return proxied
    if not camera_manager or not camera_manager.is_opened():
        raise HTTPException(status_code=503, detail="カメラが接続されていません")
    
    try:
        controls = camera_manager.get_controls()
        return {"status": "ok", "controls": controls}
    except Exception as e:
        logger.error(f"カメラコントロール取得エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/camera/control/{name}/{value}")
async def set_camera_control(name: str, value: int, request: Request):
    """カメラコントロール設定"""
    if await _check_remote_camera():
        proxied = await _proxy_request(request, f"/api/camera/control/{name}/{value}")
        if proxied:
            return proxied
    if not camera_manager or not camera_manager.is_opened():
        raise HTTPException(status_code=503, detail="カメラが接続されていません")
    
    try:
        camera_manager.set_control(name, value)
        return {"status": "ok", "name": name, "value": value}
    except Exception as e:
        logger.error(f"カメラコントロール設定エラー: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/camera/control/reset/{name}")
async def reset_camera_control(name: str, request: Request):
    """カメラコントロールをデフォルト値にリセット"""
    if await _check_remote_camera():
        proxied = await _proxy_request(request, f"/api/camera/control/reset/{name}")
        if proxied:
            return proxied
    if not camera_manager or not camera_manager.is_opened():
        raise HTTPException(status_code=503, detail="カメラが接続されていません")
    
    try:
        camera_manager.reset_control(name)
        return {"status": "ok", "name": name, "message": f"{name}をデフォルト値にリセットしました"}
    except Exception as e:
        logger.error(f"カメラコントロールリセットエラー: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/camera/controls/reset_all")
async def reset_all_camera_controls(request: Request):
    """すべてのカメラコントロールをデフォルト値にリセット"""
    if await _check_remote_camera():
        proxied = await _proxy_request(request, "/api/camera/controls/reset_all")
        if proxied:
            return proxied
    if not camera_manager or not camera_manager.is_opened():
        raise HTTPException(status_code=503, detail="カメラが接続されていません")
    
    try:
        results = camera_manager.reset_all_controls()
        success_count = sum(results.values())
        total_count = len(results)
        return {
            "status": "ok",
            "message": f"{success_count}/{total_count}個のコントロールをリセットしました",
            "results": results
        }
    except Exception as e:
        logger.error(f"カメラコントロール一括リセットエラー: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/camera/snapshot")
async def take_snapshot(request: Request):
    """スナップショット撮影"""
    if await _check_remote_camera():
        proxied = await _proxy_request(request, "/api/camera/snapshot")
        if proxied:
            return proxied
    if not camera_manager:
        raise HTTPException(status_code=503, detail="カメラが起動していません")
    
    result = await camera_manager.take_snapshot()
    if result is None:
        raise HTTPException(status_code=500, detail="スナップショット撮影に失敗しました")
    
    return result


@app.get("/api/camera/snapshots/{filename}")
async def get_snapshot(filename: str, request: Request):
    """スナップショット取得"""
    if await _check_remote_camera():
        proxied = await _proxy_request(request, f"/api/camera/snapshots/{filename}")
        if proxied:
            return proxied
    filepath = SNAPSHOTS_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="ファイルが見つかりません")
    
    return FileResponse(filepath)


@app.get("/api/camera/snapshots")
async def list_snapshots(request: Request):
    """スナップショット一覧取得"""
    import os
    if await _check_remote_camera():
        proxied = await _proxy_request(request, "/api/camera/snapshots")
        if proxied:
            return proxied
    if not SNAPSHOTS_DIR.exists():
        return {"status": "ok", "snapshots": []}
    
    snapshots = []
    for filepath in sorted(SNAPSHOTS_DIR.glob("*.jpg"), reverse=True):
        stat = filepath.stat()
        snapshots.append({
            "filename": filepath.name,
            "size": stat.st_size,
            "timestamp": stat.st_mtime
        })
    
    return {"status": "ok", "snapshots": snapshots}


# WebRTC API
@app.post("/api/webrtc/offer")
async def webrtc_offer(request: Request, offer: WebRTCOffer):
    """WebRTC Offer処理"""
    if await _check_remote_camera():
        proxied = await _proxy_request(request, "/api/webrtc/offer")
        if proxied:
            return proxied
    if not webrtc_manager:
        raise HTTPException(status_code=503, detail="WebRTCサービスが起動していません")
    
    try:
        answer = await webrtc_manager.create_offer(offer.sdp, offer.type)
        return answer
    except Exception as e:
        logger.error(f"WebRTC Offer処理エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/camera/resolution")
async def set_camera_resolution(request: Request):
    """カメラ解像度変更"""
    if await _check_remote_camera():
        proxied = await _proxy_request(request, "/api/camera/resolution")
        if proxied:
            return proxied
    if not camera_manager:
        raise HTTPException(status_code=503, detail="カメラが起動していません")
    
    try:
        data = await request.json()
        width = data.get("width")
        height = data.get("height")
        fps = data.get("fps", camera_manager.settings.get("fps", 30))
        
        if width and height:
            # update_settings()が内部でstop/startを実行
            await camera_manager.update_settings(width, height, fps)
            
            return {
                "status": "ok",
                "message": f"解像度を{width}x{height}@{fps}fpsに変更しました",
                "settings": camera_manager.settings
            }
        else:
            raise HTTPException(status_code=400, detail="widthとheightが必要です")
    except Exception as e:
        logger.error(f"解像度変更エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/camera/codec")
async def change_codec(request: Request):
    """カメラコーデック変更"""
    if await _check_remote_camera():
        proxied = await _proxy_request(request, "/api/camera/codec")
        if proxied:
            return proxied
    try:
        data = await request.json()
        codec = data.get("codec", "MJPG")
        
        if codec not in ["MJPG", "YUYV"]:
            raise HTTPException(status_code=400, detail="サポートされていないコーデックです")
        
        if camera_manager:
            # カメラ設定を更新
            camera_manager.settings["fourcc"] = codec
            
            # カメラを再起動
            await camera_manager.stop()
            await camera_manager.start()
            
            return {
                "status": "ok",
                "message": f"コーデックを{codec}に変更しました"
            }
        else:
            raise HTTPException(status_code=503, detail="カメラが起動していません")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"コーデック変更エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# プリンターAPI
@app.get("/api/printer/status")
async def printer_status():
    """3Dプリンターステータス取得"""
    if not printer_manager:
        return {"status": "disabled", "message": "OctoPrintサービスが無効です"}
    try:
        status = await printer_manager.get_status()
        return {"status": "ok", "data": status}
    except OctoPrintError as e:
        logger.error(f"プリンターステータス取得エラー: {e}")
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"プリンターステータス取得エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/printer/pause")
async def printer_pause():
    """プリント一時停止"""
    if not printer_manager:
        raise HTTPException(status_code=503, detail="3Dプリンターサービスが起動していません")
    try:
        await printer_manager.pause_job()
        return {"status": "ok", "message": "一時停止コマンドを送信しました"}
    except OctoPrintError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        logger.error(f"プリンター一時停止エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/printer/resume")
async def printer_resume():
    """プリント再開"""
    if not printer_manager:
        raise HTTPException(status_code=503, detail="3Dプリンターサービスが起動していません")
    try:
        await printer_manager.resume_job()
        return {"status": "ok", "message": "再開コマンドを送信しました"}
    except OctoPrintError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        logger.error(f"プリンター再開エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@app.post("/api/printer/present_bed")
async def printer_present_bed():
    """ベッドを前に出す"""
    if not printer_manager:
        raise HTTPException(status_code=503, detail="3Dプリンターサービスが起動していません")
    try:
        await printer_manager.present_bed()
        return {"status": "ok", "message": "ベッドを前に出しました"}
    except OctoPrintError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        logger.error(f"ベッド移動エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ロボットAPI (TEACHING)
@app.get("/api/robot/config")
async def robot_config(request: Request):
    """ロボット設定取得"""
    if await _check_remote_robot():
        proxied = await _proxy_robot_request(request, "/api/robot/config")
        if proxied:
            return proxied
    if not robot_manager:
        raise HTTPException(status_code=503, detail="ロボットサービスが起動していません")
    return robot_manager.get_config()


@app.get("/api/robot/diagnostics")
async def robot_diagnostics(request: Request):
    if await _check_remote_robot():
        proxied = await _proxy_robot_request(request, "/api/robot/diagnostics")
        if proxied:
            return proxied
    if not robot_manager:
        raise HTTPException(status_code=503, detail="ロボットサービスが起動していません")
    return {
        "emg": robot_manager.get_emg_status(),
        "positions": robot_manager.get_positions(),
    }


@app.post("/api/robot/home")
async def robot_home(request: Request):
    """原点復帰"""
    if await _check_remote_robot():
        proxied = await _proxy_robot_request(request, "/api/robot/home")
        if proxied:
            return proxied
    if not robot_manager:
        raise HTTPException(status_code=503, detail="ロボットサービスが起動していません")
    try:
        await asyncio.to_thread(robot_manager.home)
        return {"status": "ok", "message": "原点復帰を開始しました"}
    except Exception as e:
        logger.error(f"ロボット原点復帰エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/robot/jog/start")
async def robot_jog_start(request: RobotJogRequest, raw_request: Request):
    """JOG開始（押下中のみ動作）"""
    if await _check_remote_robot():
        proxied = await _proxy_robot_request(raw_request, "/api/robot/jog/start")
        if proxied:
            return proxied
    if not robot_manager:
        raise HTTPException(status_code=503, detail="ロボットサービスが起動していません")

    direction = request.direction.lower()
    if direction not in ("positive", "negative"):
        raise HTTPException(status_code=400, detail="directionは'positive'または'negative'を指定してください")

    speed_mm_s = request.speed_mm_s if request.speed_mm_s is not None else ROBOT_JOG_DEFAULT_SPEED_MM_S

    try:
        await asyncio.to_thread(
            robot_manager.jog_start,
            request.axis,
            direction == "negative",
            speed_mm_s,
        )
        return {"status": "ok", "axis": request.axis, "direction": direction, "speed_mm_s": speed_mm_s}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"ロボットJOG開始エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/robot/jog/stop")
async def robot_jog_stop(request: RobotJogStopRequest, raw_request: Request):
    """JOG停止"""
    if await _check_remote_robot():
        proxied = await _proxy_robot_request(raw_request, "/api/robot/jog/stop")
        if proxied:
            return proxied
    if not robot_manager:
        raise HTTPException(status_code=503, detail="ロボットサービスが起動していません")
    try:
        await asyncio.to_thread(robot_manager.jog_stop, request.axis)
        return {"status": "ok", "axis": request.axis}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"ロボットJOG停止エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/robot/stop")
async def robot_stop_all(request: Request):
    """全停止"""
    if await _check_remote_robot():
        proxied = await _proxy_robot_request(request, "/api/robot/stop")
        if proxied:
            return proxied
    if not robot_manager:
        raise HTTPException(status_code=503, detail="ロボットサービスが起動していません")
    try:
        await asyncio.to_thread(robot_manager.stop_all)
        return {"status": "ok", "message": "停止コマンドを送信しました"}
    except Exception as e:
        logger.error(f"ロボット停止エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/robot/point/register")
async def robot_point_register(request: RobotPointRegisterRequest, raw_request: Request):
    """現在位置をポイント登録"""
    if await _check_remote_robot():
        proxied = await _proxy_robot_request(raw_request, "/api/robot/point/register")
        if proxied:
            return proxied
    if not robot_manager:
        raise HTTPException(status_code=503, detail="ロボットサービスが起動していません")
    try:
        result = await asyncio.to_thread(
            robot_manager.register_point_from_current,
            request.point_no,
            request.comment,
        )
        return {"status": "ok", "data": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"ポイント登録エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/robot/point/move")
async def robot_point_move(request: RobotPointMoveRequest, raw_request: Request):
    """ポイント移動"""
    if await _check_remote_robot():
        proxied = await _proxy_robot_request(raw_request, "/api/robot/point/move")
        if proxied:
            return proxied
    if not robot_manager:
        raise HTTPException(status_code=503, detail="ロボットサービスが起動していません")
    try:
        await asyncio.to_thread(
            robot_manager.move_to_point,
            request.point_no,
            ROBOT_POINT_MOVE_SPEED_RATE,
        )
        return {"status": "ok", "point_no": request.point_no, "speed_rate": ROBOT_POINT_MOVE_SPEED_RATE}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"ポイント移動エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/robot/io/output")
async def robot_io_output(request: RobotIOOutputRequest, raw_request: Request):
    """CAN-IO出力 - robot_daemonにプロキシ"""
    # まず robot_daemon へプロキシを試す
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"http://localhost:8081/api/robot/io/output",
                json={"board_id": request.board_id, "port_no": request.port_no, "on": request.on},
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
    except Exception as e:
        logger.warning(f"robot_daemon IO出力失敗、app.pyで処理試行: {e}")
    
    # robot_daemonが失敗した場合、app.pyの robot_manager を試す
    if await _check_remote_robot():
        proxied = await _proxy_robot_request(raw_request, "/api/robot/io/output")
        if proxied:
            return proxied
    if not robot_manager:
        raise HTTPException(status_code=503, detail="ロボットサービスが起動していません")
    try:
        result = await asyncio.to_thread(
            robot_manager.io_output,
            request.board_id,
            request.port_no,
            request.on,
        )
        return {"status": "ok", "result": result}
    except Exception as e:
        logger.error(f"IO出力エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/robot/io/input")
async def robot_io_input(request: RobotIOInputRequest, raw_request: Request):
    """CAN-IO入力状態取得 - robot_daemonにプロキシ"""
    # まず robot_daemon へプロキシを試す
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"http://localhost:8081/api/robot/io/input",
                json={"board_id": request.board_id, "port_no": request.port_no},
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
    except Exception as e:
        logger.warning(f"robot_daemon IO入力取得失敗、app.pyで処理試行: {e}")
    
    # robot_daemonが失敗した場合、app.pyの robot_manager を試す
    if await _check_remote_robot():
        proxied = await _proxy_robot_request(raw_request, "/api/robot/io/input")
        if proxied:
            return proxied
    if not robot_manager:
        raise HTTPException(status_code=503, detail="ロボットサービスが起動していません")
    try:
        result = await asyncio.to_thread(
            robot_manager.io_input,
            request.board_id,
            request.port_no,
        )
        return {"status": "ok", "result": result}
    except Exception as e:
        logger.error(f"IO入力取得エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/robot/position_table")
async def robot_position_table_all(request: Request):
    """ポジションテーブル全件取得"""
    if await _check_remote_robot():
        proxied = await _proxy_robot_request(request, "/api/robot/position_table")
        if proxied:
            return proxied
    if not robot_manager:
        raise HTTPException(status_code=503, detail="ロボットサービスが起動していません")
    try:
        return {"status": "ok", "data": robot_manager.get_position_table_all()}
    except Exception as e:
        logger.error(f"ポジションテーブル取得エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/robot/position_table/{point_no}")
async def robot_position_table_point(point_no: int, request: Request):
    """ポジションテーブル取得"""
    if await _check_remote_robot():
        proxied = await _proxy_robot_request(request, f"/api/robot/position_table/{point_no}")
        if proxied:
            return proxied
    if not robot_manager:
        raise HTTPException(status_code=503, detail="ロボットサービスが起動していません")
    try:
        return {"status": "ok", "data": robot_manager.get_position_table_point(point_no)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"ポジションテーブル取得エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/robot/position_table/{point_no}")
async def robot_position_table_update(point_no: int, request: RobotPositionUpdateRequest, raw_request: Request):
    """ポジションテーブル更新"""
    if await _check_remote_robot():
        proxied = await _proxy_robot_request(raw_request, f"/api/robot/position_table/{point_no}")
        if proxied:
            return proxied
    if not robot_manager:
        raise HTTPException(status_code=503, detail="ロボットサービスが起動していません")
    try:
        data = await asyncio.to_thread(
            robot_manager.update_position_table_point,
            point_no,
            request.x,
            request.y,
            request.z,
            request.comment,
        )
        return {"status": "ok", "data": data}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"ポジションテーブル更新エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# グリッパーAPI
@app.get("/api/gripper/status")
async def gripper_status():
    """グリッパーステータス取得"""
    if not gripper_manager or not gripper_manager.is_connected:
        raise HTTPException(status_code=503, detail="グリッパーが接続されていません")
    
    try:
        status = await gripper_manager.get_status()
        return status
    except Exception as e:
        logger.error(f"グリッパーステータス取得エラー: {e}")
        raise HTTPException(status_code=503, detail=str(e))


@app.post("/api/gripper/servo/{action}")
async def gripper_servo(action: str):
    """サーボON/OFF"""
    if not gripper_manager or not gripper_manager.is_connected:
        raise HTTPException(status_code=503, detail="グリッパーが接続されていません")
    
    try:
        if action == "on":
            await gripper_manager.servo_on()
        elif action == "off":
            await gripper_manager.servo_off()
        else:
            raise HTTPException(status_code=400, detail="actionは'on'または'off'を指定してください")
        
        return {"status": "ok", "action": action}
    except Exception as e:
        logger.error(f"サーボ制御エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/gripper/home")
async def gripper_home():
    """原点復帰"""
    if not gripper_manager or not gripper_manager.is_connected:
        raise HTTPException(status_code=503, detail="グリッパーが接続されていません")
    
    try:
        await gripper_manager.home()
        return {"status": "ok", "message": "原点復帰を開始しました"}
    except Exception as e:
        logger.error(f"原点復帰エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/gripper/move/{position}")
async def gripper_move(position: int):
    """ポジション移動"""
    if not gripper_manager or not gripper_manager.is_connected:
        raise HTTPException(status_code=503, detail="グリッパーが接続されていません")
    
    try:
        await gripper_manager.move_to_position(position)
        return {"status": "ok", "position": position}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"ポジション移動エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/gripper/position_table/{position}")
async def get_position_table(position: int):
    """ポジションテーブル取得"""
    if not gripper_manager or not gripper_manager.is_connected:
        raise HTTPException(status_code=503, detail="グリッパーが接続されていません")
    
    try:
        data = await gripper_manager.get_position_table(position)
        return {"status": "ok", "position": position, "data": data}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"ポジションテーブル取得エラー: {e}")
        raise HTTPException(status_code=503, detail=str(e))


@app.post("/api/gripper/position_table/{position}")
async def update_position_table(position: int, request: Request):
    """ポジションテーブル更新"""
    if not gripper_manager or not gripper_manager.is_connected:
        raise HTTPException(status_code=503, detail="グリッパーが接続されていません")
    
    try:
        data = await request.json()
        position_dict = {
            "position": data.get("position_mm"),
            "width": data.get("width_mm"),
            "speed": data.get("speed_mm_s"),
            "accel": data.get("accel_g"),
            "decel": data.get("decel_g"),
            "push_current": data.get("push_current_percent", 0)
        }
        await gripper_manager.update_position_table(position, position_dict)
        return {"status": "ok", "message": f"ポジション{position}のデータを設定しました"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"ポジションテーブル更新エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/gripper/current")
async def gripper_current():
    """電流値取得"""
    if not gripper_manager or not gripper_manager.is_connected:
        raise HTTPException(status_code=503, detail="グリッパーが接続されていません")
    
    try:
        current = await gripper_manager.get_current()
        return {"status": "ok", "current": current}
    except Exception as e:
        logger.error(f"電流値取得エラー: {e}")
        raise HTTPException(status_code=503, detail=str(e))


@app.get("/api/gripper/grip_status")
async def gripper_grip_status(target_position: int = None):
    """把持状態判定"""
    if not gripper_manager or not gripper_manager.is_connected:
        raise HTTPException(status_code=503, detail="グリッパーが接続されていません")
    
    try:
        status = await gripper_manager.check_grip_status(target_position)
        return status
    except Exception as e:
        logger.error(f"把持状態判定エラー: {e}")
        raise HTTPException(status_code=503, detail=str(e))

# 画像処理API
@app.post("/api/vision/detect/fiber")
async def detect_fiber(request: Request):
    """ファイバー検出を実行"""
    if await _check_remote_camera():
        proxied = await _proxy_request(request, "/api/vision/detect/fiber")
        if proxied:
            return proxied
    if not camera_manager or not vision_manager:
        raise HTTPException(status_code=503, detail="サービスが利用できません")
    
    frame = camera_manager.get_frame()
    if frame is None:
        raise HTTPException(status_code=500, detail="画像の取得に失敗しました")
    
    try:
        result = vision_manager.detect_fiber(frame)
        lines = [f"Fiber detected: {result.get('detected')}"
                 f", count: {result.get('count', 0)}"]
        offset = result.get("offset")
        if offset:
            lines.append(f"dx: {offset.get('dx', 0):.2f}, dy: {offset.get('dy', 0):.2f}")
        annotated = _annotate_detection_text(result.get("image_base64", ""), lines)
        result["image_base64"] = annotated
        snapshot = _save_detection_snapshot(annotated, "fiber")
        if snapshot:
            result["snapshot"] = snapshot
        return result
    except Exception as e:
        logger.error(f"ファイバー検出エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/vision/detect/bead")
async def detect_bead(request: Request):
    """ビーズ検出を実行"""
    if await _check_remote_camera():
        proxied = await _proxy_request(request, "/api/vision/detect/bead")
        if proxied:
            return proxied
    if not camera_manager or not vision_manager:
        raise HTTPException(status_code=503, detail="サービスが利用できません")
    
    frame = camera_manager.get_frame()
    if frame is None:
        raise HTTPException(status_code=500, detail="画像の取得に失敗しました")
    
    try:
        result = vision_manager.detect_bead(frame)
        lines = [f"Bead detected: {result.get('detected')}"
                 f", count: {result.get('count', 0)}"]
        offset = result.get("offset")
        if offset:
            lines.append(f"dx: {offset.get('dx', 0):.2f}, dy: {offset.get('dy', 0):.2f}")
        annotated = _annotate_detection_text(result.get("image_base64", ""), lines)
        result["image_base64"] = annotated
        snapshot = _save_detection_snapshot(annotated, "bead")
        if snapshot:
            result["snapshot"] = snapshot
        return result
    except Exception as e:
        logger.error(f"ビーズ検出エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    
    logger.info("=" * 60)
    logger.info("自動組み立てロボット制御システム")
    logger.info("=" * 60)
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8080,
        log_level="info"
    )

