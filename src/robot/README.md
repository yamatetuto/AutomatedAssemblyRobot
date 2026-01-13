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

## TEACHINGからの変更点

### コード規模比較

| カテゴリ | TEACHING | 新モジュール | 変化 |
|---------|----------|-------------|------|
| 総行数 | 6,875行 | 5,793行 | -16% |
| ファイル数 | 6個 | 10個 | +67% |

### ファイル対応表

```
TEACHING/                          src/robot/
├── constant.py (151行)      →    ├── constants.py (336行)      [拡張]
├── can.py (498行)           →    ├── can_controller.py (484行) [async化]
├── splebo_n.py (2245行)     →    ├── io_expander.py (309行)    [分離]
│                                 ├── robot_manager.py (1072行) [統合]
├── file_ctrl.py (507行)     →    ├── position_manager.py (438行)[JSON化]
├── motion_control.py (2543行)→   ├── motion_controller.py (1446行)[async化]
├── sample.py (931行)        →    ├── sequence_manager.py (520行)[簡略化]
│
│  ===== 以下は新規追加 =====
│                                 ├── api.py (567行)           [★新規]
│                                 ├── websocket_handler.py (494行)[★新規]
│                                 └── __init__.py (127行)       [★新規]
```

---

## アーキテクチャ図

### ファイル間の依存関係

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            app.py (FastAPI)                                  │
│                                  │                                           │
│                    ┌─────────────┼─────────────┐                            │
│                    ▼             ▼             ▼                            │
│              ┌─────────┐   ┌──────────┐   ┌───────────────────┐            │
│              │ api.py  │   │websocket_│   │  robot_manager.py │◄──────────┐│
│              │ [★新規] │   │handler.py│   │   【統合クラス】   │           ││
│              └────┬────┘   │ [★新規]  │   └────────┬──────────┘           ││
│                   │        └─────┬────┘            │                       ││
│                   └──────────────┼─────────────────┘                       ││
│                                  │                                          ││
│    ┌──────────────┬──────────────┼──────────────┬────────────────┐         ││
│    ▼              ▼              ▼              ▼                ▼         ││
│ ┌────────┐ ┌────────────┐ ┌──────────────┐ ┌─────────────┐ ┌──────────┐   ││
│ │sequence│ │  motion_   │ │can_controller│ │ io_expander │ │ position │   ││
│ │manager │ │ controller │ │    .py       │ │    .py      │ │ manager  │   ││
│ │[簡略化]│ │ [async化]  │ │  [async化]   │ │   [分離]    │ │ [JSON化] │   ││
│ └────┬───┘ └─────┬──────┘ └──────┬───────┘ └──────┬──────┘ └────┬─────┘   ││
│      │           │               │                │              │         ││
│      │           ▼               │                │              │         ││
│      │    ┌──────────────┐       │                │              │         ││
│      │    │ NativeLibrary│       └────────┬───────┘              │         ││
│      │    │  (ctypes)    │                │                      │         ││
│      │    └──────┬───────┘                ▼                      │         ││
│      │           │                 ┌────────────┐                │         ││
│      │           ▼                 │constants.py│◄───────────────┤         ││
│      │    ┌────────────┐           │  [拡張]    │                │         ││
│      │    │libcsms_    │           └────────────┘                │         ││
│      │    │splebo_n.so │                                         │         ││
│      │    └────────────┘                                         │         ││
│      │                                                           │         ││
│      └───────────────────────────────────────────────────────────┘         ││
│                                                                             ││
│    ┌────────────────────────────────────────────────────────────────────────┘│
│    │ イベントシステム (RobotEventEmitter)                                    │
│    └─────────────────────────────────────────────────────────────────────────┘
└──────────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
             ┌──────────┐   ┌────────────┐   ┌──────────┐
             │   GPIO   │   │  SPI/I2C   │   │   CAN    │
             │(RPi.GPIO)│   │  (spidev)  │   │(MCP2515) │
             └──────────┘   └────────────┘   └──────────┘
                    │               │               │
                    ▼               ▼               ▼
             ┌─────────────────────────────────────────┐
             │        ハードウェア / Raspberry Pi       │
             └─────────────────────────────────────────┘
```

### レイヤー構造

```
┌───────────────────────────────────────────────────────────────┐
│  Layer 4: API層 [★新規追加]                                   │
│  ┌───────────────┐  ┌───────────────────┐                    │
│  │   api.py      │  │ websocket_handler │                    │
│  │  REST API     │  │   リアルタイム通信  │                    │
│  └───────────────┘  └───────────────────┘                    │
├───────────────────────────────────────────────────────────────┤
│  Layer 3: 統合管理層                                          │
│  ┌───────────────────────────────────────┐                   │
│  │          robot_manager.py             │                   │
│  │  ┌─────────────┐ ┌─────────────────┐  │                   │
│  │  │ EventEmitter│ │ Status管理      │  │ ← [★新規機能]    │
│  │  └─────────────┘ └─────────────────┘  │                   │
│  └───────────────────────────────────────┘                   │
├───────────────────────────────────────────────────────────────┤
│  Layer 2: 機能モジュール層                                     │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐          │
│  │ motion_      │ │ io_expander  │ │ position_    │          │
│  │ controller   │ │  (I/O制御)   │ │ manager      │          │
│  │ (軸移動)     │ │              │ │ (ティーチング)│          │
│  └──────────────┘ └──────────────┘ └──────────────┘          │
│  ┌──────────────┐ ┌──────────────┐                           │
│  │ can_         │ │ sequence_    │                           │
│  │ controller   │ │ manager      │                           │
│  │ (CAN通信)    │ │ (自動運転)   │                           │
│  └──────────────┘ └──────────────┘                           │
├───────────────────────────────────────────────────────────────┤
│  Layer 1: 定数・型定義層                                       │
│  ┌───────────────────────────────────────┐                   │
│  │           constants.py                │                   │
│  │  Enum, IntEnum, dataclass, 定数       │                   │
│  └───────────────────────────────────────┘                   │
├───────────────────────────────────────────────────────────────┤
│  Layer 0: ハードウェア抽象化層                                  │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐          │
│  │ NativeLibrary│ │   spidev    │ │   smbus2     │          │
│  │   (ctypes)   │ │   (SPI)     │ │   (I2C)      │          │
│  └──────────────┘ └──────────────┘ └──────────────┘          │
└───────────────────────────────────────────────────────────────┘
```

---

## 新規追加クラス・機能の説明

### ★ 完全新規ファイル

#### 1. api.py (567行) - REST APIエンドポイント

**TEACHINGにない理由**: オリジナルはスタンドアロンのGUIアプリケーションで、Web API不要

**正当性**:
- FastAPIベースのアプリケーションに統合するため必須
- フロントエンド（ブラウザ）からのロボット制御を実現
- 既存の`app.py`のAPI設計パターンと統一

**主要クラス/関数**:
```python
create_robot_router()     # FastAPIルーター生成
MoveRequest/Response      # リクエスト/レスポンスモデル
JogRequest, HomeRequest   # 操作リクエスト
```

#### 2. websocket_handler.py (494行) - リアルタイム通信

**TEACHINGにない理由**: GUIはローカルで直接状態参照、通信不要

**正当性**:
- WebブラウザUIでリアルタイム状態表示に必須
- ポーリングではなくプッシュ通知で効率的
- 複数クライアント同時接続対応

**主要クラス/関数**:
```python
RobotWebSocketManager     # WebSocket接続管理
WebSocketMessage          # メッセージ型定義
_broadcast_status()       # 状態配信ループ
```

#### 3. __init__.py (127行) - モジュールエクスポート

**正当性**: Pythonパッケージとして利用するための標準的な構成

---

### ★ 新規追加機能（既存ファイル内）

#### robot_manager.py 内の新規機能

| 機能 | 説明 | 正当性 |
|-----|------|--------|
| `RobotEventEmitter` | イベント駆動通知 | WebSocket/UI連携に必須 |
| `RobotStatus` dataclass | 状態の型安全な管理 | API応答の一貫性 |
| `RobotConfig` dataclass | 設定の構造化 | 再利用性・テスト容易性 |
| `async with` 対応 | コンテキストマネージャ | リソース解放の安全性 |
| `create_robot_manager()` | ファクトリ関数 | 依存注入パターン |

#### motion_controller.py 内の新規機能

| 機能 | 説明 | 正当性 |
|-----|------|--------|
| `AxisConfig` dataclass | 軸設定の構造化 | 型安全性 |
| `AxisStatus` dataclass | 軸状態の構造化 | 一貫した状態管理 |
| `ControllerState` Enum | 状態機械 | 明示的な状態遷移 |
| シミュレーションモード | HW無しでテスト | CI/CD対応 |

#### constants.py 内の新規定義

| 追加内容 | 説明 |
|---------|------|
| `RobotState` Enum | IDLE, MOVING, ERROR等 |
| `SafetyState` Enum | 安全状態管理 |
| `RobotEventType` Enum | イベント種別 |
| `ErrorCode` Enum | エラーコード定義 |
| `Axis` IntEnum | X=0, Y=1, Z=2 の明確化 |

---

## TEACHING と新モジュールの詳細対応

### motion_control.py → motion_controller.py

```
TEACHING                          新モジュール
─────────────────────────────────────────────────────
motion_control_class              MotionController
├── __init__()                    ├── __init__()
├── initialize_motion_contoller() ├── initialize()        [async化]
├── motion_control_loop()         ├── _control_loop()     [async化]
├── cmd_move_absolute()           ├── move_absolute()     [async化]
├── cmd_move_relative()           ├── move_relative()     [async化]
├── cmd_jog()                     ├── move_jog()          [async化]
├── cmd_stop()                    ├── stop()              [async化]
├── homing_move_start_IAI()       ├── _homing_start_iai() [内部化]
└── write_bit() / read_board()    └── I2CIOExpander       [分離]

★新規:
├── NativeLibrary                 # ctypesラッパー分離
├── AxisConfig / AxisStatus       # 型定義追加
├── シミュレーションモード対応
└── wait_motion_complete()        # 非同期待機
```

### splebo_n.py → robot_manager.py + io_expander.py

```
TEACHING (splebo_n.py)            新モジュール
─────────────────────────────────────────────────────
io_ex_input_class                 io_expander.py
├── check_io()                    ├── get_input()
├── check_door()                  ├── is_door_open()
└── check_emergency()             └── is_emergency_active()

io_ex_output_class                io_expander.py
├── set_io()                      ├── set_output()
├── buzzer()                      ├── buzzer_beep()
└── led_control()                 └── blink_start_leds()

posi_data_class                   position_manager.py
├── load_posi()                   ├── load()
├── save_posi()                   ├── save()
└── get_posi()                    └── get_position()

homing_class                      robot_manager.py
├── homing_all()                  ├── home_all()
└── homing_axis()                 └── home_axis()

★新規 (robot_manager.py):
├── RobotEventEmitter             # イベント通知
├── RobotStatus                   # 状態管理
├── async with対応                # リソース管理
└── move_to_position()            # 高レベルAPI
```

### sample.py → sequence_manager.py

```
TEACHING (sample.py)              新モジュール
─────────────────────────────────────────────────────
RunOneCycle()                     SequenceManager
├── ScrewPickup()                 [削除] ← ねじ締め不要
├── ScrewTight()                  [削除] ← ねじ締め不要
├── MoveToPosition()              ├── run_point_sequence()
└── WaitComplete()                └── (内部で処理)

★新規:
├── run_custom_sequence()         # コールバック対応
├── SequenceState Enum            # 状態機械
├── pause() / resume()            # 一時停止/再開
├── イベント通知                   # 進捗コールバック
└── SequenceProgress              # 進捗情報
```

---

## ファイル構成

```
src/robot/
├── __init__.py           # モジュールエクスポート [★新規]
├── constants.py          # 定数・Enum定義        [拡張]
├── can_controller.py     # CAN通信制御          [async化]
├── io_expander.py        # I/O制御              [分離]
├── position_manager.py   # ポジション管理        [JSON化]
├── motion_controller.py  # モーション制御        [async化]
├── robot_manager.py      # 統合管理             [リファクタリング]
├── api.py                # REST API            [★新規]
├── websocket_handler.py  # WebSocket通信        [★新規]
└── sequence_manager.py   # 自動運転シーケンス     [簡略化]

data/robot/
├── config.json           # 軸設定
├── positions.json        # ティーチングポイント
└── sequences.json        # シーケンス定義
```

### データフロー図

```
                    ┌─────────────────┐
                    │   ブラウザ UI   │
                    └────────┬────────┘
                             │ HTTP/WebSocket
                    ┌────────▼────────┐
                    │    app.py       │
                    │   (FastAPI)     │
                    └────────┬────────┘
          ┌──────────────────┼──────────────────┐
          ▼                  ▼                  ▼
    ┌──────────┐      ┌──────────┐      ┌─────────────┐
    │  api.py  │      │websocket_│      │   他の API  │
    │ /robot/* │      │handler.py│      │ (gripper等) │
    └────┬─────┘      └────┬─────┘      └─────────────┘
         │                 │
         └────────┬────────┘
                  ▼
         ┌────────────────┐
         │ robot_manager  │ ◄──── 全機能の統合ポイント
         └───────┬────────┘
     ┌───────────┼───────────┬───────────┐
     ▼           ▼           ▼           ▼
┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
│ motion_ │ │   io_   │ │position_│ │sequence_│
│controller│ │expander │ │ manager │ │ manager │
└────┬────┘ └────┬────┘ └────┬────┘ └─────────┘
     │           │           │
     ▼           │           ▼
┌─────────┐      │      ┌─────────┐
│Native   │      │      │ JSON    │
│Library  │      │      │ファイル  │
└────┬────┘      │      └─────────┘
     │           │
     ▼           ▼
┌─────────┐ ┌─────────┐
│libcsms_ │ │  CAN    │
│splebo_n │ │Controller│
│  .so    │ └────┬────┘
└────┬────┘      │
     │           │
     ▼           ▼
┌─────────────────────────────────┐
│   ハードウェア (Raspberry Pi)    │
│  GPIO / SPI / I2C / CAN Bus    │
└─────────────────────────────────┘
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

**参照元**: `TEACHING/sample.py` (構造のみ参照)

XYZ軸移動とI/O制御のシーケンス実行を管理します。

### シーケンスタイプ

| タイプ | 説明 |
|-------|------|
| HOMING | 原点復帰シーケンス |
| POINT_MOVE | ティーチングポイント順次移動 |
| CUSTOM | カスタムシーケンス（ユーザー定義） |

### 基本的な使用方法

```python
from src.robot import SequenceManager, SequenceConfig

# シーケンスマネージャ作成
seq = SequenceManager(robot_manager)

# イベントリスナー登録
seq.events.on('progress', lambda p: print(f"Step {p.current_step}/{p.total_steps}: {p.step_name}"))
seq.events.on('error', lambda e, m: print(f"Error: {e} - {m}"))
seq.events.on('complete', lambda: print("シーケンス完了!"))
```

### 1. ポイント移動シーケンス

ティーチングポイントを順番に移動します。

```python
# ポジションを順番に移動
success = await seq.run_point_sequence(["P001", "P002", "P003"])

# 速度を指定して移動
success = await seq.run_point_sequence(
    positions=["HOME", "PICK", "PLACE"],
    speed_percent=30.0
)
```

### 2. 原点復帰シーケンス

全軸の原点復帰を実行します。

```python
success = await seq.run_homing_sequence()
```

### 3. カスタムシーケンス

ユーザー定義のコールバック関数でシーケンスを実行します。

```python
async def my_custom_sequence(robot, step):
    """
    カスタムシーケンスのコールバック関数
    
    Args:
        robot: RobotManagerインスタンス
        step: 現在のステップ番号 (1から開始)
    
    Returns:
        成功したかどうか
    """
    if step == 1:
        # ステップ1: X軸を100mmに移動
        await robot.move_axis(0, 100.0, speed_percent=50)
    elif step == 2:
        # ステップ2: Y軸を50mmに移動
        await robot.move_axis(1, 50.0, speed_percent=50)
    elif step == 3:
        # ステップ3: Z軸を25mmに下降
        await robot.move_axis(2, 25.0, speed_percent=30)
    elif step == 4:
        # ステップ4: 出力ポート0をON
        await robot.set_output(0, True)
    elif step == 5:
        # ステップ5: 0.5秒待機
        import asyncio
        await asyncio.sleep(0.5)
    elif step == 6:
        # ステップ6: 出力ポート0をOFF、Z軸を上昇
        await robot.set_output(0, False)
        await robot.move_axis(2, 0.0, speed_percent=50)
    
    return True  # 成功

# カスタムシーケンス実行
success = await seq.run_custom_sequence(my_custom_sequence, total_steps=6)
```

### シーケンス制御

```python
# 一時停止
seq.pause()

# 再開
seq.resume()

# 停止（緊急停止）
await seq.stop_sequence()

# 進捗取得
progress = seq.get_progress()
print(f"状態: {progress.state.name}")
print(f"ステップ: {progress.current_step}/{progress.total_steps}")
print(f"経過時間: {progress.elapsed_time:.1f}秒")
```

### 設定カスタマイズ

```python
from src.robot import SequenceConfig

config = SequenceConfig(
    move_timeout=60.0,      # 移動タイムアウト [秒]
    io_timeout=5.0,         # I/O確認タイムアウト [秒]
    default_speed=50.0,     # デフォルト移動速度 [%]
    z_down_speed=30.0,      # Z軸下降速度 [%]
    z_up_speed=50.0,        # Z軸上昇速度 [%]
    xy_speed=50.0,          # XY移動速度 [%]
    step_delay=0.1          # ステップ間待機時間 [秒]
)

seq = SequenceManager(robot_manager, config=config)
```

### イベント一覧

| イベント | 引数 | 説明 |
|---------|------|------|
| `started` | sequence_type: str | シーケンス開始 |
| `progress` | progress: SequenceProgress | ステップ進捗 |
| `paused` | なし | 一時停止 |
| `resumed` | なし | 再開 |
| `complete` | なし | 正常完了 |
| `error` | error: SequenceError, message: str | エラー発生 |
| `stopped` | なし | 停止（中断） |

### 実用的な例: ピック＆プレース

```python
from src.robot import RobotManager, SequenceManager, create_robot_manager

async def pick_and_place():
    # ロボット初期化
    robot = create_robot_manager(simulation_mode=True)
    await robot.initialize()
    await robot.home_all()
    
    # シーケンスマネージャ作成
    seq = SequenceManager(robot)
    
    # 進捗表示
    seq.events.on('progress', lambda p: print(f"[{p.current_step}/{p.total_steps}] {p.step_name}"))
    
    # ピック＆プレースシーケンス
    async def sequence(robot, step):
        if step == 1:
            await robot.move_to_position("PICK_APPROACH")
        elif step == 2:
            await robot.move_to_position("PICK")
        elif step == 3:
            await robot.set_output(0, True)  # グリッパー閉
            await asyncio.sleep(0.3)
        elif step == 4:
            await robot.move_to_position("PICK_APPROACH")
        elif step == 5:
            await robot.move_to_position("PLACE_APPROACH")
        elif step == 6:
            await robot.move_to_position("PLACE")
        elif step == 7:
            await robot.set_output(0, False)  # グリッパー開
            await asyncio.sleep(0.3)
        elif step == 8:
            await robot.move_to_position("PLACE_APPROACH")
        return True
    
    success = await seq.run_custom_sequence(sequence, total_steps=8)
    
    if success:
        print("ピック＆プレース完了!")
    else:
        print(f"エラー: {seq.get_progress().error_message}")
    
    await robot.shutdown()

# 実行
import asyncio
asyncio.run(pick_and_place())
```
