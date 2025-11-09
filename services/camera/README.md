# Camera Service

カメラ映像のキャプチャ、WebRTCストリーミング、スナップショット管理を提供するマイクロサービス

---

## 📋 サービス概要

**ポート**: 8001  
**責務**: USBカメラからの映像取得、WebRTC配信、パラメータ制御、スナップショット撮影

### 主要機能
- ✅ WebRTCによる低遅延ストリーミング
- ✅ スナップショット撮影と管理
- ✅ カメラパラメータ調整（明るさ、コントラスト、フォーカスなど）
- ✅ 複数解像度対応
- ✅ 自動パラメータリセット（終了時）

---

## 🚀 使用方法

### 起動

```bash
cd services/camera
python main.py
```

または全サービス一括起動:

```bash
# プロジェクトルートから
./scripts/start_all.sh
```

### 動作確認

```bash
# ヘルスチェック
curl http://localhost:8001/health

# スナップショット一覧
curl http://localhost:8001/snapshots
```

---

## 📡 API仕様

### ヘルスチェック
```
GET /health
```

**レスポンス**:
```json
{
  "service": "camera",
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2025-11-09T12:34:56"
}
```

### WebRTC接続

```
POST /offer
Content-Type: application/json

{
  "sdp": "v=0...",
  "type": "offer"
}
```

**レスポンス**:
```json
{
  "sdp": "v=0...",
  "type": "answer"
}
```

### スナップショット撮影

```
POST /snapshot
```

**レスポンス**:
```json
{
  "filename": "snapshot_20251109_123456.jpg",
  "timestamp": "20251109_123456",
  "url": "/snapshots/snapshot_20251109_123456.jpg"
}
```

### スナップショット一覧取得

```
GET /snapshots
```

**レスポンス**:
```json
[
  {
    "filename": "snapshot_20251109_123456.jpg",
    "timestamp": "20251109_123456",
    "url": "/snapshots/snapshot_20251109_123456.jpg"
  }
]
```

### スナップショット取得

```
GET /snapshots/{filename}
```

### カメラコントロール一覧

```
GET /controls
```

### カメラパラメータ設定

```
POST /control/{name}/{value}

例: POST /control/brightness/200
```

### 解像度変更

```
POST /resolution?width=1280&height=720&fps=30
```

---

## ⚙️ 設定

### config.yaml

```yaml
service:
  name: camera
  version: "1.0.0"
  host: "0.0.0.0"
  port: 8001

camera:
  device: 0  # /dev/video0
  width: 640
  height: 480
  fps: 30
  codec: "MJPEG"

snapshots:
  directory: "./snapshots"
  max_snapshots: 100

logging:
  level: "INFO"
  directory: "../../logs"
```

### 環境変数

設定はYAMLファイルより環境変数が優先されます:

```bash
export CAMERA_DEVICE=0
export CAMERA_WIDTH=1280
export CAMERA_HEIGHT=720
export SERVICE_PORT=8001
```

---

## 📦 依存関係

### 必須パッケージ

- `fastapi>=0.100.0` - Webフレームワーク
- `uvicorn>=0.23.0` - ASGIサーバー
- `opencv-python>=4.6.0` - カメラキャプチャ
- `aiortc>=1.6.0` - WebRTC
- `av>=10.0.0` - 動画処理
- `pyyaml>=6.0` - 設定ファイル
- `pydantic>=2.0.0` - データバリデーション

### システム依存

- `v4l-utils` - カメラパラメータ制御
- USBカメラ（UVC対応）

### インストール

```bash
pip3 install -r requirements.txt
sudo apt install v4l-utils
```

---

## 🔧 トラブルシューティング

### カメラが開けない

```bash
# デバイス確認
v4l2-ctl --list-devices
ls -l /dev/video*

# 権限確認
sudo usermod -a -G video $USER
# ログアウト・ログインが必要
```

### WebRTC接続エラー

- ファイアウォール設定を確認
- HTTPS環境でないとWebRTCが動作しない場合があります（ローカルネットワークは除く）

### パフォーマンス問題

- 解像度を下げる（640x480推奨）
- コーデックをMJPEGに変更
- FPSを下げる（15-30fps）

---

## 📁 ディレクトリ構造

```
services/camera/
├── main.py              # メインアプリケーション
├── config.yaml          # 設定ファイル
├── requirements.txt     # 依存パッケージ
├── README.md            # このファイル
├── controller/          # コントローラモジュール（将来拡張）
└── snapshots/           # スナップショット保存先
```

---

## 🔗 関連サービス

- **Gateway Service** (port 8000) - このサービスへのリバースプロキシ
- **Image Processing Service** (port 8003) - 撮影画像の解析

---

## 📝 更新履歴

### v1.0.0 (2025-11-09)
- 初版リリース
- WebRTCストリーミング実装
- スナップショット機能実装
- カメラパラメータ制御実装

---

**メンテナンス**: アクティブ  
**ステータス**: 🟢 本番利用可能
