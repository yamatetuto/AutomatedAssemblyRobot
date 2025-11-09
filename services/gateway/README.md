# Gateway Service

統合Web UIとAPIゲートウェイを提供するマイクロサービス

---

## 📋 サービス概要

**ポート**: 8000  
**責務**: すべてのバックエンドサービスへのリバースプロキシ、Web UIホスティング

### 主要機能
- ✅ 統合Web UI（カメラ＋グリッパー制御）
- ✅ APIゲートウェイ（リバースプロキシ）
- ✅ ヘルスチェック集約
- ✅ CORS対応

---

## 🚀 使用方法

### 起動

```bash
cd services/gateway
python main.py
```

### アクセス

ブラウザで `http://localhost:8000` を開く

---

## 📡 API仕様

### ヘルスチェック
```
GET /health
```

### Camera Service Proxy
```
GET/POST /api/camera/{path}

例: GET /api/camera/snapshots
例: POST /api/camera/snapshot
```

### Gripper Service Proxy
```
GET/POST /api/gripper/{path}

例: GET /api/gripper/status
例: POST /api/gripper/servo/on
```

---

## ⚙️ 設定

### config.yaml

```yaml
service:
  name: gateway
  version: "1.0.0"
  host: "0.0.0.0"
  port: 8000

services:
  camera:
    url: "http://localhost:8001"
    prefix: "/api/camera"
  gripper:
    url: "http://localhost:8002"
    prefix: "/api/gripper"

logging:
  level: "INFO"
  directory: "../../logs"
```

---

## 📦 依存関係

### 必須パッケージ

- `fastapi>=0.100.0`
- `uvicorn>=0.23.0`
- `httpx>=0.25.0` - 非同期HTTPクライアント
- `jinja2>=3.1.2` - テンプレートエンジン

### バックエンドサービス

- Camera Service (port 8001)
- Gripper Service (port 8002)

---

## 🔧 トラブルシューティング

### バックエンドサービスに接続できない

各サービスが起動しているか確認:

```bash
curl http://localhost:8001/health
curl http://localhost:8002/health
```

### Web UIが表示されない

- テンプレートファイルが存在するか確認: `templates/index.html`
- ログを確認: `../../logs/gateway.log`

---

## 📝 更新履歴

### v1.0.0 (2025-11-09)
- 初版リリース
- APIゲートウェイ実装
- 統合Web UI実装

---

**メンテナンス**: アクティブ  
**ステータス**: 🟢 本番利用可能
