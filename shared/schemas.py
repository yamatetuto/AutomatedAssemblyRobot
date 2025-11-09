"""共通データスキーマ（Pydantic）"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


# ===== カメラ関連 =====
class CameraControl(BaseModel):
    """カメラコントロール"""
    name: str
    type: str  # "int", "bool", "menu"
    min: Optional[int] = None
    max: Optional[int] = None
    step: Optional[int] = None
    default: Optional[int] = None
    value: Optional[int] = None
    menu: Optional[Dict[str, int]] = None


class SnapshotInfo(BaseModel):
    """スナップショット情報"""
    filename: str
    timestamp: str
    url: str


class CameraResolution(BaseModel):
    """カメラ解像度"""
    width: int = Field(ge=320, le=4096)
    height: int = Field(ge=240, le=3072)
    fps: int = Field(ge=1, le=60, default=30)


# ===== グリッパー関連 =====
class GripperStatus(BaseModel):
    """グリッパーステータス"""
    position_mm: float
    servo_on: bool
    alarm: int
    warn: int
    current_position_number: Optional[int] = None


class PositionData(BaseModel):
    """グリッパーポジションデータ"""
    position: float = Field(description="位置 [mm]")
    width: float = Field(description="把持幅 [mm]")
    speed: int = Field(ge=1, le=100, description="速度 [%]")
    accel: int = Field(ge=1, le=100, description="加速度 [%]")
    decel: int = Field(ge=1, le=100, description="減速度 [%]")
    push_current: int = Field(ge=0, le=100, description="押当電流 [%]")


class PositionTableEntry(BaseModel):
    """ポジションテーブルのエントリ"""
    index: int = Field(ge=0, le=63)
    data: PositionData


# ===== 画像処理関連 =====
class DetectionResult(BaseModel):
    """物体検出結果"""
    x: float
    y: float
    width: float
    height: float
    confidence: float
    label: Optional[str] = None


class CalibrationPoint(BaseModel):
    """キャリブレーションポイント"""
    camera_x: float
    camera_y: float
    robot_x: float
    robot_y: float
    robot_z: float


class CalibrationData(BaseModel):
    """キャリブレーションデータ"""
    points: List[CalibrationPoint]
    transform_matrix: Optional[List[List[float]]] = None
    calibrated_at: Optional[datetime] = None


# ===== 共通 =====
class HealthCheck(BaseModel):
    """ヘルスチェックレスポンス"""
    service: str
    status: str  # "healthy", "degraded", "unhealthy"
    version: str
    timestamp: datetime


class ErrorResponse(BaseModel):
    """エラーレスポンス"""
    error: str
    detail: Optional[str] = None
    timestamp: datetime
