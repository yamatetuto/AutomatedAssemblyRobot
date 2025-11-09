# マルチRaspberry Pi構成への移行検証

**日付**: 2025-11-09  
**現状**: カメラとグリッパーを1台のRaspberry Piで制御  
**計画**: Raspberry Pi 2台構成への分離
  - **Pi 1**: ロボット操作用（グリッパー制御）
  - **Pi 2**: 画像処理用（カメラ + 画像認識）

## 1. 現在のアーキテクチャ分析

### 現状の実装（モノリシック構成）

```
┌─────────────────────────────────────────┐
│      Raspberry Pi (10.32.77.150)       │
│                                         │
│  ┌───────────────────────────────────┐  │
│  │         app.py (FastAPI)          │  │
│  │   - WebRTC映像配信                │  │
│  │   - カメラ制御API                 │  │
│  │   - グリッパー制御API             │  │
│  │   - Web UI (HTML/JS)              │  │
│  └───────────────────────────────────┘  │
│           ↓             ↓               │
│  ┌────────────┐  ┌──────────────┐      │
│  │  Camera    │  │   Gripper    │      │
│  │  Manager   │  │   Manager    │      │
│  └────────────┘  └──────────────┘      │
│        ↓               ↓                │
│  /dev/video0     /dev/ttyUSB0          │
│   (USB Camera)    (USB-RS485)          │
└─────────────────────────────────────────┘
```

### 利点
- ✅ 実装がシンプル
- ✅ ネットワーク遅延なし
- ✅ 同期処理が容易
- ✅ デバッグが簡単

### 欠点
- ❌ CPU負荷が1台に集中
- ❌ 画像処理とロボット制御の競合
- ❌ スケーラビリティが低い

## 2. 分離後のアーキテクチャ（推奨構成）

### 方式A: RESTful API通信（推奨）

```
┌──────────────────────────┐      HTTP/REST      ┌──────────────────────────┐
│   Raspberry Pi 2         │ ◄─────────────────► │   Raspberry Pi 1         │
│   (画像処理サーバー)     │                     │   (ロボット制御サーバー) │
│   IP: 10.32.77.151       │                     │   IP: 10.32.77.150       │
│                          │                     │                          │
│  ┌────────────────────┐  │                     │  ┌────────────────────┐  │
│  │  app_vision.py     │  │                     │  │  app_robot.py      │  │
│  │  (FastAPI)         │  │                     │  │  (FastAPI)         │  │
│  │                    │  │                     │  │                    │  │
│  │  - カメラ映像配信  │  │                     │  │  - グリッパー制御  │  │
│  │  - 画像認識API     │  │                     │  │  - ロボット制御    │  │
│  │  - WebRTC配信      │  │                     │  │  - 制御API         │  │
│  └────────────────────┘  │                     │  └────────────────────┘  │
│          ↓               │                     │          ↓               │
│  ┌───────────────┐       │                     │  ┌───────────────┐       │
│  │ CameraManager │       │                     │  │GripperManager │       │
│  └───────────────┘       │                     │  └───────────────┘       │
│          ↓               │                     │          ↓               │
│    /dev/video0           │                     │    /dev/ttyUSB0          │
│    (USB Camera)          │                     │    (USB-RS485)           │
└──────────────────────────┘                     └──────────────────────────┘
          ↓                                                ↑
    ┌──────────────┐                               ┌──────────────┐
    │ ユーザー     │ ◄───────── HTTP ────────────► │ 制御指令     │
    │ (ブラウザ)   │                               │              │
    └──────────────┘                               └──────────────┘
```

#### 通信フロー例
1. ユーザーがRPi2のWeb UIにアクセス
2. カメラ映像をWebRTCで配信
3. 画像認識結果に基づいて、RPi2からRPi1へHTTP POST
4. RPi1がグリッパーを制御
5. 制御結果をRPi2に返却
6. RPi2がユーザーに結果を表示

### 方式B: WebSocket通信（高頻度データ向け）

```
┌──────────────────────────┐    WebSocket    ┌──────────────────────────┐
│   Raspberry Pi 2         │ ◄─────────────► │   Raspberry Pi 1         │
│   (画像処理)             │  (双方向通信)   │   (ロボット制御)         │
└──────────────────────────┘                 └──────────────────────────┘
```

#### 利点
- リアルタイム性が高い
- 双方向通信が容易
- イベント駆動

#### 欠点
- 接続管理が複雑
- RESTより実装が複雑

## 3. 現在のコードベースの分離可能性

### ✅ 分離可能な部分（モジュール化済み）

#### CameraManager (src/camera/camera_manager.py)
```python
# そのままRPi2で使用可能
# 依存: OpenCV, asyncio のみ
# ハードウェア: /dev/video0
```

#### GripperManager (src/gripper/gripper_manager.py)
```python
# そのままRPi1で使用可能
# 依存: minimalmodbus, asyncio のみ
# ハードウェア: /dev/ttyUSB0
```

#### WebRTCManager (src/webrtc/webrtc_manager.py)
```python
# RPi2で使用（カメラ映像配信）
# 依存: aiortc
```

### ⚠️ 修正が必要な部分

#### app.py → app_vision.py と app_robot.py に分割

**app_vision.py (RPi2用)**
```python
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import httpx  # RPi1との通信用

from src.camera.camera_manager import CameraManager
from src.webrtc.webrtc_manager import WebRTCManager

app = FastAPI()
camera_manager = CameraManager()
webrtc_manager = WebRTCManager(camera_manager)

# カメラAPI
@app.get("/api/camera/status")
async def camera_status():
    ...

# 画像認識API
@app.post("/api/vision/detect")
async def detect_object(request: Request):
    # 画像認識処理
    result = await perform_detection()
    
    # RPi1のグリッパーを制御
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://10.32.77.150:8080/api/gripper/move/5",
            json={"position": result["position"]}
        )
    
    return result

# WebRTC配信
@app.post("/offer")
async def offer(request: Request):
    ...
```

**app_robot.py (RPi1用)**
```python
from fastapi import FastAPI
from src.gripper.gripper_manager import GripperManager

app = FastAPI()
gripper_manager = GripperManager()

# グリッパーAPI
@app.get("/api/gripper/status")
async def gripper_status():
    ...

@app.post("/api/gripper/move/{position}")
async def gripper_move(position: int):
    ...

@app.get("/api/gripper/current")
async def gripper_current():
    ...

@app.get("/api/gripper/grip_status")
async def gripper_grip_status():
    ...
```

## 4. 実装手順

### フェーズ1: 準備（現在のコードベースで実施）
1. ✅ モジュール化完了（src/camera, src/gripper, src/webrtc）
2. ✅ 各マネージャーの独立性確認
3. ✅ API設計の見直し

### フェーズ2: 分離実装
1. **app.pyを2つに分割**
   - `app_vision.py`: カメラ + WebRTC + 画像認識
   - `app_robot.py`: グリッパー + ロボット制御

2. **通信レイヤーの実装**
   ```python
   # app_vision.pyに追加
   import httpx
   
   ROBOT_API_BASE = "http://10.32.77.150:8080"
   
   async def call_robot_api(endpoint: str, method="GET", **kwargs):
       async with httpx.AsyncClient(timeout=10.0) as client:
           if method == "GET":
               response = await client.get(f"{ROBOT_API_BASE}{endpoint}")
           elif method == "POST":
               response = await client.post(
                   f"{ROBOT_API_BASE}{endpoint}",
                   **kwargs
               )
           return response.json()
   ```

3. **Web UIの分割**
   - RPi2: カメラ映像 + 画像認識UI
   - RPi1: グリッパー制御UI（オプション）

### フェーズ3: テスト
1. 単体テスト（各Pi個別）
2. 統合テスト（Pi間通信）
3. 性能テスト（遅延測定）

### フェーズ4: 最適化
1. 通信のタイムアウト設定
2. エラーハンドリング
3. リトライロジック
4. ログ集約

## 5. 通信プロトコルの詳細設計

### グリッパー制御API（RPi1提供）

```python
# 基本制御
GET  /api/gripper/status          # ステータス取得
POST /api/gripper/servo/{action}  # サーボON/OFF
POST /api/gripper/home            # 原点復帰
POST /api/gripper/move/{position} # ポジション移動

# 把持判定（新規）
GET  /api/gripper/current         # 電流値取得
GET  /api/gripper/grip_status     # 把持状態判定

# ポジションテーブル
GET  /api/gripper/position_table/{position}
POST /api/gripper/position_table/{position}
```

### 画像認識API（RPi2提供）

```python
# カメラ制御
GET  /api/camera/status           # カメラステータス
POST /api/camera/settings         # パラメータ設定
GET  /api/camera/snapshot         # 静止画取得

# 画像認識（追加実装）
POST /api/vision/detect           # 物体検出
POST /api/vision/measure          # 寸法測定
POST /api/vision/inspect          # 外観検査
```

### 統合ワークフローAPI（RPi2で実装）

```python
POST /api/workflow/pick_and_place
# 1. カメラで対象物検出
# 2. 位置・姿勢計算
# 3. RPi1へグリッパー移動指令
# 4. 把持判定
# 5. 結果返却
```

## 6. 懸念事項と対策

### 懸念1: ネットワーク遅延
- **測定**: ping 10.32.77.150 → 通常<1ms
- **対策**: タイムアウト設定（5-10秒）
- **モニタリング**: 応答時間のログ記録

### 懸念2: 通信エラー
- **対策**: リトライロジック（最大3回）
- **フォールバック**: エラー時の安全停止
- **ログ**: エラー詳細の記録

### 懸念3: 同期処理
- **現状**: 同一プロセス内で同期が容易
- **分離後**: HTTP呼び出しで await を使用
- **対策**: 状態管理をRPi2で一元化

### 懸念4: デバッグの複雑化
- **対策**: 各Piで独立したログ
- **ツール**: Grafana/Prometheusでメトリクス可視化
- **開発環境**: Docker Composeでローカル再現

## 7. 現在の実装で問題ない理由

### ✅ モジュール化が完了している
- `src/camera`, `src/gripper`, `src/webrtc` が独立
- 各マネージャーは疎結合
- FastAPIのルーター分離が容易

### ✅ 非同期処理が適切
- `asyncio.to_thread()` で同期処理を分離済み
- イベントループのブロックを回避
- ネットワーク通信への対応が容易

### ✅ API設計がRESTful
- エンドポイントが明確
- HTTPメソッドの使い分けが適切
- そのまま他のPiから呼び出し可能

## 8. 移行のリスクと対応

### リスク: 低
- **理由**: 現在のコードベースが分離前提で設計されている
- **証拠**: モジュール化、API化、非同期処理

### 必要な作業量: 中
- **app.pyの分割**: 1-2日
- **通信レイヤー実装**: 1日
- **テスト**: 2-3日
- **合計**: 約1週間

### 推奨タイミング
1. **現在**: 単一Pi構成で機能を完成させる
2. **次フェーズ**: 画像認識機能を追加
3. **最終フェーズ**: 負荷が高くなったら分離

## 9. 結論

### 現在の実装方法で問題なし ✅

**理由**:
1. ✅ モジュール化が適切に行われている
2. ✅ 各マネージャーが独立している
3. ✅ API設計がRESTful
4. ✅ 非同期処理が適切
5. ✅ 将来の分離が容易

### 分離時の修正箇所（最小限）

```python
# 修正前（現在）
await gripper_manager.move_to_position(5)

# 修正後（分離後）
async with httpx.AsyncClient() as client:
    await client.post("http://10.32.77.150:8080/api/gripper/move/5")
```

### 推奨事項

1. **現状維持**: 単一Pi構成で開発を継続
2. **API完成**: すべてのAPI機能を実装
3. **負荷測定**: CPU使用率・応答時間を計測
4. **閾値設定**: CPU > 80%、応答時間 > 100ms で分離検討
5. **段階的移行**: まずWebRTC配信のみ分離してテスト

### 将来的な拡張性

現在のアーキテクチャは以下の構成にも対応可能:
- 2台構成（カメラ + ロボット）
- 3台構成（カメラ + 画像処理 + ロボット）
- N台構成（複数ロボット、複数カメラ）
- クラウド連携（AWS/Azure + エッジ）
