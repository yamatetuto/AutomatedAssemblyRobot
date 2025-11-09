# 🤖 AutomatedAssemblyRobot (Microservices Architecture)

積層型3Dプリンター、ディスペンサー、XYZ直交ロボットを組み合わせた医療機器の自動組立システム  
**マイクロサービスアーキテクチャ版**

---

## 📋 プロジェクト概要

本プロジェクトは、以下のデバイスを統合制御し、医療機器の自動組立を実現するシステムです:

- **3Dプリンター** (Tronxy GEMINI S) - OctoPrint経由で制御 ※将来実装
- **XYZ直交ロボット** (株式会社コスモスウェブ製) - 企業ライブラリで制御 ※将来実装
- **電動グリッパー** (IAI社 RCP2-GRSS) - Modbus RTU通信 ✅実装済み
- **ディスペンサー** - Raspberry Pi GPIO制御 ※将来実装
- **カメラ** - OpenCV + WebRTC ✅実装済み

---

## 🏗️ アーキテクチャ

### マイクロサービス構成

```
┌─────────────────────────────────────────────────────────┐
│                  Gateway Service (8000)                 │
│          Web UI + API Gateway + Reverse Proxy           │
└────────────────┬────────────────┬───────────────────────┘
                 │                │
      ┌──────────┴────────┐   ┌───┴─────────────┐
      │ Camera Service    │   │ Gripper Service │
      │    (8001)         │   │     (8002)      │
      │                   │   │                 │
      │ - WebRTC Stream   │   │ - Modbus RTU    │
      │ - Snapshots       │   │ - Position Ctrl │
      │ - v4l2 Controls   │   │ - Status Monitor│
      └───────────────────┘   └─────────────────┘
```

### サービス一覧

| サービス | ポート | 責務 | 状態 |
|---------|--------|------|------|
| **Gateway** | 8000 | Web UI, APIゲートウェイ | ✅ 実装済み |
| **Camera** | 8001 | カメラストリーミング、スナップショット | ✅ 実装済み |
| **Gripper** | 8002 | グリッパー制御、ポジション管理 | ✅ 実装済み |
| Image Processing | 8003 | 物体検出、キャリブレーション | 🚧 未実装 |
| Printer | 8004 | 3Dプリンター制御 | 🚧 未実装 |
| Dispenser | 8005 | ディスペンサー制御 | 🚧 未実装 |
| Robot | 8006 | ロボットアーム制御 | 🚧 未実装 |
| Sequence | 8007 | 自動組立シーケンス | 🚧 未実装 |

---

## 🚀 クイックスタート

### 1. 依存パッケージのインストール

```bash
# システムパッケージ
sudo apt update
sudo apt install -y python3-pip v4l-utils

# Pythonパッケージ（各サービス）
pip3 install --break-system-packages -r requirements.txt
```

### 2. 全サービス起動

```bash
./scripts/start_all.sh
```

### 3. Web UIにアクセス

ブラウザで `http://localhost:8000` を開く

### 4. ヘルスチェック

```bash
./scripts/health_check.sh
```

### 5. 停止

```bash
./scripts/stop_all.sh
```

---

## 📁 ディレクトリ構造

```
AutomatedAssemblyRobot/
├── services/                   # マイクロサービス
│   ├── camera/                 # Camera Service (port 8001)
│   │   ├── main.py
│   │   ├── config.yaml
│   │   ├── requirements.txt
│   │   ├── README.md
│   │   ├── controller/
│   │   └── snapshots/
│   ├── gripper/                # Gripper Service (port 8002)
│   │   ├── main.py
│   │   ├── config.yaml
│   │   ├── requirements.txt
│   │   ├── README.md
│   │   └── controller/
│   └── gateway/                # Gateway Service (port 8000)
│       ├── main.py
│       ├── config.yaml
│       ├── requirements.txt
│       ├── README.md
│       ├── templates/
│       ├── static/
│       └── middleware/
│
├── shared/                     # 共通ライブラリ
│   ├── config.py               # 設定管理
│   ├── logger.py               # ログ設定
│   └── schemas.py              # Pydanticスキーマ
│
├── scripts/                    # 運用スクリプト
│   ├── start_all.sh            # 全サービス起動
│   ├── stop_all.sh             # 全サービス停止
│   └── health_check.sh         # ヘルスチェック
│
├── docs/                       # ドキュメント
│   ├── microservices_plan.md  # アーキテクチャ設計書
│   ├── requirements.md         # 要件定義
│   └── schema.md               # データスキーマ
│
├── logs/                       # ログファイル
├── snapshots/                  # スナップショット
└── README.md                   # このファイル
```

---

## 🎯 各サービスの詳細

### Gateway Service (port 8000)

**役割**: 統合Web UI、APIゲートウェイ、リバースプロキシ

- すべてのバックエンドサービスへのプロキシ
- `/api/camera/*` → Camera Service
- `/api/gripper/*` → Gripper Service

**詳細**: [services/gateway/README.md](services/gateway/README.md)

### Camera Service (port 8001)

**役割**: カメラ映像のキャプチャとストリーミング

- WebRTCによる低遅延ストリーミング
- スナップショット撮影・管理
- カメラパラメータ制御（明るさ、コントラスト、フォーカスなど）

**詳細**: [services/camera/README.md](services/camera/README.md)

### Gripper Service (port 8002)

**役割**: IAI電動グリッパーの制御

- Modbus RTU通信
- サーボON/OFF、原点復帰
- 64ポジション位置決め
- ポジションテーブル管理

**詳細**: [services/gripper/README.md](services/gripper/README.md)

---

## ⚙️ 設定

各サービスは `config.yaml` で設定可能:

```yaml
service:
  name: <service_name>
  host: "0.0.0.0"
  port: <port_number>

logging:
  level: "INFO"
  directory: "../../logs"
```

環境変数による上書きも可能:

```bash
export SERVICE_PORT=8000
export LOGGING_LEVEL=DEBUG
```

---

## 🔧 開発

### 個別サービスの起動

```bash
# Camera Service
cd services/camera
python3 main.py

# Gripper Service
cd services/gripper
python3 main.py

# Gateway Service
cd services/gateway
python3 main.py
```

### ログの確認

```bash
tail -f logs/camera_service.log
tail -f logs/gripper_service.log
tail -f logs/gateway_service.log
```

---

## 📚 ドキュメント

- [マイクロサービス移行計画](docs/microservices_plan.md)
- [要件定義書](docs/requirements.md)
- [データスキーマ](docs/schema.md)
- [Camera Service README](services/camera/README.md)
- [Gripper Service README](services/gripper/README.md)
- [Gateway Service README](services/gateway/README.md)

---

## 🐛 トラブルシューティング

### サービスが起動しない

```bash
# ログを確認
cat logs/camera_service.log
cat logs/gripper_service.log
cat logs/gateway_service.log

# ポートが使用中か確認
sudo netstat -tulpn | grep -E '8000|8001|8002'
```

### デバイスに接続できない

```bash
# カメラ
v4l2-ctl --list-devices
sudo usermod -a -G video $USER

# グリッパー
ls -l /dev/ttyUSB*
sudo usermod -a -G dialout $USER
```

---

## 🤝 コントリビューション

セマンティックコミットを使用:

- `feat:` 新機能
- `fix:` バグ修正
- `docs:` ドキュメント
- `refactor:` リファクタリング
- `test:` テスト

---

## 📝 更新履歴

### v2.0.0 (2025-11-09) - Microservices Architecture
- ✨ マイクロサービスアーキテクチャに移行
- 🎯 3つのサービスを実装（Gateway, Camera, Gripper）
- 🔧 共通ライブラリ（shared/）を追加
- 📜 運用スクリプトを追加（start/stop/health_check）
- 📚 各サービスにREADMEを追加

### v1.6 (2025-11-05) - Monolithic版
- グリッパーステータス表示改善
- 非ブロッキング制御実装

---

**開発状況**: 🟢 Phase 1完了（Camera/Gripper統合）  
**次のステップ**: Image Processing Service実装  
**最終更新**: 2025-11-09  
**Repository**: https://github.com/yamatetuto/AutomatedAssemblyRobot
