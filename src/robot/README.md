# SPLEBO-N ロボット制御モジュール

AutomatedAssemblyRobotに統合されたSPLEBO-Nテーブルロボット制御モジュールです。

## 概要

このモジュールは、TEACHINGフォルダにあるオリジナルのSPLEBO-N制御コードを
FastAPI/asyncioベースのアプリケーションに統合するために書き換えたものです。

### 主な特徴

- **非同期対応 (asyncio)**: FastAPIとシームレスに統合
- **シミュレーションモード**: ハードウェアなしでテスト可能
- **型安全**: dataclass, Enum, 型ヒントを活用
- **モジュラー設計**: 各機能が独立したクラスに分離

---

## ファイル構成

```
src/robot/
├── __init__.py           # モジュールエクスポート
├── constants.py          # 定数・Enum定義
├── can_controller.py     # CAN通信制御
├── io_expander.py        # I/O制御
├── position_manager.py   # ポジション管理
├── motion_controller.py  # モーション制御
├── robot_manager.py      # 統合管理（メインエントリーポイント）
├── api.py                # REST APIエンドポイント
├── websocket_handler.py  # WebSocketリアルタイム通信
└── sequence_manager.py   # 自動運転シーケンス

data/robot/
├── config.json           # 軸設定
├── positions.json        # ティーチングポイント
└── sequences.json        # シーケンス定義
```

---

## クイックスタート

### 基本的な使用方法

```python
from src.robot import RobotManager, create_robot_manager

# ロボットマネージャーを作成
robot = create_robot_manager(simulation_mode=True)

# 初期化
await robot.initialize()

# 原点復帰
await robot.home_all()

# 軸移動
await robot.move_axis(0, 100.0, speed_percent=50)
await robot.wait_motion_complete()

# ティーチングポイントへ移動
await robot.move_to_position("P001")

# シャットダウン
await robot.shutdown()
```

### コンテキストマネージャーを使用

```python
async with RobotManager() as robot:
    await robot.home_all()
    await robot.move_to_position("P001")
# 自動的にshutdown()が呼ばれる
```

---

## シミュレーションモード

シミュレーションモードは、実際のハードウェア（Raspberry Pi、モーションボード等）
がない環境でもコードをテスト・開発できる機能です。

### 有効化方法

```python
# 方法1: create_robot_manager使用
robot = create_robot_manager(simulation_mode=True)

# 方法2: RobotConfig使用
from src.robot import RobotManager, RobotConfig
config = RobotConfig(simulation_mode=True)
robot = RobotManager(config)
```

### シミュレーションされる機能

| コンポーネント | 通常モード | シミュレーションモード |
|---------------|-----------|----------------------|
| GPIO | 実際のピン制御 | 仮想状態を保持 |
| SPI/I2C | ハードウェア通信 | ダミーデータを返す |
| モーション | 実際の軸移動 | 位置を計算で更新 |
| CAN | MCP2515通信 | バッファ操作のみ |

### 用途

- 開発PCでのコーディング・デバッグ
- CI/CDでの自動テスト
- APIエンドポイントの開発

---

## モジュール詳細

### constants.py

**参照元**: `TEACHING/constant.py`, `TEACHING/splebo_n.py`

定数・Enum定義を集約。

```python
from src.robot import Axis, InputPort, OutputPort, RobotState

# 軸指定
axis = Axis.X  # 0
axis = Axis.Y  # 1

# 入力ポート
port = InputPort.DOOR_SENSOR  # 0

# 状態
state = RobotState.IDLE
```

### can_controller.py

**参照元**: `TEACHING/can.py`

MCP2515 CANコントローラをSPI経由で制御。

```python
from src.robot import CANController

can = CANController()
await can.initialize()

# データ送信
await can.send_can_data(board_id=0)

# 入力読み取り
value = can.get_input_bit(board_id=0, bit=5)
```

### io_expander.py

**参照元**: `TEACHING/splebo_n.py` (io_ex_input_class, io_ex_output_class)

I/Oエキスパンダボードの入出力制御。

```python
from src.robot import IOExpander

io = IOExpander(can_controller)

# 入力読み取り
door_open = await io.get_input(InputPort.DOOR_SENSOR)

# 出力設定
await io.set_output(OutputPort.BUZZER, True)

# センサーチェック
in_position = await io.check_driver_position()
```

### position_manager.py

**参照元**: `TEACHING/file_ctrl.py`

ティーチングポイントの管理。JSON形式で保存。

```python
from src.robot import PositionManager, Position

pm = PositionManager("data/robot/positions.json")
await pm.load()

# ポジション取得
pos = pm.get_position("P001")
print(f"X={pos.x}, Y={pos.y}, Z={pos.z}")

# 新規ポジション追加
new_pos = Position(name="P002", x=100.0, y=50.0, z=25.0)
pm.add_position(new_pos)
await pm.save()
```

### motion_controller.py

**参照元**: `TEACHING/motion_control.py` (2544行)

libcsms_splebo_n.soネイティブライブラリのラッパー。

```python
from src.robot import MotionController, AxisConfig, MotorType

mc = MotionController(simulation_mode=True)

# 軸設定
mc.set_axis_config(0, AxisConfig(
    motor_type=MotorType.IAI,
    max_speed=1000,
    pulse_length=0.01
))

await mc.initialize()

# 絶対位置移動
await mc.move_absolute(axis=0, position_mm=100.0, speed_percent=50)
await mc.wait_motion_complete(axis=0)

# JOG移動
await mc.move_jog(axis=0, direction_ccw=True, speed_percent=10)
await mc.stop(axis=0)

# 原点復帰
await mc.home_axis(axis=0)
```

### robot_manager.py

**参照元**: `TEACHING/splebo_n.py` (2246行)

全コンポーネントを統合管理するメインクラス。

```python
from src.robot import RobotManager, RobotEventType

robot = RobotManager()

# イベントハンドラ登録
async def on_motion_complete(event):
    print(f"Motion completed: {event.data}")

robot.events.on(RobotEventType.MOTION_COMPLETE, on_motion_complete)

await robot.initialize()

# 状態取得
status = robot.get_status()
print(f"State: {status.state}, Moving: {status.is_moving}")

# 現在位置取得
positions = robot.get_all_positions()
```

---

## TEACHING対応表

オリジナルのTEACHINGコードと新モジュールの対応関係です。

### ファイル対応

| TEACHING | 新モジュール | 備考 |
|----------|-------------|------|
| constant.py | constants.py | Enum化 |
| can.py | can_controller.py | asyncio化 |
| splebo_n.py (io_ex部分) | io_expander.py | 分離 |
| file_ctrl.py | position_manager.py | JSON形式に変更 |
| motion_control.py | motion_controller.py | asyncio化 |
| splebo_n.py (メイン) | robot_manager.py | 統合クラス化 |
| sample.py | sequence_manager.py | asyncio化・状態機械 |

### 主要関数対応

| TEACHING (motion_control.py) | 新モジュール |
|------------------------------|-------------|
| `motion_control_class.__init__()` | `MotionController.__init__()` |
| `initialize_motion_contoller()` | `MotionController.initialize()` |
| `motion_control_loop()` | `MotionController._control_loop()` |
| `cmd_move_absolute()` | `NativeLibrary.move_absolute()` |
| `cmd_stop()` | `NativeLibrary.stop()` |
| `homing_move_start_IAI()` | `MotionController._homing_start_iai()` |

| TEACHING (splebo_n.py) | 新モジュール |
|------------------------|-------------|
| `initialize()` | `RobotManager.initialize()` |
| `io_ex_input_class` | `IOExpander.get_input()` |
| `io_ex_output_class` | `IOExpander.set_output()` |
| `posi_data_class` | `PositionManager` |
| `homing_class` | `RobotManager.home_all()` |

---

## 設定ファイル

### data/robot/config.json

軸ごとの詳細設定を定義します。

```json
{
  "axes": [
    {
      "axis": 0,
      "name": "X",
      "motor_type": 1,
      "motor_type_name": "IAI",
      "max_speed": 1000,
      "pulse_length": 0.01,
      "limit_minus": 0.0,
      "limit_plus": 500.0
    }
  ]
}
```

### モータータイプ

| 値 | 名前 | 説明 |
|---|------|------|
| 0 | NONE | 未使用 |
| 1 | IAI | IAI電動アクチュエータ |
| 2 | STEPPING | ステッピングモータ |
| 3 | aSTEP | Oriental Motor aSTEP |

---

## トラブルシューティング

### ハードウェアモジュールが見つからない

```
WARNING: ハードウェアモジュール(spidev, RPi.GPIO)が見つかりません。シミュレーションモードで動作します。
```

→ 開発PC上での正常動作です。Raspberry Pi上では警告は出ません。

### libcsms_splebo_n.soが見つからない

```
ERROR: Failed to load native library
```

→ ライブラリパスを確認してください：
```python
robot = create_robot_manager(
    motion_lib_path="/path/to/libcsms_splebo_n.so"
)
```

---

## 開発ステータス

| Phase | 内容 | 状態 |
|-------|------|------|
| Phase 1 | 基盤構築 | ✅ 完了 |
| Phase 2 | モーション制御 | ✅ 完了 |
| Phase 3 | API統合 | ✅ 完了 |
| Phase 4 | シーケンス機能 | ✅ 完了 |

詳細は [TEACHING_INTEGRATION_TASKS.md](../../docs/TEACHING_INTEGRATION_TASKS.md) を参照。

---

## REST API

### エンドポイント一覧

| メソッド | パス | 説明 |
|---------|------|------|
| GET | /api/robot/status | ロボット状態取得 |
| GET | /api/robot/positions | 全軸位置取得 |
| POST | /api/robot/initialize | ロボット初期化 |
| POST | /api/robot/shutdown | シャットダウン |
| POST | /api/robot/home | 原点復帰 |
| POST | /api/robot/move | 軸移動 |
| POST | /api/robot/jog/start | JOG移動開始 |
| POST | /api/robot/jog/stop | JOG移動停止 |
| POST | /api/robot/stop | 緊急停止 |
| GET | /api/robot/teaching/positions | ティーチングポイント一覧 |
| POST | /api/robot/teaching/teach | 現在位置をティーチング |
| POST | /api/robot/teaching/move | ティーチングポイントへ移動 |
| POST | /api/robot/io/output | 出力ポート設定 |
| GET | /api/robot/io/input/{port} | 入力ポート読み取り |

### WebSocket

```
ws://localhost:8000/ws/robot
```

100msごとにロボット状態がJSON形式で配信されます。

```json
{
  "type": "status",
  "data": {
    "state": "IDLE",
    "mode": "MANUAL",
    "is_moving": false,
    "axis_positions": {"0": 100.0, "1": 50.0, ...}
  },
  "timestamp": "2026-01-07T12:00:00.000000"
}
```

---

## シーケンス機能

**参照元**: `TEACHING/sample.py` (932行)

自動運転シーケンスを管理・実行します。

### 使用例

```python
from src.robot import SequenceManager

seq = SequenceManager(robot_manager)

# イベントリスナー登録
seq.events.on('progress', lambda p: print(f"Step: {p.step_name}"))
seq.events.on('error', lambda e, m: print(f"Error: {e} - {m}"))
seq.events.on('complete', lambda: print("完了!"))

# シーケンス開始
await seq.start_sequence("screw_tightening")

# 一時停止/再開
seq.pause()
seq.resume()

# 停止
await seq.stop_sequence()
```

### 対応シーケンス

| シーケンス名 | 説明 |
|-------------|------|
| screw_tightening | ねじ取り・締めサイクル |
| homing | 原点復帰のみ |
| demo | デモ（テスト用） |

### TEACHINGコード対応

| TEACHING (sample.py) | 新モジュール |
|----------------------|-------------|
| EnumLoopState (L42-69) | LoopState |
| EnumScrewPickupState (L107-146) | ScrewPickupStep |
| EnumScrewTightState (L171-215) | ScrewTightStep |
| ScrewPickup() (L450-550) | _screw_pickup_sequence() |
| ScrewTight() (L600-750) | _screw_tight_sequence() |
| main_loop() (L850-930) | _screw_tightening_cycle() |
