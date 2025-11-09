"""Gripper Service - IAI電動グリッパー制御"""
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import asyncio

# 親ディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from shared.config import load_config
from shared.logger import setup_logger
from shared.schemas import HealthCheck, GripperStatus, PositionData, PositionTableEntry
from controller.CONController import CONController


# 設定とロガーの初期化
config = load_config("gripper")
logger = setup_logger(
    service_name=config.get("service.name", "gripper"),
    log_level=config.get("logging.level", "INFO"),
    log_dir=config.get("logging.directory")
)

# FastAPIアプリ
app = FastAPI(title="Gripper Service", version=config.get("service.version", "1.0.0"))

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# グリッパーコントローラ
gripper: Optional[CONController] = None

# グリッパー設定
GRIPPER_PORT = config.get("gripper.port", "/dev/ttyUSB0")
GRIPPER_SLAVE_ADDRESS = config.get_int("gripper.slave_address", 1)
GRIPPER_BAUDRATE = config.get_int("gripper.baudrate", 38400)
GRIPPER_TIMEOUT = float(config.get("gripper.timeout", 1.0))


@app.on_event("startup")
async def startup_event():
    """起動時処理"""
    global gripper
    logger.info("Gripper Service起動")
    try:
        gripper = CONController(
            port=GRIPPER_PORT,
            slave_address=GRIPPER_SLAVE_ADDRESS,
            baudrate=GRIPPER_BAUDRATE,
            timeout=GRIPPER_TIMEOUT
        )
        logger.info(f"グリッパー接続成功: {GRIPPER_PORT}")
    except Exception as e:
        logger.error(f"グリッパー接続失敗: {e}")
        gripper = None


@app.on_event("shutdown")
async def shutdown_event():
    """終了時処理"""
    logger.info("Gripper Service終了")
    if gripper:
        try:
            gripper.close()
        except:
            pass


@app.get("/health", response_model=HealthCheck)
async def health_check():
    """ヘルスチェック"""
    status = "healthy" if gripper else "unhealthy"
    return HealthCheck(
        service=config.get("service.name", "gripper"),
        status=status,
        version=config.get("service.version", "1.0.0"),
        timestamp=datetime.now()
    )


@app.post("/servo/{action}")
async def servo_control(action: str):
    """サーボON/OFF"""
    if not gripper:
        raise HTTPException(status_code=503, detail="グリッパーが接続されていません")
    
    try:
        if action.lower() == "on":
            await asyncio.get_event_loop().run_in_executor(None, gripper.servo_on)
            logger.info("サーボON")
        elif action.lower() == "off":
            await asyncio.get_event_loop().run_in_executor(None, gripper.servo_off)
            logger.info("サーボOFF")
        else:
            raise HTTPException(status_code=400, detail="actionは'on'または'off'を指定してください")
        
        return {"status": "ok", "action": action}
    except Exception as e:
        logger.error(f"サーボ制御エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/home")
async def home():
    """原点復帰"""
    if not gripper:
        raise HTTPException(status_code=503, detail="グリッパーが接続されていません")
    
    try:
        await asyncio.get_event_loop().run_in_executor(None, gripper.home)
        logger.info("原点復帰実行")
        return {"status": "ok", "message": "原点復帰を実行しました"}
    except Exception as e:
        logger.error(f"原点復帰エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/move/{position}")
async def move_to_position(position: int):
    """ポジション移動"""
    if not gripper:
        raise HTTPException(status_code=503, detail="グリッパーが接続されていません")
    
    if position < 0 or position > 63:
        raise HTTPException(status_code=400, detail="ポジションは0-63の範囲で指定してください")
    
    try:
        await asyncio.get_event_loop().run_in_executor(None, gripper.move_to_pos, position)
        logger.info(f"ポジション{position}へ移動")
        return {"status": "ok", "position": position}
    except Exception as e:
        logger.error(f"移動エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/status", response_model=GripperStatus)
async def get_status():
    """ステータス取得"""
    if not gripper:
        raise HTTPException(status_code=503, detail="グリッパーが接続されていません")
    
    try:
        status = await asyncio.get_event_loop().run_in_executor(None, gripper.get_status)
        return GripperStatus(
            position_mm=status.get("position_mm", 0.0),
            servo_on=status.get("servo_on", False),
            alarm=status.get("alarm", 0),
            warn=status.get("warn", 0),
            current_position_number=status.get("current_position_number")
        )
    except Exception as e:
        logger.error(f"ステータス取得エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/positions")
async def get_all_positions():
    """全ポジション設定取得"""
    if not gripper:
        raise HTTPException(status_code=503, detail="グリッパーが接続されていません")
    
    try:
        positions = await asyncio.get_event_loop().run_in_executor(None, gripper.read_all_position_data)
        return positions
    except Exception as e:
        logger.error(f"ポジション取得エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/positions/{index}")
async def update_position(index: int, data: PositionData):
    """ポジション設定更新"""
    if not gripper:
        raise HTTPException(status_code=503, detail="グリッパーが接続されていません")
    
    if index < 0 or index > 63:
        raise HTTPException(status_code=400, detail="インデックスは0-63の範囲で指定してください")
    
    try:
        position_dict = {
            "position": data.position,
            "width": data.width,
            "speed": data.speed,
            "accel": data.accel,
            "decel": data.decel,
            "push_current": data.push_current
        }
        await asyncio.get_event_loop().run_in_executor(
            None, gripper.write_position_data, index, position_dict
        )
        logger.info(f"ポジション{index}を更新")
        return {"status": "ok", "index": index}
    except Exception as e:
        logger.error(f"ポジション更新エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host=config.get("service.host", "0.0.0.0"),
        port=config.get_int("service.port", 8002),
        log_level=config.get("logging.level", "info").lower()
    )
