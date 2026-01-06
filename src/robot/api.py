# *********************************************************************#
# File Name : api.py
# Explanation : Robot REST API Endpoints
# Project : AutomatedAssemblyRobot - SPLEBO-N Integration
# ----------------------------------------------------------------------
# Based on : 新規作成（TEACHINGにはWeb API機能なし）
# History :
#           ver0.0.1 2026.1.7 New Create - REST API endpoints
# *********************************************************************#

"""
Robot REST API エンドポイント

SPLEBO-Nロボットを制御するためのREST APIを提供します。
FastAPIのルーターとして実装され、app.pyに組み込まれます。

エンドポイント一覧:
    GET  /robot/status          - ロボット状態取得
    GET  /robot/positions       - 全軸位置取得
    POST /robot/initialize      - ロボット初期化
    POST /robot/shutdown        - ロボットシャットダウン
    POST /robot/home            - 原点復帰
    POST /robot/move            - 軸移動
    POST /robot/jog/start       - JOG移動開始
    POST /robot/jog/stop        - JOG移動停止
    POST /robot/stop            - 緊急停止
    GET  /robot/teaching/positions  - ティーチングポイント一覧
    POST /robot/teaching/teach      - 現在位置をティーチング
    POST /robot/teaching/move       - ティーチングポイントへ移動
    POST /robot/io/output           - 出力ポート設定
    GET  /robot/io/input            - 入力ポート読み取り

使用例:
    from src.robot.api import create_robot_router
    
    robot_manager = RobotManager()
    router = create_robot_router(robot_manager)
    app.include_router(router, prefix="/robot", tags=["robot"])
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum
import logging

from .robot_manager import RobotManager, RobotStatus, RobotMode
from .constants import Axis, RobotState, ErrorCode

logger = logging.getLogger(__name__)


# =============================================================================
# Pydantic Models (リクエスト/レスポンス)
# =============================================================================

class MoveRequest(BaseModel):
    """軸移動リクエスト"""
    axis: int = Field(..., ge=0, le=7, description="軸番号 (0-7)")
    position: float = Field(..., description="目標位置 [mm]")
    speed_percent: float = Field(default=100.0, ge=1, le=100, description="速度 [%]")
    wait_complete: bool = Field(default=True, description="完了を待つかどうか")


class MultiMoveRequest(BaseModel):
    """複数軸移動リクエスト"""
    moves: List[MoveRequest] = Field(..., description="移動コマンドリスト")
    parallel: bool = Field(default=True, description="並列実行するかどうか")


class JogStartRequest(BaseModel):
    """JOG移動開始リクエスト"""
    axis: int = Field(..., ge=0, le=7, description="軸番号")
    direction_positive: bool = Field(..., description="正方向かどうか")
    speed_percent: float = Field(default=10.0, ge=1, le=100, description="速度 [%]")


class TeachRequest(BaseModel):
    """ティーチングリクエスト"""
    name: str = Field(..., min_length=1, max_length=50, description="ポジション名")
    comment: str = Field(default="", max_length=200, description="コメント")


class MoveToPositionRequest(BaseModel):
    """ポジション移動リクエスト"""
    name: str = Field(..., description="ポジション名")
    speed_percent: float = Field(default=100.0, ge=1, le=100, description="速度 [%]")


class IOOutputRequest(BaseModel):
    """I/O出力リクエスト"""
    port: int = Field(..., ge=0, description="出力ポート番号")
    value: bool = Field(..., description="出力値")


class HomeRequest(BaseModel):
    """原点復帰リクエスト"""
    axis: Optional[int] = Field(default=None, ge=0, le=7, description="軸番号（省略時は全軸）")


# Response Models

class StatusResponse(BaseModel):
    """ロボット状態レスポンス"""
    state: str
    mode: str
    is_initialized: bool
    is_homing_complete: bool
    is_moving: bool
    is_error: bool
    error_code: int
    error_message: str
    current_position_name: str
    axis_positions: Dict[int, float]


class PositionsResponse(BaseModel):
    """軸位置レスポンス"""
    positions: Dict[int, float]


class TeachingPositionResponse(BaseModel):
    """ティーチングポジションレスポンス"""
    name: str
    coordinates: Dict[int, float]
    comment: str


class SuccessResponse(BaseModel):
    """成功レスポンス"""
    success: bool
    message: str = ""


class IOInputResponse(BaseModel):
    """I/O入力レスポンス"""
    port: int
    value: bool


# =============================================================================
# Router Factory
# =============================================================================

def create_robot_router(robot_manager: RobotManager) -> APIRouter:
    """
    ロボットAPIルーターを作成
    
    Args:
        robot_manager: RobotManagerインスタンス
        
    Returns:
        FastAPI APIRouter
    """
    router = APIRouter()
    
    def get_robot() -> RobotManager:
        """依存性注入用"""
        return robot_manager
    
    # =========================================================================
    # 状態取得
    # =========================================================================
    
    @router.get("/status", response_model=StatusResponse, summary="ロボット状態取得")
    async def get_status(robot: RobotManager = Depends(get_robot)):
        """
        現在のロボット状態を取得します。
        
        Returns:
            StatusResponse: ロボット状態
        """
        status = robot.get_status()
        return StatusResponse(
            state=status.state.name if hasattr(status.state, 'name') else str(status.state),
            mode=status.mode.name if hasattr(status.mode, 'name') else str(status.mode),
            is_initialized=status.is_initialized,
            is_homing_complete=status.is_homing_complete,
            is_moving=status.is_moving,
            is_error=status.is_error,
            error_code=status.error_code.value if hasattr(status.error_code, 'value') else int(status.error_code),
            error_message=status.error_message,
            current_position_name=status.current_position_name,
            axis_positions=status.axis_positions
        )
    
    @router.get("/positions", response_model=PositionsResponse, summary="全軸位置取得")
    async def get_positions(robot: RobotManager = Depends(get_robot)):
        """
        全軸の現在位置を取得します。
        
        Returns:
            PositionsResponse: 軸位置
        """
        positions = robot.get_all_positions()
        return PositionsResponse(positions=positions)
    
    # =========================================================================
    # 初期化・シャットダウン
    # =========================================================================
    
    @router.post("/initialize", response_model=SuccessResponse, summary="ロボット初期化")
    async def initialize_robot(robot: RobotManager = Depends(get_robot)):
        """
        ロボットを初期化します。
        
        起動時に一度呼び出してください。
        モーションコントローラ、CAN通信、I/Oを初期化します。
        """
        if robot.status.is_initialized:
            return SuccessResponse(success=True, message="Already initialized")
        
        success = await robot.initialize()
        if not success:
            raise HTTPException(status_code=500, detail="Initialization failed")
        
        return SuccessResponse(success=True, message="Robot initialized")
    
    @router.post("/shutdown", response_model=SuccessResponse, summary="ロボットシャットダウン")
    async def shutdown_robot(robot: RobotManager = Depends(get_robot)):
        """
        ロボットをシャットダウンします。
        
        全軸を停止し、リソースを解放します。
        """
        await robot.shutdown()
        return SuccessResponse(success=True, message="Robot shutdown complete")
    
    # =========================================================================
    # 原点復帰
    # =========================================================================
    
    @router.post("/home", response_model=SuccessResponse, summary="原点復帰")
    async def home_robot(
        request: HomeRequest = None,
        robot: RobotManager = Depends(get_robot)
    ):
        """
        原点復帰を実行します。
        
        Args:
            axis: 軸番号（省略時は全軸）
        """
        if not robot.status.is_initialized:
            raise HTTPException(status_code=400, detail="Robot not initialized")
        
        if request and request.axis is not None:
            success = await robot.home_axis(request.axis)
            message = f"Axis {request.axis} homing complete"
        else:
            success = await robot.home_all()
            message = "All axes homing complete"
        
        if not success:
            raise HTTPException(status_code=500, detail="Homing failed")
        
        return SuccessResponse(success=True, message=message)
    
    # =========================================================================
    # 移動制御
    # =========================================================================
    
    @router.post("/move", response_model=SuccessResponse, summary="軸移動")
    async def move_axis(
        request: MoveRequest,
        robot: RobotManager = Depends(get_robot)
    ):
        """
        指定した軸を目標位置へ移動します。
        
        Args:
            axis: 軸番号 (0-7)
            position: 目標位置 [mm]
            speed_percent: 速度 [%] (1-100)
            wait_complete: 完了を待つかどうか
        """
        if not robot.status.is_initialized:
            raise HTTPException(status_code=400, detail="Robot not initialized")
        
        success = await robot.move_axis(
            axis=request.axis,
            target_mm=request.position,
            speed_percent=request.speed_percent,
            wait_complete=request.wait_complete
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Move failed")
        
        return SuccessResponse(
            success=True, 
            message=f"Axis {request.axis} moved to {request.position}mm"
        )
    
    @router.post("/move/multi", response_model=SuccessResponse, summary="複数軸移動")
    async def move_multiple_axes(
        request: MultiMoveRequest,
        robot: RobotManager = Depends(get_robot)
    ):
        """
        複数軸を同時に移動します。
        """
        if not robot.status.is_initialized:
            raise HTTPException(status_code=400, detail="Robot not initialized")
        
        from .robot_manager import MoveCommand
        
        moves = [
            MoveCommand(
                axis=m.axis,
                target_mm=m.position,
                speed_percent=m.speed_percent,
                is_absolute=True,
                wait_complete=m.wait_complete
            )
            for m in request.moves
        ]
        
        success = await robot.move_axes(moves, parallel=request.parallel)
        
        if not success:
            raise HTTPException(status_code=500, detail="Multi-move failed")
        
        return SuccessResponse(success=True, message=f"Moved {len(moves)} axes")
    
    @router.post("/jog/start", response_model=SuccessResponse, summary="JOG移動開始")
    async def jog_start(
        request: JogStartRequest,
        robot: RobotManager = Depends(get_robot)
    ):
        """
        JOG移動（連続移動）を開始します。
        
        停止するまで指定方向に移動し続けます。
        """
        if not robot.status.is_initialized:
            raise HTTPException(status_code=400, detail="Robot not initialized")
        
        success = await robot.jog(
            axis=request.axis,
            direction_positive=request.direction_positive,
            speed_percent=request.speed_percent
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Jog start failed")
        
        direction = "+" if request.direction_positive else "-"
        return SuccessResponse(
            success=True, 
            message=f"Axis {request.axis} jog {direction} started"
        )
    
    @router.post("/jog/stop", response_model=SuccessResponse, summary="JOG移動停止")
    async def jog_stop(
        axis: int = Query(..., ge=0, le=7, description="軸番号"),
        robot: RobotManager = Depends(get_robot)
    ):
        """
        JOG移動を停止します。
        """
        success = await robot.stop(axis)
        return SuccessResponse(success=True, message=f"Axis {axis} stopped")
    
    @router.post("/stop", response_model=SuccessResponse, summary="緊急停止")
    async def emergency_stop(
        axis: Optional[int] = Query(default=None, ge=0, le=7, description="軸番号（省略時は全軸）"),
        robot: RobotManager = Depends(get_robot)
    ):
        """
        軸を緊急停止します。
        
        axisを省略すると全軸停止します。
        """
        success = await robot.stop(axis)
        
        if axis is not None:
            message = f"Axis {axis} stopped"
        else:
            message = "All axes stopped"
        
        return SuccessResponse(success=success, message=message)
    
    # =========================================================================
    # ティーチング
    # =========================================================================
    
    @router.get("/teaching/positions", response_model=List[TeachingPositionResponse], 
                summary="ティーチングポイント一覧")
    async def get_teaching_positions(robot: RobotManager = Depends(get_robot)):
        """
        登録されているティーチングポイントの一覧を取得します。
        """
        positions = await robot.get_positions()
        return [
            TeachingPositionResponse(
                name=pos.name,
                coordinates=pos.coordinates if hasattr(pos, 'coordinates') else {
                    0: pos.x, 1: pos.y, 2: pos.z, 3: pos.u,
                    4: pos.s1, 5: pos.s2, 6: pos.a, 7: pos.b
                },
                comment=pos.comment
            )
            for pos in positions
        ]
    
    @router.post("/teaching/teach", response_model=SuccessResponse, summary="現在位置をティーチング")
    async def teach_position(
        request: TeachRequest,
        robot: RobotManager = Depends(get_robot)
    ):
        """
        現在の軸位置を指定した名前でティーチングポイントとして保存します。
        """
        if not robot.status.is_initialized:
            raise HTTPException(status_code=400, detail="Robot not initialized")
        
        success = await robot.teach_position(request.name, request.comment)
        
        if not success:
            raise HTTPException(status_code=500, detail="Teaching failed")
        
        return SuccessResponse(success=True, message=f"Position '{request.name}' taught")
    
    @router.post("/teaching/move", response_model=SuccessResponse, 
                 summary="ティーチングポイントへ移動")
    async def move_to_teaching_position(
        request: MoveToPositionRequest,
        robot: RobotManager = Depends(get_robot)
    ):
        """
        指定したティーチングポイントへ移動します。
        """
        if not robot.status.is_initialized:
            raise HTTPException(status_code=400, detail="Robot not initialized")
        
        success = await robot.move_to_position(
            request.name, 
            speed_percent=request.speed_percent
        )
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Position '{request.name}' not found")
        
        return SuccessResponse(success=True, message=f"Moved to '{request.name}'")
    
    @router.delete("/teaching/positions/{name}", response_model=SuccessResponse,
                   summary="ティーチングポイント削除")
    async def delete_teaching_position(
        name: str,
        robot: RobotManager = Depends(get_robot)
    ):
        """
        指定したティーチングポイントを削除します。
        """
        success = await robot.delete_position(name)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Position '{name}' not found")
        
        return SuccessResponse(success=True, message=f"Position '{name}' deleted")
    
    # =========================================================================
    # I/O制御
    # =========================================================================
    
    @router.get("/io/input/{port}", response_model=IOInputResponse, summary="入力ポート読み取り")
    async def get_io_input(
        port: int,
        robot: RobotManager = Depends(get_robot)
    ):
        """
        指定した入力ポートの状態を読み取ります。
        """
        value = await robot.get_input(port)
        
        if value is None:
            raise HTTPException(status_code=500, detail="Failed to read input")
        
        return IOInputResponse(port=port, value=value)
    
    @router.post("/io/output", response_model=SuccessResponse, summary="出力ポート設定")
    async def set_io_output(
        request: IOOutputRequest,
        robot: RobotManager = Depends(get_robot)
    ):
        """
        指定した出力ポートの値を設定します。
        """
        success = await robot.set_output(request.port, request.value)
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to set output")
        
        state = "ON" if request.value else "OFF"
        return SuccessResponse(success=True, message=f"Output {request.port} set to {state}")
    
    @router.post("/io/buzzer", response_model=SuccessResponse, summary="ブザー鳴動")
    async def buzzer(
        duration: float = Query(default=0.5, ge=0.1, le=5.0, description="鳴動時間 [秒]"),
        robot: RobotManager = Depends(get_robot)
    ):
        """
        ブザーを指定時間鳴らします。
        """
        await robot.buzzer_on(duration)
        return SuccessResponse(success=True, message=f"Buzzer beeped for {duration}s")
    
    # =========================================================================
    # モード制御
    # =========================================================================
    
    @router.post("/mode", response_model=SuccessResponse, summary="動作モード設定")
    async def set_mode(
        mode: str = Query(..., description="モード (MANUAL/AUTO/TEACHING/MAINTENANCE)"),
        robot: RobotManager = Depends(get_robot)
    ):
        """
        動作モードを設定します。
        
        - MANUAL: 手動モード
        - AUTO: 自動モード（原点復帰完了後のみ）
        - TEACHING: ティーチングモード
        - MAINTENANCE: メンテナンスモード
        """
        try:
            robot_mode = RobotMode[mode.upper()]
        except KeyError:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid mode: {mode}. Valid modes: MANUAL, AUTO, TEACHING, MAINTENANCE"
            )
        
        success = await robot.set_mode(robot_mode)
        
        if not success:
            raise HTTPException(status_code=400, detail=f"Cannot switch to {mode} mode")
        
        return SuccessResponse(success=True, message=f"Mode set to {mode}")
    
    # =========================================================================
    # エラー処理
    # =========================================================================
    
    @router.post("/error/clear", response_model=SuccessResponse, summary="エラークリア")
    async def clear_error(robot: RobotManager = Depends(get_robot)):
        """
        エラー状態をクリアします。
        """
        success = await robot.clear_error()
        
        if not success:
            raise HTTPException(status_code=400, detail="Cannot clear error")
        
        return SuccessResponse(success=True, message="Error cleared")
    
    @router.post("/reset", response_model=SuccessResponse, summary="ロボットリセット")
    async def reset_robot(robot: RobotManager = Depends(get_robot)):
        """
        ロボットをリセットします。
        
        全軸停止、エラークリア、ホーミングフラグリセットを行います。
        """
        success = await robot.reset()
        return SuccessResponse(success=True, message="Robot reset complete")
    
    return router
