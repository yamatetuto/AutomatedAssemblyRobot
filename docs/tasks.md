# 実装計画書

**作成日**: 2025-11-05  
**目的**: 自動組立ロボットシステムの実装手順を明確化

---

## 概要

調査結果（`docs/reports/`）と要件定義（`docs/requirements.md`）に基づき、実装を段階的に進める。

---

## フェーズ1: 基盤整備 🔧

### タスク1-1: プロジェクト構造の再編成
**ファイル**: プロジェクトルート

**実施内容**:
```
AutomatedAssemblyRobot/
├── camera_controller/          # 既存（整理のみ）
├── gripper_controller/             # 既存（名称変更検討: gripper_controller）
├── printer_controller/         # 新規作成
│   ├── __init__.py
│   ├── OctoPrintController.py
│   └── README.md
├── dispenser_controller/       # 新規作成
│   ├── __init__.py
│   ├── DispenserController.py
│   └── README.md
├── robot_controller/           # 新規作成（企業ライブラリ確認後）
│   ├── __init__.py
│   ├── RobotController.py
│   ├── CoordinateTransformer.py
│   └── README.md
├── core/                       # 新規作成（統合制御）
│   ├── __init__.py
│   ├── AssemblyController.py
│   ├── Sequencer.py
│   └── schemas.py              # データクラス定義
├── web_app/                    # 新規作成（Webアプリ）
│   ├── __init__.py
│   ├── main.py                 # FastAPI
│   ├── routers/
│   ├── static/
│   └── templates/
├── config/                     # 新規作成
│   ├── system_config.yaml
│   └── .env.example
├── sequences/                  # 新規作成
│   └── example_sequence.yaml
├── logs/                       # 新規作成（自動生成）
├── tests/                      # 新規作成
│   ├── test_camera.py
│   ├── test_gripper.py
│   └── test_printer.py
├── docs/                       # 既存（拡張済み）
│   ├── reports/
│   ├── schema.md
│   └── requirements.md
├── requirements.txt            # 新規作成
├── setup.py                    # 新規作成
├── .gitignore                  # 更新
├── README.md                   # 更新
└── DesignDocument.md           # 既存
```

**不要ファイルの削除**:
```bash
rm camera_controller/webrtc/streamer_backup*.py
rm camera_controller/webrtc_index_backup*.html
```

---

### タスク1-2: requirements.txt の作成
**ファイル**: `requirements.txt`

**内容**:
```txt
# カメラ・映像処理
opencv-python==4.8.1.78
aiortc==1.6.0
aiohttp==3.9.1
numpy==1.24.3

# グリッパー制御
minimalmodbus==2.1.1
pyserial==3.5

# プリンター制御
requests==2.31.0

# ディスペンサー制御
RPi.GPIO==0.7.1
# または gpiozero==2.0.1

# Webアプリケーション
fastapi==0.104.1
uvicorn[standard]==0.24.0
websockets==12.0
pydantic==2.5.0
python-multipart==0.0.6

# 設定管理
python-dotenv==1.0.0
PyYAML==6.0.1

# テスト
pytest==7.4.3
pytest-asyncio==0.21.1
pytest-cov==4.1.0

# 開発ツール
black==23.11.0
flake8==6.1.0
mypy==1.7.0
```

---

### タスク1-3: .gitignore の更新
**ファイル**: `.gitignore`

**内容**:
```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# 環境変数
.env
.env.local
config/*.key

# ログ
logs/*.log
*.log

# スナップショット
camera_controller/snapshots/*.jpg
snapshots/*.jpg

# バックアップファイル
*_backup*
*.bak
*~

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# テスト
.pytest_cache/
.coverage
htmlcov/

# 一時ファイル
*.tmp
temp/
```

---

### タスク1-4: setup.py の作成
**ファイル**: `setup.py`

**内容**:
```python
from setuptools import setup, find_packages

setup(
    name="automated-assembly-robot",
    version="0.1.0",
    description="自動組立ロボット制御システム",
    author="Your Name",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        "opencv-python>=4.8.0",
        "aiortc>=1.6.0",
        "aiohttp>=3.9.0",
        "minimalmodbus>=2.1.0",
        "pyserial>=3.5",
        "requests>=2.31.0",
        "RPi.GPIO>=0.7.1",
        "fastapi>=0.104.0",
        "uvicorn[standard]>=0.24.0",
        "websockets>=12.0",
        "pydantic>=2.5.0",
        "python-dotenv>=1.0.0",
        "PyYAML>=6.0.0",
        "numpy>=1.24.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-asyncio>=0.21.0",
            "pytest-cov>=4.1.0",
            "black>=23.11.0",
            "flake8>=6.1.0",
            "mypy>=1.7.0",
        ]
    },
)
```

---

### タスク1-5: README.md の更新
**ファイル**: `README.md`

**内容**: 包括的な説明を追加
- プロジェクト概要
- インストール手順
- 使用方法
- ディレクトリ構造
- 開発ガイド

---

## フェーズ2: コア機能実装 🚀

### タスク2-1: 3Dプリンター制御モジュール
**ファイル**: `printer_controller/OctoPrintController.py`

**実装クラス**:
```python
class OctoPrintController:
    def __init__(host, api_key, port)
    def connect() -> bool
    def get_state() -> PrinterState
    def set_tool_temperature(temp: float)
    def set_bed_temperature(temp: float)
    def start_print(filename: str)
    def pause_print()
    def cancel_print()
    def send_gcode(commands: list[str])
    def upload_file(filepath: str)
    def wait_for_completion() -> bool
```

**テスト**: `tests/test_printer.py`

---

### タスク2-2: ディスペンサー制御モジュール
**ファイル**: `dispenser_controller/DispenserController.py`

**実装クラス**:
```python
class DispenserController:
    def __init__(pin: int)
    def dispense(duration: float)
    def dispense_pulse(duration: float, interval: float, count: int)
    def get_state() -> DispenserState
    def close()
```

**テスト**: `tests/test_dispenser.py`

---

### タスク2-3: 画像処理アルゴリズム
**ファイル**: `camera_controller/processor/processors.py`

**実装関数**:
```python
def detect_objects(frame, lower_color, upper_color) -> list[DetectedObject]
def template_matching(frame, template, threshold) -> list[tuple]
def detect_edges(frame) -> np.ndarray
def find_contours(frame) -> list
def calculate_center(contour) -> tuple[int, int]
def calculate_angle(contour) -> float
```

**テスト**: `tests/test_image_processing.py`

---

### タスク2-4: ロボットアーム統合（保留：企業ライブラリ確認後）
**ファイル**: `robot_controller/RobotController.py`

**実装クラス** (仮):
```python
class RobotController:
    def __init__(port: str)
    def connect() -> bool
    def home() -> bool
    def move_to(position: Position3D)
    def move_relative(dx, dy, dz)
    def get_position() -> Position3D
    def set_speed(speed: float)
    def get_state() -> RobotState
```

**実装クラス**: `CoordinateTransformer`
```python
class CoordinateTransformer:
    def __init__(calibration_file: str)
    def camera_to_robot(x_cam, y_cam) -> tuple[float, float]
    def robot_to_camera(x_rob, y_rob) -> tuple[float, float]
    def calibrate(points: list[CoordinateMapping])
    def save_calibration(filepath: str)
    def load_calibration(filepath: str)
```

**テスト**: `tests/test_robot.py`

---

## フェーズ3: 統合制御システム 🎯

### タスク3-1: データスキーマ実装
**ファイル**: `core/schemas.py`

**内容**: `docs/schema.md` で定義したデータクラスをすべて実装
- Position3D
- CameraState, RobotState, GripperState, PrinterState, DispenserState
- DetectedObject
- Task, AssemblySequence
- SystemEvent, TaskLog
- 各種Config

---

### タスク3-2: 統合コントローラー
**ファイル**: `core/AssemblyController.py`

**実装クラス**:
```python
class AssemblyController:
    def __init__(config: SystemConfig)
    def initialize_devices() -> bool
    def shutdown_devices()
    def get_all_states() -> dict
    async def execute_sequence(sequence: AssemblySequence) -> bool
    def emergency_stop()
```

**依存**:
- CameraController
- RobotController
- GripperController (CONController)
- PrinterController
- DispenserController

---

### タスク3-3: シーケンスエンジン
**ファイル**: `core/Sequencer.py`

**実装クラス**:
```python
class Sequencer:
    def __init__(controller: AssemblyController)
    async def execute_task(task: Task) -> bool
    async def execute_sequence(sequence: AssemblySequence) -> bool
    def load_sequence_from_yaml(filepath: str) -> AssemblySequence
    def save_sequence_to_yaml(sequence, filepath: str)
```

**処理フロー**:
1. YAMLファイルからシーケンス読み込み
2. 各タスクを順次実行
3. エラー発生時はリトライ
4. すべてのログを記録

---

### タスク3-4: 設定管理
**ファイル**: 
- `config/system_config.yaml` (サンプル)
- `core/config_loader.py` (ロード処理)

**実装関数**:
```python
def load_config(filepath: str) -> SystemConfig
def load_env_variables() -> dict
def merge_configs(yaml_config, env_config) -> SystemConfig
```

---

### タスク3-5: ログ・エラーハンドリング
**ファイル**: `core/logger.py`

**実装**:
```python
import logging

def setup_logger(name: str, log_file: str, level=logging.INFO)
def log_event(event: SystemEvent)
def log_task(task_log: TaskLog)
```

**カスタム例外**:
```python
class AssemblyError(Exception): pass
class DeviceConnectionError(AssemblyError): pass
class MotionError(AssemblyError): pass
class VisionError(AssemblyError): pass
```

---

## フェーズ4: Webアプリケーション 🌐

### タスク4-1: FastAPI バックエンド
**ファイル**: `web_app/main.py`

**エンドポイント設計**:
```
GET  /api/status          - 全デバイス状態取得
GET  /api/camera/stream   - カメラストリーム (WebRTC)
POST /api/camera/snapshot - スナップショット撮影

GET  /api/robot/position  - ロボット現在位置
POST /api/robot/move      - ロボット移動指令
POST /api/robot/home      - 原点復帰

POST /api/gripper/grip    - 把持
POST /api/gripper/release - 開放
GET  /api/gripper/state   - グリッパー状態

POST /api/printer/start   - プリント開始
POST /api/printer/stop    - プリント停止
GET  /api/printer/state   - プリンター状態

POST /api/dispenser/dispense - 吐出

GET  /api/sequences       - シーケンス一覧
POST /api/sequences       - シーケンス作成
POST /api/sequences/{id}/start - シーケンス実行

WS   /ws/status           - リアルタイム状態更新
```

---

### タスク4-2: WebSocket通信
**ファイル**: `web_app/websocket.py`

**機能**:
- 接続管理
- 状態ブロードキャスト（1秒ごと）
- イベント通知

---

### タスク4-3: フロントエンドUI
**ディレクトリ**: `web_app/static/`, `web_app/templates/`

**ページ構成**:
- `index.html` - ダッシュボード
- `camera.html` - カメラビュー
- `manual.html` - 手動操作パネル
- `sequences.html` - シーケンス管理
- `settings.html` - 設定画面

**技術**:
- HTML/CSS/JavaScript (Vanilla または Vue.js軽量版)
- WebSocketでリアルタイム更新
- Bootstrap または TailwindCSS でスタイリング

---

## フェーズ5: テスト・デバッグ ✅

### タスク5-1: ユニットテスト
**ファイル**: `tests/test_*.py`

**テスト対象**:
- 各デバイスコントローラー
- 画像処理関数
- 座標変換
- シーケンスエンジン

**実行**:
```bash
pytest tests/ -v --cov=.
```

---

### タスク5-2: 統合テスト
**ファイル**: `tests/test_integration.py`

**テストシナリオ**:
1. デバイス初期化
2. 簡単なシーケンス実行
3. エラー回復
4. 並行動作

---

### タスク5-3: 実機デバッグ
**手順**:
1. 各デバイスを個別に動作確認
2. 簡単なシーケンスで動作確認
3. エラーケースの確認
4. 長時間運転の安定性確認

---

## 実装順序（推奨）

### Week 1: 基盤整備
1. プロジェクト構造整理
2. requirements.txt, setup.py, .gitignore 作成
3. README.md 更新
4. バックアップファイル削除
5. **Git commit**: `chore: プロジェクト構造整理と基盤ファイル作成`

### Week 2: プリンター・ディスペンサー
1. printer_controller/ 実装
2. dispenser_controller/ 実装
3. テスト作成・実行
4. **Git commit**: `feat: プリンターとディスペンサー制御モジュール実装`

### Week 3: 画像処理・座標変換
1. camera_controller/processor/processors.py 実装
2. robot_controller/CoordinateTransformer.py 実装
3. キャリブレーション手順ドキュメント作成
4. **Git commit**: `feat: 画像処理と座標変換機能実装`

### Week 4: ロボット統合（企業ライブラリ確認後）
1. robot_controller/ 実装
2. 企業ライブラリとの統合
3. 動作確認
4. **Git commit**: `feat: ロボットアーム制御統合`

### Week 5: 統合制御システム
1. core/schemas.py 実装
2. core/AssemblyController.py 実装
3. core/Sequencer.py 実装
4. config/ サンプル作成
5. **Git commit**: `feat: 統合制御システム実装`

### Week 6: Webアプリ（バックエンド）
1. web_app/main.py 実装
2. REST API エンドポイント実装
3. WebSocket実装
4. **Git commit**: `feat: Webアプリバックエンド実装`

### Week 7: Webアプリ（フロントエンド）
1. ダッシュボードUI
2. カメラビュー統合
3. 手動操作パネル
4. シーケンス管理UI
5. **Git commit**: `feat: Webアプリフロントエンド実装`

### Week 8: テスト・デバッグ
1. ユニットテスト追加
2. 統合テスト
3. 実機デバッグ
4. ドキュメント最終化
5. **Git commit**: `test: テスト追加とデバッグ完了`

---

## ユーザー確認待ち事項 ⚠️

実装を進める前に、以下の情報をユーザーから確認する必要があります:

1. **ロボット制御ライブラリ** （最優先）
   - ライブラリファイルの場所
   - インポート方法
   - API仕様またはサンプルコード

2. **ディスペンサー仕様**
   - 型番
   - 制御電圧 (3.3V / 5V)
   - 使用するGPIOピン番号

3. **OctoPrint情報**
   - IPアドレス
   - APIキー
   - ポート番号

4. **優先順位の確認**
   - 最優先で実装すべき機能
   - スキップ可能な機能

---

## 次のステップ

1. ✅ ユーザーへ確認事項を質問
2. ✅ 回答を受けて `docs/tasks.md` を更新
3. ✅ Week 1（基盤整備）の実装を開始

---

**作成者**: GitHub Copilot  
**次回更新**: ユーザー確認後
