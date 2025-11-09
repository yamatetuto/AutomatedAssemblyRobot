# モジュール仕様書

## 概要

`src/` ディレクトリには、自動組み立てロボットの各機能を再利用可能なモジュールとして実装しています。

## ディレクトリ構造

```
src/
├── __init__.py              # パッケージエントリーポイント
├── camera/                  # カメラ制御モジュール
│   ├── __init__.py
│   └── camera_manager.py    # CameraManagerクラス
├── gripper/                 # グリッパー制御モジュール
│   ├── __init__.py
│   └── gripper_manager.py   # GripperManagerクラス
├── webrtc/                  # WebRTC通信モジュール
│   ├── __init__.py
│   └── webrtc_manager.py    # WebRTCManagerクラス
└── config/                  # 設定管理モジュール
    ├── __init__.py
    └── settings.py          # 設定定数
```

## モジュール詳細

### 1. CameraManager (カメラ管理)

**ファイル**: `src/camera/camera_manager.py`

**機能**:
- OpenCVを使ったカメラキャプチャ
- 非同期フレーム取得
- カメラ設定の変更（解像度、FPS）
- v4l2-ctlを使ったカメラコントロール
- スナップショット撮影

**使用例**:

```python
from src.camera.camera_manager import CameraManager

# インスタンス作成
camera = CameraManager()

# カメラ起動
await camera.start()

# フレーム取得
frame = camera.get_frame()

# スナップショット撮影
snapshot = await camera.take_snapshot()

# カメラ停止
await camera.stop()
```

**主なメソッド**:
- `async start()` - カメラキャプチャを開始
- `async stop()` - カメラキャプチャを停止
- `get_frame()` - 現在のフレームを取得
- `is_opened()` - カメラが開いているか確認
- `async take_snapshot()` - スナップショット撮影
- `get_controls()` - カメラコントロール一覧を取得
- `set_control(name, value)` - カメラコントロールを設定
- `async update_settings(width, height, fps)` - 解像度とFPSを更新

### 2. GripperManager (グリッパー管理)

**ファイル**: `src/gripper/gripper_manager.py`

**機能**:
- IAI製グリッパーのModbus RTU制御
- CONControllerをラップ
- 非同期操作対応
- ポジションテーブル管理

**使用例**:

```python
from src.gripper.gripper_manager import GripperManager

# インスタンス作成
gripper = GripperManager()

# 接続
await gripper.connect()

# ステータス取得
status = await gripper.get_status()

# サーボON
await gripper.servo_on()

# 原点復帰
await gripper.home()

# ポジション移動
await gripper.move_to_position(0)

# 切断
await gripper.disconnect()
```

**主なメソッド**:
- `async connect()` - グリッパーに接続
- `async disconnect()` - グリッパーから切断
- `async get_status()` - ステータス取得
- `async servo_on()` - サーボON
- `async servo_off()` - サーボOFF
- `async home()` - 原点復帰
- `async move_to_position(position_number)` - 指定ポジションに移動
- `async get_position_table(position_number)` - ポジションテーブル取得
- `async update_position_table(position_number, data)` - ポジションテーブル更新

### 3. WebRTCManager (WebRTC通信管理)

**ファイル**: `src/webrtc/webrtc_manager.py`

**機能**:
- aiortcを使ったWebRTC接続管理
- カメラ映像のストリーミング
- 複数クライアント対応

**使用例**:

```python
from src.webrtc.webrtc_manager import WebRTCManager

# インスタンス作成（CameraManagerを渡す）
webrtc = WebRTCManager(camera_manager)

# Offer処理
answer = await webrtc.create_offer(
    sdp=offer_sdp,
    type="offer"
)

# すべての接続を閉じる
await webrtc.close_all()
```

**主なメソッド**:
- `async create_offer(sdp, type)` - WebRTC Offerを処理してAnswerを返す
- `async close_peer_connection(pc)` - 特定のPeerConnectionを閉じる
- `async close_all()` - すべてのPeerConnectionを閉じる

### 4. 設定管理 (config.settings)

**ファイル**: `src/config/settings.py`

**機能**:
- 環境変数からの設定読み込み
- デフォルト値の管理
- プロジェクトルートの定義

**設定項目**:

```python
# カメラ設定
CAMERA_DEVICE = 0
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
CAMERA_FPS = 30
CAMERA_FOURCC = 'MJPG'

# グリッパー設定
GRIPPER_PORT = '/dev/ttyUSB0'
GRIPPER_SLAVE_ADDR = 1
GRIPPER_BAUDRATE = 38400

# WebRTC設定
STUN_SERVER = 'stun:stun.l.google.com:19302'

# ディレクトリ
PROJECT_ROOT = Path(__file__).parent.parent.parent
SNAPSHOTS_DIR = PROJECT_ROOT / 'snapshots'
POSITION_TABLE_FILE = PROJECT_ROOT / 'position_table.json'
```

**環境変数でのオーバーライド**:

```bash
export CAMERA_DEVICE=1
export CAMERA_WIDTH=1920
export CAMERA_HEIGHT=1080
export GRIPPER_PORT=/dev/ttyUSB1
```

## 統合使用例

```python
import asyncio
from src import CameraManager, GripperManager, WebRTCManager

async def main():
    # モジュール初期化
    camera = CameraManager()
    gripper = GripperManager()
    
    # 起動
    await camera.start()
    await gripper.connect()
    
    # WebRTC管理
    webrtc = WebRTCManager(camera)
    
    # 何か処理...
    
    # 終了
    await webrtc.close_all()
    await camera.stop()
    await gripper.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
```

## 利点

1. **再利用性**: 各モジュールが独立しているため、他のプロジェクトでも使用可能
2. **テスト容易性**: 各モジュールを個別にテストできる
3. **保守性**: 機能ごとに分離されているため、変更の影響範囲が限定的
4. **可読性**: コードが整理され、理解しやすい

## 次のステップ

- `web_app/main.py` でこれらのモジュールを使用した統合アプリケーションを構築
- 各モジュールの単体テストを作成
- ログ機能の拡充
