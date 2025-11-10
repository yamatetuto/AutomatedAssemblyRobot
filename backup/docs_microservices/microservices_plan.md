# マイクロサービスアーキテクチャ移行計画

**作成日**: 2025-11-09  
**バージョン**: 1.0  

---

## 1. サービス分割方針

現在のモノリシックな構造を、ドメイン駆動設計（DDD）とマイクロサービスの原則に基づいて分割します。

### 分割原則
1. **単一責任の原則**: 各サービスは1つのビジネス機能を担当
2. **疎結合**: サービス間はREST APIで通信
3. **独立デプロイ**: 各サービスを個別に起動・停止可能
4. **独立スケーリング**: 負荷に応じて個別にスケール
5. **技術スタックの独立性**: 各サービスで最適な技術を選択可能

---

## 2. サービス一覧

### 2.1 Camera Service (カメラサービス)
- **責務**: カメラ映像のキャプチャ、ストリーミング、パラメータ制御
- **ポート**: 8001
- **API**:
  - `GET /stream` - WebRTCストリーミング
  - `POST /snapshot` - スナップショット撮影
  - `GET /snapshots` - スナップショット一覧
  - `GET /controls` - カメラコントロール一覧
  - `POST /control/{name}/{value}` - パラメータ設定
  - `POST /resolution` - 解像度変更
- **依存**: v4l2, OpenCV, aiortc
- **データ保存**: `./snapshots/`

### 2.2 Gripper Service (グリッパーサービス)
- **責務**: IAI電動グリッパーの制御、位置管理
- **ポート**: 8002
- **API**:
  - `POST /servo/{action}` - サーボON/OFF
  - `POST /home` - 原点復帰
  - `POST /move/{position}` - ポジション移動
  - `GET /status` - ステータス取得
  - `GET /positions` - 全ポジション設定取得
  - `POST /positions/{index}` - ポジション設定更新
- **依存**: minimalmodbus (Modbus RTU)
- **ハードウェア**: `/dev/ttyUSB0` @ 38400bps

### 2.3 Image Processing Service (画像処理サービス)
- **責務**: 物体検出、座標変換、キャリブレーション
- **ポート**: 8003
- **API**:
  - `POST /detect` - 物体検出
  - `POST /calibrate` - キャリブレーション
  - `POST /transform` - 座標変換
  - `GET /calibration/status` - キャリブレーション状態
- **依存**: OpenCV, NumPy, scikit-image
- **データ保存**: `./calibration/`

### 2.4 Printer Service (3Dプリンターサービス) ※将来実装
- **責務**: OctoPrint経由での3Dプリンター制御
- **ポート**: 8004
- **API**:
  - `POST /print` - プリント開始
  - `GET /status` - プリンター状態
  - `POST /pause` - 一時停止
  - `POST /cancel` - キャンセル
- **依存**: OctoPrint REST API
- **外部接続**: OctoPrint (通常 :5000)

### 2.5 Dispenser Service (ディスペンサーサービス) ※将来実装
- **責務**: GPIO経由でのディスペンサー制御
- **ポート**: 8005
- **API**:
  - `POST /dispense` - 吐出実行
  - `GET /status` - ステータス
  - `POST /configure` - パラメータ設定
- **依存**: RPi.GPIO
- **ハードウェア**: GPIO pins

### 2.6 Robot Service (ロボットアームサービス) ※将来実装
- **責務**: XYZ直交ロボットの制御
- **ポート**: 8006
- **API**:
  - `POST /move` - 座標移動
  - `POST /home` - 原点復帰
  - `GET /status` - 現在位置取得
- **依存**: 企業提供ライブラリ

### 2.7 Gateway Service (ゲートウェイサービス)
- **責務**: 統合Web UI、サービス間ルーティング、認証
- **ポート**: 8000
- **機能**:
  - すべてのサービスへのリバースプロキシ
  - Web UIの提供
  - APIゲートウェイ
  - CORS設定
- **依存**: FastAPI, httpx (HTTP client)

### 2.8 Sequence Service (シーケンスサービス) ※将来実装
- **責務**: 自動組立シーケンスの実行、ワークフロー管理
- **ポート**: 8007
- **API**:
  - `POST /sequence/start` - シーケンス開始
  - `POST /sequence/pause` - 一時停止
  - `GET /sequence/status` - 実行状態
  - `GET /sequences` - シーケンス一覧
  - `POST /sequence/upload` - シーケンス登録
- **依存**: 各種サービスAPI
- **データ保存**: `./sequences/`

---

## 3. ディレクトリ構造

```
AutomatedAssemblyRobot/
├── services/
│   ├── camera/                    # Camera Service
│   │   ├── README.md
│   │   ├── main.py
│   │   ├── requirements.txt
│   │   ├── config.yaml
│   │   ├── controller/
│   │   │   ├── __init__.py
│   │   │   ├── capture.py
│   │   │   ├── webrtc_streamer.py
│   │   │   └── processor.py
│   │   └── snapshots/             # ローカルストレージ
│   │
│   ├── gripper/                   # Gripper Service
│   │   ├── README.md
│   │   ├── main.py
│   │   ├── requirements.txt
│   │   ├── config.yaml
│   │   └── controller/
│   │       ├── __init__.py
│   │       └── modbus_controller.py
│   │
│   ├── image_processing/          # Image Processing Service
│   │   ├── README.md
│   │   ├── main.py
│   │   ├── requirements.txt
│   │   ├── config.yaml
│   │   ├── detector/
│   │   │   ├── __init__.py
│   │   │   ├── color_based.py
│   │   │   └── template_matching.py
│   │   ├── calibration/
│   │   │   ├── __init__.py
│   │   │   └── camera_calibrator.py
│   │   └── data/                  # キャリブレーションデータ
│   │
│   ├── gateway/                   # Gateway Service
│   │   ├── README.md
│   │   ├── main.py
│   │   ├── requirements.txt
│   │   ├── config.yaml
│   │   ├── templates/
│   │   │   └── index.html         # 統合Web UI
│   │   ├── static/
│   │   │   ├── css/
│   │   │   └── js/
│   │   └── middleware/
│   │       └── proxy.py
│   │
│   ├── printer/                   # Printer Service (将来)
│   ├── dispenser/                 # Dispenser Service (将来)
│   ├── robot/                     # Robot Service (将来)
│   └── sequence/                  # Sequence Service (将来)
│
├── shared/                        # 共通ライブラリ
│   ├── __init__.py
│   ├── config.py                  # 設定管理
│   ├── logger.py                  # ログ設定
│   └── schemas.py                 # Pydantic共通スキーマ
│
├── scripts/                       # 運用スクリプト
│   ├── start_all.sh              # 全サービス起動
│   ├── stop_all.sh               # 全サービス停止
│   ├── health_check.sh           # ヘルスチェック
│   └── deploy.sh                 # デプロイ
│
├── docker/                        # Docker設定 (将来)
│   ├── docker-compose.yml
│   └── Dockerfile.*
│
├── docs/
│   ├── architecture.md           # アーキテクチャ図
│   ├── api_reference.md          # API仕様書
│   └── deployment.md             # デプロイ手順
│
├── tests/                         # 統合テスト
│   ├── integration/
│   └── e2e/
│
├── README.md                      # プロジェクトREADME
└── requirements.txt               # ルート依存関係
```

---

## 4. サービス間通信

### 4.1 同期通信 (REST API)
- **プロトコル**: HTTP/HTTPS
- **形式**: JSON
- **クライアント**: httpx (非同期対応)

### 4.2 非同期通信 (将来拡張)
- **オプション1**: Redis Pub/Sub
- **オプション2**: MQTT
- **用途**: イベント駆動アーキテクチャ、リアルタイム通知

---

## 5. データ管理

### 5.1 各サービスのデータ
- **Camera Service**: スナップショット画像 (ローカルファイル)
- **Gripper Service**: ポジション設定 (Modbus HMI, メモリキャッシュ)
- **Image Processing Service**: キャリブレーションデータ (JSON/YAML)

### 5.2 共有データ (将来)
- **オプション**: PostgreSQL / MongoDB
- **用途**: シーケンス履歴、ログ、設定

---

## 6. 移行ステップ

### Phase 1: サービス分離 (Week 1-2)
1. Camera Serviceの切り出し
2. Gripper Serviceの切り出し
3. Gateway Serviceの作成
4. 各サービスのREADME作成

### Phase 2: 統合とテスト (Week 3)
1. サービス間通信の実装
2. 統合Web UIの移行
3. エンドツーエンドテスト

### Phase 3: 新機能追加 (Week 4-)
1. Image Processing Serviceの実装
2. Sequence Serviceの実装
3. その他サービスの追加

---

## 7. 技術スタック

### 共通
- **言語**: Python 3.9+
- **Webフレームワーク**: FastAPI
- **ASGIサーバー**: Uvicorn
- **HTTPクライアント**: httpx
- **設定管理**: pydantic-settings, PyYAML
- **ログ**: loguru

### サービス固有
- **Camera**: OpenCV, aiortc
- **Gripper**: minimalmodbus
- **Image Processing**: scikit-image, NumPy

---

## 8. 運用

### 起動
```bash
# 全サービス起動
./scripts/start_all.sh

# 個別起動
cd services/camera && python main.py
cd services/gripper && python main.py
```

### ヘルスチェック
```bash
./scripts/health_check.sh
```

### ログ
各サービスは `./logs/{service_name}.log` に出力

---

## 9. セキュリティ

### Phase 1 (現在)
- ローカルネットワークのみ
- 認証なし

### 将来拡張
- JWT認証
- HTTPS (Let's Encrypt)
- RBAC (役割ベースアクセス制御)

---

## 10. モニタリング (将来)

- **Prometheus**: メトリクス収集
- **Grafana**: ダッシュボード
- **Jaeger**: 分散トレーシング

