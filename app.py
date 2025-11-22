"""
自動組み立てロボット統合アプリケーション
src/モジュールを使用したWebアプリケーション
"""
import asyncio
import logging
import signal
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
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
)
from src.printer.octoprint_client import OctoPrintClient, OctoPrintError
from src.printer.printer_manager import PrinterManager

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# グローバルインスタンス
camera_manager: Optional[CameraManager] = None
gripper_manager: Optional[GripperManager] = None
webrtc_manager: Optional[WebRTCManager] = None
printer_manager: Optional[PrinterManager] = None


# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    """アプリケーションのライフサイクル管理"""
    global camera_manager, gripper_manager, webrtc_manager, printer_manager
    
    logger.info("🚀 アプリケーションを起動中...")
    
    # カメラ初期化
    try:
        camera_manager = CameraManager()
        await camera_manager.start()
        logger.info("✅ カメラサービス起動")
    except Exception as e:
        logger.error(f"❌ カメラサービス起動失敗: {e}")
        camera_manager = None
    
    # グリッパー初期化
    try:
        gripper_manager = GripperManager()
        await gripper_manager.connect()
        logger.info("✅ グリッパーサービス起動")
    except Exception as e:
        logger.error(f"❌ グリッパーサービス起動失敗: {e}")
        gripper_manager = None
    
    # WebRTC初期化
    try:
        webrtc_manager = WebRTCManager(camera_manager)
        logger.info("✅ WebRTCサービス起動")
    except Exception as e:
        logger.error(f"❌ WebRTCサービス起動失敗: {e}")
        webrtc_manager = None
    
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
    
    logger.info("🎉 すべてのサービスが起動しました")
    
    yield
    
    # シャットダウン処理
    logger.info("🛑 アプリケーションを終了中...")
    
    if webrtc_manager:
        await webrtc_manager.close_all()
    
    if camera_manager:
        await camera_manager.stop()
    
    if gripper_manager:
        await gripper_manager.disconnect()

    if printer_manager:
        await printer_manager.stop()
    
    logger.info("👋 すべてのサービスを停止しました")


# FastAPIアプリ
app = FastAPI(title="自動組み立てロボット制御システム", lifespan=lifespan)

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


# ルート
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


# カメラAPI
@app.get("/api/camera/status")
async def get_camera_status():
    """カメラ状態取得"""
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
async def get_camera_resolutions():
    """カメラ対応解像度一覧"""
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
async def get_camera_controls():
    """カメラコントロール一覧取得"""
    if not camera_manager or not camera_manager.is_opened():
        raise HTTPException(status_code=503, detail="カメラが接続されていません")
    
    try:
        controls = camera_manager.get_controls()
        return {"status": "ok", "controls": controls}
    except Exception as e:
        logger.error(f"カメラコントロール取得エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/camera/control/{name}/{value}")
async def set_camera_control(name: str, value: int):
    """カメラコントロール設定"""
    if not camera_manager or not camera_manager.is_opened():
        raise HTTPException(status_code=503, detail="カメラが接続されていません")
    
    try:
        camera_manager.set_control(name, value)
        return {"status": "ok", "name": name, "value": value}
    except Exception as e:
        logger.error(f"カメラコントロール設定エラー: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/camera/control/reset/{name}")
async def reset_camera_control(name: str):
    """カメラコントロールをデフォルト値にリセット"""
    if not camera_manager or not camera_manager.is_opened():
        raise HTTPException(status_code=503, detail="カメラが接続されていません")
    
    try:
        camera_manager.reset_control(name)
        return {"status": "ok", "name": name, "message": f"{name}をデフォルト値にリセットしました"}
    except Exception as e:
        logger.error(f"カメラコントロールリセットエラー: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/camera/controls/reset_all")
async def reset_all_camera_controls():
    """すべてのカメラコントロールをデフォルト値にリセット"""
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
async def take_snapshot():
    """スナップショット撮影"""
    if not camera_manager:
        raise HTTPException(status_code=503, detail="カメラが起動していません")
    
    result = await camera_manager.take_snapshot()
    if result is None:
        raise HTTPException(status_code=500, detail="スナップショット撮影に失敗しました")
    
    return result


@app.get("/api/camera/snapshots/{filename}")
async def get_snapshot(filename: str):
    """スナップショット取得"""
    filepath = SNAPSHOTS_DIR / filename
    if not filepath.exists():
        raise HTTPException(status_code=404, detail="ファイルが見つかりません")
    
    return FileResponse(filepath)


@app.get("/api/camera/snapshots")
async def list_snapshots():
    """スナップショット一覧取得"""
    import os
    
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
async def webrtc_offer(offer: WebRTCOffer):
    """WebRTC Offer処理"""
    if not webrtc_manager:
        raise HTTPException(status_code=503, detail="WebRTCサービスが起動していません")
    
    try:
        answer = await webrtc_manager.create_offer(offer.sdp, offer.type)
        return answer
    except Exception as e:
        logger.error(f"WebRTC Offer処理エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/camera/resolution")
async def set_camera_resolution(request: dict):
    """カメラ解像度変更"""
    if not camera_manager:
        raise HTTPException(status_code=503, detail="カメラが起動していません")
    
    try:
        width = request.get("width")
        height = request.get("height")
        fps = request.get("fps", camera_manager.settings.get("fps", 30))
        
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


# シグナルハンドラー
def signal_handler(signum, frame):
    """シグナルハンドラー（Ctrl+C対応）"""
    logger.info("終了シグナルを受信しました")
    import sys
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


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
