# 🤖 AutomatedAssemblyRobot

積層型3Dプリンター、ディスペンサー、XYZ直交ロボットを組み合わせた医療機器の自動組立システム

---

## 📋 プロジェクト概要

本プロジェクトは、以下のデバイスを統合制御し、医療機器の自動組立を実現するシステムです:

- **3Dプリンター** (Tronxy GEMINI S) - OctoPrint経由で制御
- **XYZ直交ロボット** (株式会社コスモスウェブ製) - 企業ライブラリで制御
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

### 🚧 実装中
- [ ] 電流値取得の安定化（Modbusタイムアウト対策）
- [ ] 3Dプリンター制御 (OctoPrint API)
- [ ] ディスペンサー制御 (GPIO)
- [ ] 画像処理・物体検出
- [ ] ロボットアーム統合
- [ ] 自動組立シーケンス

---

## 🏗️ ディレクトリ構造

```
AutomatedAssemblyRobot/
├── app.py                     # 統合アプリケーション（メイン）
├── src/                       # モジュール化されたソースコード
│   ├── camera/               # カメラ管理モジュール
│   │   ├── __init__.py
│   │   └── camera_manager.py
│   ├── gripper/              # グリッパー管理モジュール
│   │   ├── __init__.py
│   │   ├── gripper_manager.py  # Modbusロック機構実装
│   │   └── controller.py       # CONController (Modbus RTU)
│   ├── webrtc/               # WebRTC管理モジュール
│   │   ├── __init__.py
│   │   └── webrtc_manager.py
│   └── config/               # 設定管理モジュール
│       ├── __init__.py
│       └── settings.py
├── web_app/                   # Webアプリケーション
│   ├── static/               # 静的ファイル
│   │   ├── css/             # スタイルシート
│   │   │   └── style.css    # メインCSS
│   │   └── js/              # JavaScript
│   │       └── app.js       # UIロジック（電流値グラフ、把持判定等）
│   └── templates/            # HTMLテンプレート
│       └── index_webrtc_fixed.html
├── snapshots/                 # スナップショット保存先
├── docs/                      # ドキュメント
│   ├── reports/              # 調査レポート
│   ├── requirements.md       # 要件定義
│   ├── schema.md             # データ構造定義
│   └── device_specifications.md
├── backup/                    # バックアップ
│   ├── old_code/             # 旧コード
│   ├── services_backup/      # 旧マイクロサービス実装
│   └── docs_microservices/   # マイクロサービス設計ドキュメント
├── requirements.txt           # Python依存パッケージ
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
sudo apt install -y git python3-pip python3-opencv v4l-utils
```

### 2. リポジトリのクローン
```bash
cd ~
git clone https://github.com/yamatetuto/AutomatedAssemblyRobot.git
cd AutomatedAssemblyRobot
```

### 3. Python依存パッケージのインストール
```bash
# システムワイドインストール（推奨）
pip3 install --break-system-packages fastapi uvicorn minimalmodbus aiortc jinja2 python-multipart av

# または仮想環境を使用
python3 -m venv venv
source venv/bin/activate
pip3 install fastapi uvicorn minimalmodbus aiortc jinja2 python-multipart av
```

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

**開発状況**: 🟡 ベータ版（v2.2 - 一部機能調整中）  
**最終更新**: 2025-11-09  
**Repository**: https://github.com/yamatetuto/AutomatedAssemblyRobot
