# データ構造・スキーマ定義

**作成日**: 2025-11-05  
**目的**: システム全体で使用するデータ構造を統一的に定義

---

## 1. デバイス状態

### 1.1 カメラ状態
```python
from dataclasses import dataclass
from typing import Optional
import numpy as np

@dataclass
class CameraState:
    """カメラ状態"""
    device_id: int
    is_active: bool
    width: int
    height: int
    fps: float
    brightness: float
    contrast: float
    saturation: float
    hue: float
    codec: str

@dataclass
class ImageFrame:
    """画像フレーム"""
    timestamp: float
    frame: np.ndarray
    width: int
    height: int
    source: str  # カメラID
```

### 1.2 ロボット状態
```python
@dataclass
class Position3D:
    """3次元座標"""
    x: float
    y: float
    z: float
    unit: str = "mm"  # mm または inch

@dataclass
class RobotState:
    """ロボット状態"""
    is_connected: bool
    is_homed: bool
    is_moving: bool
    current_position: Position3D
    target_position: Optional[Position3D]
    speed: float  # mm/s
    acceleration: float  # mm/s^2
```

### 1.3 グリッパー状態
```python
@dataclass
class GripperState:
    """グリッパー状態"""
    is_servo_on: bool
    is_homed: bool
    is_moving: bool
    position: int  # ポジション番号
    current_value: int  # 電流値
    load_cell: int  # 荷重データ
    alarm_code: int
    is_gripping: bool
```

### 1.4 プリンター状態
```python
@dataclass
class PrinterState:
    """3Dプリンター状態"""
    is_connected: bool
    is_operational: bool
    is_printing: bool
    is_paused: bool
    tool_temp: float  # ノズル温度
    tool_target: float
    bed_temp: float  # ベッド温度
    bed_target: float
    progress: float  # 0-100%
    current_file: Optional[str]
    print_time: float  # 秒
    print_time_left: Optional[float]
```

### 1.5 ディスペンサー状態
```python
@dataclass
class DispenserState:
    """ディスペンサー状態"""
    is_ready: bool
    gpio_pin: int
    is_dispensing: bool
    total_dispense_count: int
    last_dispense_duration: float
```

---

## 2. 検出結果

### 2.1 物体検出
```python
@dataclass
class DetectedObject:
    """検出された物体"""
    object_id: int
    label: str  # "part_a", "part_b" など
    confidence: float  # 0-1
    center: tuple[int, int]  # (x, y) ピクセル座標
    bounding_box: tuple[int, int, int, int]  # (x, y, width, height)
    area: float  # ピクセル面積
    angle: float  # 回転角度（度）
    timestamp: float
```

### 2.2 座標変換
```python
@dataclass
class CoordinateMapping:
    """座標マッピング情報"""
    camera_point: tuple[float, float]  # カメラ座標 (px, py)
    robot_point: Position3D  # ロボット座標
    timestamp: float
    calibration_id: str
```

---

## 3. 組立シーケンス

### 3.1 タスク定義
```python
from enum import Enum
from typing import Any, Dict

class TaskType(Enum):
    """タスクタイプ"""
    PRINT = "print"              # 3Dプリント
    MOVE = "move"                # ロボット移動
    GRIP = "grip"                # 把持
    RELEASE = "release"          # 開放
    DISPENSE = "dispense"        # 接着剤塗布
    CAPTURE = "capture"          # 画像撮影
    DETECT = "detect"            # 物体検出
    WAIT = "wait"                # 待機
    HOME = "home"                # 原点復帰

@dataclass
class Task:
    """実行タスク"""
    task_id: str
    task_type: TaskType
    parameters: Dict[str, Any]
    timeout: float  # 秒
    retry_count: int = 0
    max_retries: int = 3
```

### 3.2 シーケンス定義
```python
@dataclass
class AssemblySequence:
    """組立シーケンス"""
    sequence_id: str
    name: str
    description: str
    tasks: list[Task]
    estimated_duration: float  # 秒
    created_at: float
    created_by: str

# 使用例
sequence = AssemblySequence(
    sequence_id="seq_001",
    name="部品A組立",
    description="部品Aをピックアップして接着",
    tasks=[
        Task(
            task_id="task_001",
            task_type=TaskType.CAPTURE,
            parameters={},
            timeout=5.0
        ),
        Task(
            task_id="task_002",
            task_type=TaskType.DETECT,
            parameters={"label": "part_a"},
            timeout=3.0
        ),
        Task(
            task_id="task_003",
            task_type=TaskType.MOVE,
            parameters={"target": Position3D(100, 50, 10)},
            timeout=10.0
        ),
        Task(
            task_id="task_004",
            task_type=TaskType.GRIP,
            parameters={"position": 1},
            timeout=5.0
        ),
    ],
    estimated_duration=30.0,
    created_at=time.time(),
    created_by="user"
)
```

---

## 4. イベント・ログ

### 4.1 システムイベント
```python
from enum import Enum

class EventLevel(Enum):
    """イベントレベル"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

@dataclass
class SystemEvent:
    """システムイベント"""
    event_id: str
    timestamp: float
    level: EventLevel
    source: str  # デバイス名またはモジュール名
    message: str
    details: Optional[Dict[str, Any]] = None
```

### 4.2 タスク実行ログ
```python
from enum import Enum

class TaskStatus(Enum):
    """タスク実行状態"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class TaskLog:
    """タスク実行ログ"""
    task_id: str
    sequence_id: str
    status: TaskStatus
    start_time: float
    end_time: Optional[float]
    duration: Optional[float]
    error_message: Optional[str] = None
    retry_count: int = 0
```

---

## 5. 設定データ

### 5.1 デバイス設定
```python
@dataclass
class CameraConfig:
    """カメラ設定"""
    device_id: int
    width: int = 640
    height: int = 480
    fps: int = 30
    rotation: int = 0
    flip: bool = False

@dataclass
class RobotConfig:
    """ロボット設定"""
    port: str
    baudrate: int
    max_speed: float  # mm/s
    max_acceleration: float  # mm/s^2
    home_position: Position3D
    work_area_min: Position3D
    work_area_max: Position3D

@dataclass
class GripperConfig:
    """グリッパー設定"""
    port: str
    slave_address: int
    baudrate: int
    grip_position: int
    release_position: int
    grip_force: int  # 把持力（電流値）

@dataclass
class PrinterConfig:
    """プリンター設定"""
    host: str
    port: int
    api_key: str
    default_tool_temp: float
    default_bed_temp: float

@dataclass
class DispenserConfig:
    """ディスペンサー設定"""
    gpio_pin: int
    default_duration: float  # 秒
    pulse_mode: bool
    pulse_duration: float
    pulse_interval: float
```

### 5.2 システム設定
```python
@dataclass
class SystemConfig:
    """システム全体設定"""
    camera: CameraConfig
    robot: RobotConfig
    gripper: GripperConfig
    printer: PrinterConfig
    dispenser: DispenserConfig
    log_level: EventLevel
    log_directory: str
    snapshot_directory: str
    sequence_directory: str
```

---

## 6. API レスポンス

### 6.1 標準レスポンス
```python
from typing import Generic, TypeVar, Optional

T = TypeVar('T')

@dataclass
class APIResponse(Generic[T]):
    """API標準レスポンス"""
    success: bool
    data: Optional[T]
    message: str
    timestamp: float
    error_code: Optional[str] = None

# 使用例
response = APIResponse(
    success=True,
    data={"position": {"x": 100, "y": 50, "z": 10}},
    message="移動完了",
    timestamp=time.time()
)
```

### 6.2 WebSocketメッセージ
```python
class MessageType(Enum):
    """WebSocketメッセージタイプ"""
    STATE_UPDATE = "state_update"
    COMMAND = "command"
    EVENT = "event"
    LOG = "log"

@dataclass
class WebSocketMessage:
    """WebSocketメッセージ"""
    type: MessageType
    payload: Dict[str, Any]
    timestamp: float
```

---

## 7. データベーススキーマ（将来拡張用）

### 7.1 組立履歴
```sql
CREATE TABLE assembly_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sequence_id TEXT NOT NULL,
    started_at REAL NOT NULL,
    completed_at REAL,
    status TEXT NOT NULL,
    total_tasks INTEGER NOT NULL,
    completed_tasks INTEGER NOT NULL,
    failed_tasks INTEGER NOT NULL,
    error_message TEXT
);
```

### 7.2 タスクログ
```sql
CREATE TABLE task_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    assembly_id INTEGER NOT NULL,
    task_id TEXT NOT NULL,
    task_type TEXT NOT NULL,
    started_at REAL NOT NULL,
    completed_at REAL,
    status TEXT NOT NULL,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    FOREIGN KEY (assembly_id) REFERENCES assembly_history(id)
);
```

### 7.3 キャリブレーションデータ
```sql
CREATE TABLE calibration_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    calibration_id TEXT NOT NULL UNIQUE,
    camera_x REAL NOT NULL,
    camera_y REAL NOT NULL,
    robot_x REAL NOT NULL,
    robot_y REAL NOT NULL,
    robot_z REAL NOT NULL,
    created_at REAL NOT NULL
);
```

---

## 8. 設定ファイルフォーマット

### 8.1 YAML設定ファイル例
```yaml
# config/system_config.yaml
camera:
  device_id: 0
  width: 640
  height: 480
  fps: 30
  rotation: 0
  flip: false

robot:
  port: "/dev/ttyUSB0"
  baudrate: 115200
  max_speed: 100.0  # mm/s
  max_acceleration: 500.0  # mm/s^2
  home_position:
    x: 0.0
    y: 0.0
    z: 0.0
  work_area_min:
    x: 0.0
    y: 0.0
    z: 0.0
  work_area_max:
    x: 800.0
    y: 250.0
    z: 100.0

gripper:
  port: "/dev/ttyUSB1"
  slave_address: 1
  baudrate: 9600
  grip_position: 1
  release_position: 0
  grip_force: 50

printer:
  host: "192.168.1.100"
  port: 80
  api_key: "${OCTOPRINT_API_KEY}"  # 環境変数から読み込み
  default_tool_temp: 200.0
  default_bed_temp: 60.0

dispenser:
  gpio_pin: 17
  default_duration: 0.5
  pulse_mode: false
  pulse_duration: 0.1
  pulse_interval: 0.1

system:
  log_level: "INFO"
  log_directory: "./logs"
  snapshot_directory: "./snapshots"
  sequence_directory: "./sequences"
```

### 8.2 シーケンスファイル例
```yaml
# sequences/assembly_part_a.yaml
sequence_id: "seq_part_a_001"
name: "部品A組立シーケンス"
description: "部品Aをピックアップして指定位置に配置"
estimated_duration: 45.0

tasks:
  - task_id: "task_001"
    type: "capture"
    parameters: {}
    timeout: 5.0
  
  - task_id: "task_002"
    type: "detect"
    parameters:
      label: "part_a"
      min_confidence: 0.8
    timeout: 3.0
  
  - task_id: "task_003"
    type: "move"
    parameters:
      target:
        x: 100.0
        y: 50.0
        z: 10.0
    timeout: 10.0
  
  - task_id: "task_004"
    type: "grip"
    parameters:
      position: 1
    timeout: 5.0
  
  - task_id: "task_005"
    type: "move"
    parameters:
      target:
        x: 200.0
        y: 100.0
        z: 20.0
    timeout: 10.0
  
  - task_id: "task_006"
    type: "dispense"
    parameters:
      duration: 0.5
    timeout: 3.0
  
  - task_id: "task_007"
    type: "release"
    parameters:
      position: 0
    timeout: 5.0
```

---

## 9. ファイル命名規則

```
snapshots/snapshot_YYYYMMDD_HHMMSS.jpg
logs/system_YYYYMMDD.log
logs/task_YYYYMMDD.log
sequences/seq_<name>_<version>.yaml
config/system_config.yaml
config/calibration_<camera_id>.yaml
```

---

## まとめ

このスキーマ定義により:
- ✅ 型安全なデータ構造（`dataclass`使用）
- ✅ 統一されたAPI設計
- ✅ 拡張性のある設定管理
- ✅ ログとデバッグの容易さ

すべてのモジュールでこのスキーマを参照し、一貫性を保つこと。
