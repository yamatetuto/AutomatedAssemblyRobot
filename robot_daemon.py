"""Robot-only daemon for root execution (TEACHING control)."""
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

from src.config.settings import (
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
from src.robot.teaching_manager import TeachingRobotManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

robot_manager: Optional[TeachingRobotManager] = None
_services_started = False


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


async def _startup_services() -> None:
    global robot_manager, _services_started
    if _services_started:
        return
    _services_started = True

    logger.info("🚀 ロボットサービスを起動中...")

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

    logger.info("🎉 ロボットサービス起動完了")


async def _shutdown_services() -> None:
    global robot_manager, _services_started
    if not _services_started:
        return
    _services_started = False

    logger.info("🛑 ロボットサービスを終了中...")

    if robot_manager:
        await asyncio.to_thread(robot_manager.close)
        robot_manager = None

    logger.info("👋 ロボットサービスを停止しました")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await _startup_services()
    yield
    await _shutdown_services()


app = FastAPI(title="Robot Service", lifespan=lifespan)


@app.on_event("startup")
async def on_startup() -> None:
    await _startup_services()


@app.on_event("shutdown")
async def on_shutdown() -> None:
    await _shutdown_services()


@app.get("/health")
async def health_check():
    return {"status": "healthy", "robot": robot_manager is not None}


@app.get("/api/robot/config")
async def robot_config():
    if not robot_manager:
        raise HTTPException(status_code=503, detail="ロボットサービスが起動していません")
    return robot_manager.get_config()


@app.get("/api/robot/diagnostics")
async def robot_diagnostics():
    if not robot_manager:
        raise HTTPException(status_code=503, detail="ロボットサービスが起動していません")
    return {
        "emg": robot_manager.get_emg_status(),
        "positions": robot_manager.get_positions(),
    }


@app.post("/api/robot/home")
async def robot_home():
    if not robot_manager:
        raise HTTPException(status_code=503, detail="ロボットサービスが起動していません")
    try:
        await asyncio.to_thread(robot_manager.home)
        return {"status": "ok", "message": "原点復帰を開始しました"}
    except Exception as e:
        logger.error(f"ロボット原点復帰エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/robot/jog/start")
async def robot_jog_start(request: RobotJogRequest):
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
async def robot_jog_stop(request: RobotJogStopRequest):
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
async def robot_stop_all():
    if not robot_manager:
        raise HTTPException(status_code=503, detail="ロボットサービスが起動していません")
    try:
        await asyncio.to_thread(robot_manager.stop_all)
        return {"status": "ok", "message": "停止コマンドを送信しました"}
    except Exception as e:
        logger.error(f"ロボット停止エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/robot/point/register")
async def robot_point_register(request: RobotPointRegisterRequest):
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


@app.post("/api/robot/io/output")
async def robot_io_output(request: RobotIOOutputRequest):
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
async def robot_io_input(request: RobotIOInputRequest):
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


@app.post("/api/robot/point/move")
async def robot_point_move(request: RobotPointMoveRequest):
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


@app.get("/api/robot/position_table")
async def robot_position_table_all():
    if not robot_manager:
        raise HTTPException(status_code=503, detail="ロボットサービスが起動していません")
    try:
        return {"status": "ok", "data": robot_manager.get_position_table_all()}
    except Exception as e:
        logger.error(f"ポジションテーブル取得エラー: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/robot/position_table/{point_no}")
async def robot_position_table_point(point_no: int):
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
async def robot_position_table_update(point_no: int, request: RobotPositionUpdateRequest):
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8081,
        log_level="info",
    )
