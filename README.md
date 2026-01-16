# 🤖 AutomatedAssemblyRobot

積層型3Dプリンター、ディスペンサー、XYZ直交ロボットを組み合わせた医療機器の自動組立システム

---

## 📋 プロジェクト概要

本プロジェクトは、以下のデバイスを統合制御し、医療機器の自動組立を実現するシステムです:

- **3Dプリンター** (Tronxy GEMINI S) - OctoPrint経由で制御
- **XYZ直交ロボット** (株式会社コスモスウェブ製 SPLEBO-N) - libcsms_splebo_n.so経由で制御
- **電動グリッパー** (IAI社 RCP2-GRSS) - Modbus RTU通信
- **ディスペンサー** - Raspberry Pi GPIO制御
- **カメラ** (Logitech C922 Pro) - OpenCV + WebRTC

---

## 🎯 主要機能

### ✅ 実装済み
- [x] **WebRTCリアルタイムストリーミング** - 低遅延カメラ映像配信
- [x] **グリッパー制御** (Modbus RTU) - 位置決め、把持、サーボ制御
- [x] **電流値モニタリング** - リアルタイムグラフ表示
- [x] **把持状態判定** - PSFL、電流値、MOVE信号による多重判定
- [x] **ポジションテーブル管理** - 64ポジションのパラメータ設定
- [x] **カメラパラメータ調整** - 明るさ、コントラスト、露出、フォーカス等
- [x] **スナップショット撮影** - タイムスタンプ付き画像保存
- [x] **統合Web UI** - FastAPI + WebRTC対応制御画面
- [x] **モジュール化アーキテクチャ** - 再利用可能なコンポーネント設計
- [x] **Modbus排他制御** - asyncio.Lock()による通信の安定化
- [x] **3Dプリンター制御** (OctoPrint API) - 状態監視、一時停止/再開(退避動作付)
- [x] **SPLEBO-N XYZ直交ロボット制御** - asyncio対応、REST API、WebSocket状態配信

### 🚧 実装中
- [ ] 電流値取得の安定化（Modbusタイムアウト対策）
- [ ] ディスペンサー制御 (GPIO)
- [ ] 自動組立シーケンス

### ✅ 画像処理（Vision）
- [x] **光ファイバー検出** - Cannyエッジ + Hough変換による直線検出
- [x] **ガラス玉検出** - Hough円変換による円形物体検出
- [x] **オフセット計算** - 画像中心からの距離算出

---

## 🏗️ ディレクトリ構造

```
AutomatedAssemblyRobot/
├── app.py                     # 統合アプリケーション（メイン）
├── src/                       # モジュール化されたソースコード
│   ├── camera/               # カメラ管理モジュール
│   │   ├── __init__.py
│   │   ├── camera_manager.py # OpenCV + V4L2カメラ制御
│   │   └── README.md
│   ├── gripper/              # グリッパー管理モジュール
│   │   ├── __init__.py
│   │   ├── gripper_manager.py  # 高レベルAPI（排他制御、キャッシュ）
│   │   ├── controller.py       # CONController (Modbus RTU通信)
│   │   └── README.md
│   ├── robot/                # SPLEBO-N XYZ直交ロボット制御
│   │   ├── __init__.py
│   │   ├── robot_manager.py    # 統合管理クラス
│   │   ├── motion_controller.py # モーション制御
│   │   ├── can_controller.py   # CAN通信 (MCP2515)
│   │   ├── io_expander.py      # I/O制御
│   │   ├── position_manager.py # ティーチングポジション管理
│   │   ├── sequence_manager.py # シーケンス実行
│   │   ├── api.py              # REST APIエンドポイント
│   │   ├── websocket_handler.py # WebSocket状態配信
│   │   ├── constants.py        # 定数・Enum定義
│   │   └── README.md
│   ├── webrtc/               # WebRTC管理モジュール
│   │   ├── __init__.py
│   │   ├── webrtc_manager.py   # aiortc WebRTC接続管理
│   │   └── README.md
│   ├── printer/              # 3Dプリンター管理モジュール
│   │   ├── __init__.py
│   │   ├── octoprint_client.py # OctoPrint REST APIクライアント
│   │   ├── printer_manager.py  # 高レベルプリンター制御
│   │   └── README.md
│   ├── vision/               # 画像処理モジュール
│   │   ├── __init__.py
│   │   ├── manager.py          # VisionManager（検出統括）
│   │   └── detectors/          # 検出器
│   │       ├── __init__.py
│   │       ├── base.py         # BaseDetector（抽象基底クラス）
│   │       ├── fiber.py        # FiberDetector（光ファイバー検出）
│   │       └── bead.py         # BeadDetector（ガラス玉検出）
│   └── config/               # 設定管理モジュール
│       ├── __init__.py
│       └── settings.py         # 環境変数読み込み
├── data/                      # データファイル
│   └── robot/                 # ロボット設定・ポジションデータ
│       ├── config.json        # 軸設定
│       ├── positions.json     # ティーチングポイント
│       └── sequences.json     # シーケンス定義
├── web_app/                   # Webアプリケーション
│   ├── main_webrtc_fixed.py  # 旧メインファイル（参考用）
│   ├── static/               # 静的ファイル
│   │   ├── css/             
│   │   │   └── style.css    # メインCSS
│   │   └── js/              
│   │       └── app.js       # UIロジック（電流値グラフ、把持判定等）
│   └── templates/            # HTMLテンプレート
│       └── index_webrtc_fixed.html
├── scripts/                   # 運用スクリプト
│   ├── start_all.sh          # 全サービス起動（旧マイクロサービス用）
│   ├── stop_all.sh           # 全サービス停止
│   └── health_check.sh       # ヘルスチェック
├── snapshots/                 # スナップショット保存先
├── requirements.txt           # Python依存パッケージ
├── setup.py                   # パッケージ設定
└── README.md                  # このファイル
```

---

## 💻 システム要件

### ハードウェア
- **Raspberry Pi 4 Model B** (4GB RAM以上推奨)
  - IPアドレス: 10.32.77.150（設定例）
- **USBカメラ**: Logitech C922 Pro
- **IAI RCP2-GRSSグリッパー** + USB-RS485変換アダプタ
- **ネットワーク接続** (Wi-Fi/Ethernet)

### ソフトウェア
- **OS**: Raspberry Pi OS 11 (Bullseye) 以上
- **Python**: 3.9 以上
- **必須パッケージ**:
  - OpenCV 4.6+
  - FastAPI 0.100+
  - aiortc 1.6+ (WebRTC)
  - minimalmodbus 2.0+ (Modbus RTU)
  - uvicorn (ASGIサーバー)
  - jinja2 (テンプレートエンジン)

---

## 🚀 インストール

### 1. システム準備
```bash
# システムパッケージの更新
sudo apt update && sudo apt upgrade -y

# 必須ツールのインストール
sudo apt install -y git v4l-utils
```

### 2. リポジトリのクローン
```bash
cd ~
git clone https://github.com/yamatetuto/AutomatedAssemblyRobot.git
cd AutomatedAssemblyRobot
```

### 3. Python依存パッケージのインストール

#### Step 1: aptでインストール（推奨）
```bash
# Webアプリケーション
sudo apt install -y python3-fastapi python3-uvicorn python3-pydantic python3-multipart python3-jinja2 python3-websockets

# カメラ・映像処理
sudo apt install -y python3-opencv python3-numpy python3-aiohttp python3-av

# ハードウェア通信 (Raspberry Pi)
sudo apt install -y python3-serial python3-spidev python3-smbus python3-rpi.gpio

# 設定管理
sudo apt install -y python3-yaml python3-dotenv

# テスト・開発ツール（オプション）
sudo apt install -y python3-pytest python3-flake8 python3-mypy
```

#### Step 2: pipでインストール（aptで利用不可のパッケージ）
```bash
# aiortc: WebRTC (カメラストリーミング)
# minimalmodbus: Modbus通信 (グリッパー制御)
pip3 install --break-system-packages aiortc minimalmodbus

# テスト追加パッケージ（オプション）
pip3 install --break-system-packages pytest-asyncio pytest-cov
```

> **Note**: `--break-system-packages` オプションはRaspberry Pi OS (Bookworm以降)で
> システムワイドにpipパッケージをインストールする際に必要です。

### 4. デバイス接続確認
```bash
# カメラデバイスの確認
v4l2-ctl --list-devices

# グリッパー（USB-RS485）の確認
ls -l /dev/ttyUSB*

# 権限設定
sudo usermod -a -G video,dialout $USER
# ログアウト・ログインが必要
```

---

## 🎮 使用方法

### 統合アプリケーション起動（推奨）

```bash
cd ~/AutomatedAssemblyRobot
python app.py
```

**アクセス**: ブラウザで `http://<Raspberry_PiのIPアドレス>:8080` を開く

例: `http://10.32.77.150:8080`

#### Web UI機能
- **📹 カメラ映像**: WebRTCによる低遅延ストリーミング（~300ms）
- **📸 スナップショット**: 画像キャプチャと一覧表示
- **🎛️ カメラ設定**: 
  - スライダー調整（明るさ、コントラスト、彩度、シャープネス、ゲイン等）
  - チェックボックス（オートホワイトバランス、オートフォーカス等）
  - セレクトボックス（露出モード、電源周波数等）
  - 解像度変更（320x240～1920x1080）
  - コーデック変更（MJPEG/YUYV）
- **🤏 グリッパー制御**:
  - サーボON/OFF
  - 原点復帰
  - ポジション移動（0-63）
  - ポジションテーブル編集（位置、幅、速度、加減速、押当電流）
  - 全64ポジション一覧表示（ページネーション対応）
  - **🆕 電流値モニター**: リアルタイムグラフ表示（Chart.js）
  - **🆕 把持状態判定**: 成功/失敗/警告/移動中の自動判定
- **📊 ステータス表示**: 右上に現在位置とサーボ状態を常時表示

### ロボットデーモン + app.py 同時起動

robot_daemon と app.py を同時に起動するスクリプトを追加しました。

```bash
cd ~/AutomatedAssemblyRobot
scripts/start_robot_app.sh
```

ログ出力:
- logs/robot_daemon.log
- logs/app.log

### バックグラウンド起動

サーバーをバックグラウンドで実行:

```bash
nohup python app.py > app.log 2>&1 &
```

ログ確認:
```bash
tail -f app.log
```

停止:
```bash
pkill -f "python.*app.py"
```

---

## 📡 API仕様

### カメラAPI

| メソッド | エンドポイント | 説明 |
|---------|---------------|------|
| GET | `/api/camera/status` | カメラ状態取得 |
| GET | `/api/camera/controls` | コントロール一覧取得 |
| POST | `/api/camera/control/{name}/{value}` | パラメータ設定 |
| GET | `/api/camera/resolutions` | 対応解像度一覧 |
| POST | `/api/camera/resolution` | 解像度変更 |
| POST | `/api/camera/codec` | コーデック変更 |
| POST | `/api/camera/snapshot` | スナップショット撮影 |
| GET | `/api/camera/snapshots` | スナップショット一覧 |
| GET | `/api/camera/snapshots/{filename}` | スナップショット取得 |

### グリッパーAPI

| メソッド | エンドポイント | 説明 |
|---------|---------------|------|
| GET | `/api/gripper/status` | ステータス取得 |
| POST | `/api/gripper/servo/{action}` | サーボON/OFF (`on`\|`off`) |
| POST | `/api/gripper/home` | 原点復帰 |
| POST | `/api/gripper/move/{position}` | ポジション移動 (0-63) |
| GET | `/api/gripper/position_table/{position}` | ポジションデータ取得 |
| POST | `/api/gripper/position_table/{position}` | ポジションデータ設定 |
| **🆕** GET | `/api/gripper/current` | **電流値取得（mA）** |
| **🆕** GET | `/api/gripper/grip_status` | **把持状態判定** |

#### 把持状態判定レスポンス

```json
{
  "status": "success",  // "success" | "failure" | "warning" | "moving"
  "reason": "normal",   // 詳細理由
  "current": 150,       // 電流値（mA）
  "position_mm": 45.23, // 現在位置（mm）
  "psfl": false,        // 押付け空振りフラグ
  "confidence": "high"  // 判定信頼度
}
```

### WebRTC API

| メソッド | エンドポイント | 説明 |
|---------|---------------|------|
| POST | `/api/webrtc/offer` | WebRTC接続確立 |

### 3Dプリンター API

| メソッド | エンドポイント | 説明 |
|---------|---------------|------|
| GET | `/api/printer/status` | プリンター状態取得 |
| POST | `/api/printer/pause` | 一時停止（退避動作付） |
| POST | `/api/printer/resume` | 再開（位置復帰付） |
| GET | `/api/printer/files` | ファイル一覧取得 |

### 画像処理 API

| メソッド | エンドポイント | 説明 |
|---------|---------------|------|
| POST | `/api/vision/fiber` | 光ファイバー検出 |
| POST | `/api/vision/bead` | ガラス玉検出 |

### XYZ直交ロボット API (SPLEBO-N)

| メソッド | エンドポイント | 説明 |
|---------|---------------|------|
| GET | `/api/robot/status` | ロボット状態取得 |
| GET | `/api/robot/positions` | 全軸位置取得 |
| POST | `/api/robot/initialize` | ロボット初期化 |
| POST | `/api/robot/shutdown` | シャットダウン |
| POST | `/api/robot/home` | 原点復帰 |
| POST | `/api/robot/move` | 軸移動 |
| POST | `/api/robot/jog/start` | JOG移動開始 |
| POST | `/api/robot/jog/stop` | JOG移動停止 |
| POST | `/api/robot/stop` | 緊急停止 |
| GET | `/api/robot/teaching/positions` | ティーチングポイント一覧 |
| POST | `/api/robot/teaching/teach` | 現在位置をティーチング |
| POST | `/api/robot/teaching/move` | ティーチングポイントへ移動 |
| DELETE | `/api/robot/teaching/positions/{name}` | ポイント削除 |
| GET | `/api/robot/io/input/{port}` | 入力ポート読み取り |
| POST | `/api/robot/io/output` | 出力ポート設定 |
| WS | `/ws/robot` | リアルタイム状態配信 (WebSocket) |

---

## ⚙️ 設定

環境変数で設定をカスタマイズできます（`src/config/settings.py`参照）:

```bash
export CAMERA_DEVICE=0
export CAMERA_WIDTH=640
export CAMERA_HEIGHT=480
export CAMERA_FPS=30
export GRIPPER_PORT=/dev/ttyUSB0
export GRIPPER_BAUDRATE=38400
export GRIPPER_SLAVE_ADDR=1

# 3Dプリンター設定
export OCTOPRINT_URL=http://127.0.0.1:5000
export OCTOPRINT_API_KEY=your_api_key_here
export OCTOPRINT_POLL_INTERVAL=5.0

# 画像処理設定
export VISION_FIBER_CANNY_THRESHOLD1=50
export VISION_FIBER_CANNY_THRESHOLD2=150
export VISION_BEAD_MIN_DIST=20
export VISION_BEAD_PARAM2=30

# XYZ直交ロボット設定 (SPLEBO-N)
export ROBOT_SIMULATION_MODE=true     # シミュレーションモード（開発用）
export ROBOT_CAN_SPI_BUS=0            # SPI バス番号
export ROBOT_CAN_SPI_DEVICE=0         # SPI デバイス番号
export ROBOT_GPIO_NOVA_RESET=14       # NOVAリセットピン
export ROBOT_GPIO_POWER=12            # 電源ピン
export ROBOT_GPIO_CAN_CS=8            # CAN CSピン
export ROBOT_GPIO_EMG_SW=15           # 非常停止スイッチピン
```

---

## 🔧 トラブルシューティング

### カメラが認識されない
```bash
# デバイス確認
v4l2-ctl --list-devices

# 権限確認
ls -l /dev/video0
sudo usermod -a -G video $USER
# ログアウト・ログインが必要
```

### グリッパーが通信できない
```bash
# デバイス確認
ls -l /dev/ttyUSB*

# 権限設定
sudo usermod -a -G dialout $USER
# ログアウト・ログインが必要

# ボーレート確認（グリッパー本体の設定: 38400bps）
```

### Modbus通信エラー（"No communication with the instrument"）

**症状**: 電流値取得やポジション移動時にタイムアウトエラー

**原因**: 複数のAPIリクエストが同時にModbusアクセスし、通信が混雑

**対策**:
- v2.2で実装済み: `asyncio.Lock()`による排他制御
- 電流値取得間隔を500msに設定（調整可能）
- さらなる調整が必要な場合: `web_app/static/js/app.js`の`setInterval`値を変更

### Web UIにアクセスできない
```bash
# サーバーが起動しているか確認
ps aux | grep "python.*app.py"

# ポート8080が使用されているか確認
sudo netstat -tulpn | grep 8080

# ファイアウォール確認（必要に応じて）
sudo ufw allow 8080
```

### カメラ映像が表示されない
- ブラウザを `Ctrl+Shift+R` でハードリフレッシュ
- ブラウザのコンソールでエラーを確認
- サーバーを再起動

### 640x480以上で映像が止まる
- **v2.1で修正済み**: フォーマット設定順序を最適化
- コーデックをMJPEGに設定してください

---

## 🏛️ アーキテクチャ

### v2.0からの変更点

**v1.x**: モノリシック設計（web_app/main_webrtc_fixed.py）
- すべての機能を1ファイルに実装
- 動作は安定しているが保守性に課題

**v2.0**: モジュール化アーキテクチャ（app.py + src/）
- 各機能を独立したモジュールに分割
- 再利用性とテスト容易性の向上
- パフォーマンス最適化（同期的Modbus通信）

**v2.2**: Modbus排他制御実装
- [x] **3Dプリンター制御** (OctoPrint API) - 状態監視、一時停止/再開(退避動作付)
- `asyncio.Lock()`による通信の競合解消
- すべてのModbus操作を非同期化
- 安定性と応答性の向上

### モジュール構成

```python
# カメラ管理
from src.camera.camera_manager import CameraManager

# グリッパー管理
from src.gripper.gripper_manager import GripperManager

# WebRTC管理
from src.webrtc.webrtc_manager import WebRTCManager

# 設定
from src.config.settings import *
```

### Modbus排他制御の仕組み
- [x] **3Dプリンター制御** (OctoPrint API) - 状態監視、一時停止/再開(退避動作付)

GripperManagerクラスで`asyncio.Lock()`を使用:

```python
class GripperManager:
    def __init__(self):
        self._modbus_lock = asyncio.Lock()  # 排他制御
    
    async def get_current(self):
        async with self._modbus_lock:  # ロック取得
            current = await asyncio.to_thread(
                self.controller.instrument.read_register, 0x900C
            )
            return current
```

すべてのModbus操作（ステータス取得、移動、電流値取得等）が同じロックを使用するため、通信が順次実行されます。

### なぜマイクロサービスではないのか？

初期設計ではマイクロサービスアーキテクチャを検討しましたが、以下の理由で断念:

1. **ハードウェア排他制御**: カメラとグリッパーは1プロセスのみがアクセス可能
2. **通信オーバーヘッド**: プロセス間通信によるレイテンシー増加
3. **デプロイの複雑性**: Raspberry Pi上での複数プロセス管理

→ **モジュール化設計**を採用し、コードの再利用性を維持しつつ単一プロセスで統合

---

## 📚 ドキュメント

詳細なドキュメントは `docs/` ディレクトリを参照:

- [要件定義書](docs/requirements.md) - システム要件とAPI仕様
- [デバイス仕様書](docs/device_specifications.md) - ハードウェア仕様
- [データスキーマ定義](docs/schema.md) - データ構造
- [調査レポート](docs/reports/) - 技術調査結果

---

## 🤝 コントリビューション

1. このリポジトリをフォーク
2. フィーチャーブランチを作成 (`git checkout -b feature/amazing-feature`)
3. 変更をコミット (`git commit -m 'feat: Add amazing feature'`)
4. ブランチにプッシュ (`git push origin feature/amazing-feature`)
5. プルリクエストを作成

### コミットメッセージ規約（Semantic Commits）
- `feat:` 新機能
- `fix:` バグ修正
- `docs:` ドキュメント
- `chore:` 雑務（依存関係更新など）
- `test:` テスト
- `refactor:` リファクタリング

---

## 📄 ライセンス

このプロジェクトは研究用途です。商用利用については別途相談してください。

---

## 📞 サポート

問題が発生した場合:
1. [トラブルシューティング](#-トラブルシューティング)を確認
2. [要件定義書](docs/requirements.md)を参照
3. GitHubでIssueを作成

---

## 🙏 謝辞

- 株式会社コスモスウェブ - 自動組立装置の製作
- IAI社 - 電動グリッパー提供
- OpenCV、FastAPI、aiortcコミュニティ

---

## 📝 更新履歴

### v3.0 (2026-01-07)
- **SPLEBO-N XYZ直交ロボット制御モジュール追加**
  - `src/robot/` モジュール新規作成
  - asyncio対応の非同期モーション制御
  - REST API エンドポイント20種類以上
  - WebSocketリアルタイム状態配信（100ms間隔）
  - シミュレーションモード対応（開発PC用）
  - ティーチングポジション管理（JSON形式）
  - シーケンス実行エンジン（ポイント移動、カスタムシーケンス）
- **ロボット制御API**
  - `/api/robot/` 配下にRESTエンドポイント追加
  - `/ws/robot` WebSocketエンドポイント追加
- **依存関係追加**
  - spidev==3.6 (SPI通信)
  - smbus2==0.4.3 (I2C通信)
  - jinja2==3.1.2 (テンプレート)

### v2.2 (2025-11-09)
- **電流値モニタリング機能追加**
  - リアルタイム電流値取得API (`/api/gripper/current`)
  - Chart.jsによるグラフ表示（60ポイント、500ms更新）
  - 電流値パネルUIの実装
- **把持状態判定機能追加**
  - 多重判定ロジック実装（PSFL、電流閾値、MOVE信号）
  - API (`/api/gripper/grip_status`) 追加
  - 成功/失敗/警告/移動中の4状態判定
  - LEDインジケーターUI実装
- **Modbus排他制御実装**
- [x] **3Dプリンター制御** (OctoPrint API) - 状態監視、一時停止/再開(退避動作付)
  - `asyncio.Lock()`による通信競合の解消
  - すべてのModbus操作を非同期化（`asyncio.to_thread()`）
  - タイムアウトエラーの削減
- **PEND信号からMOVE信号への変更**
  - 不安定なPENDビットを使用停止
  - MOVEビット（0x9007 bit 5）による移動検出に変更
  - より信頼性の高い状態判定を実現
- **CSS/JS分離**
  - `web_app/static/css/style.css` 作成
  - `web_app/static/js/app.js` 作成
  - HTMLファイルの保守性向上
- **バグ修正**
  - Chart.js高さ制限（`max-height: 250px`）
  - スナップショットURL修正（singular→plural）
  - app.py重複エンドポイント削除
- **既知の課題**
  - 電流値取得の安定性向上が必要（Modbusタイムアウト）

### v2.1 (2025-11-09)
- **モジュール化アーキテクチャ実装**
  - src/camera, src/gripper, src/webrtc モジュール作成
  - 統合アプリケーション（app.py）実装
- **パフォーマンス大幅改善**
  - Modbus通信最適化（同期的直接呼び出し）
  - グリッパーステータス取得: 40倍以上高速化（~0.14秒）
  - ポジションデータ取得: ~0.18秒
  - ポジション移動: ~0.22秒
- **バグ修正**
  - WebRTC RTCPeerConnection設定修正
  - カメラパラメータ取得のパース処理修正
  - ポジションテーブルデータマッピング修正
  - 高解像度時のカメラ映像停止問題修正
- **機能追加**
  - `/api/camera/status` エンドポイント追加
  - `/api/camera/resolutions` エンドポイント追加
- **ドキュメント整理**
  - README.md全面刷新
  - requirements.md更新
  - マイクロサービス関連ドキュメントをbackupへ移動

### v1.6 (2025-11-05)
- グリッパーステータス表示を右上に配置
- トーストメッセージ表示改善
- 非ブロッキンググリッパー制御実装

### v1.5 (2025-11-05)
- トースト表示時間延長と視認性向上

### v1.4 (2025-11-05)
- グリッパー操作の非ブロッキング化（カメラフリーズ解消）
- `asyncio.run_in_executor()`による並行実行

### v1.3 (2025-11-05)
- ポジションテーブル全パラメータ表示（横スクロール対応）
- カメラコントロールでbool/menu型対応
- チェックボックス・セレクトボックスUI追加

---

**開発状況**: � 安定版（v3.0 - SPLEBO-Nロボット制御統合）  
**最終更新**: 2026-01-07  
**Repository**: https://github.com/yamatetuto/AutomatedAssemblyRobot

## 最新の更新 (2025-11-12)

### グリッパー制御の改善
- **キャッシュ機能の実装**: 電流値と位置を200ms間隔でバックグラウンドタスクが自動更新
  - `get_current()`、`check_grip_status()`でキャッシュ優先使用
  - Modbus通信の重複読み取りを大幅削減
  - API応答速度の向上

- **安全機能の追加**: サーバー終了時にサーボ自動OFF
  - `disconnect()`で自動的にサーボ状態を確認
  - ONの場合は自動的にOFFにしてから切断

### カメラ制御の拡張
- **ユニバーサルv4l2サポート**: あらゆるカメラに対応
  - int, int64, bool, menu, button, bitmask型の全サポート
  - コントロールフラグの検証（inactive/disabled/grabbed）
  - 個別・一括リセット機能

### WebUI改善
- **電流値モニター**: リアルタイムグラフ表示
  - 500ms間隔で更新、60秒分の履歴表示
  - Y軸固定（0-500mA）、X軸相対時間表示

- **把持状態判定**: 3秒間隔で自動更新
  - サイレントモード（トースト通知なし）
  - LED + 詳細情報表示

### デバッグ機能
- **グリッパーREADME**: ターミナルからのデバッグ手順を追加
  - Pythonインタラクティブシェルでの操作方法
  - 各メソッドの実行例とトラブルシューティング

詳細は各サービスのREADME.mdを参照してください。
