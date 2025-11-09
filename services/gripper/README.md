# Gripper Service

IAI電動グリッパー(RCP2-GRSS)の制御を提供するマイクロサービス

---

## 📋 サービス概要

**ポート**: 8002  
**責務**: Modbus RTU経由でのグリッパー制御、位置決め、ポジションテーブル管理

### 主要機能
- ✅ サーボON/OFF制御
- ✅ 原点復帰
- ✅ 64ポジションへの位置決め
- ✅ ポジションテーブル管理（位置、幅、速度、加減速度、押当電流）
- ✅ ステータスモニタリング

---

## 🚀 使用方法

### 起動

```bash
cd services/gripper
python main.py
```

### 動作確認

```bash
# ヘルスチェック
curl http://localhost:8002/health

# ステータス取得
curl http://localhost:8002/status
```

---

## 📡 API仕様

### ヘルスチェック
```
GET /health
```

### サーボON/OFF
```
POST /servo/{action}

例: POST /servo/on
例: POST /servo/off
```

### 原点復帰
```
POST /home
```

### ポジション移動
```
POST /move/{position}

例: POST /move/5
```

### ステータス取得
```
GET /status
```

**レスポンス**:
```json
{
  "position_mm": 50.0,
  "servo_on": true,
  "alarm": 0,
  "warn": 0,
  "current_position_number": 5
}
```

### 全ポジション設定取得
```
GET /positions
```

### ポジション設定更新
```
POST /positions/{index}
Content-Type: application/json

{
  "position": 50.0,
  "width": 30.0,
  "speed": 50,
  "accel": 50,
  "decel": 50,
  "push_current": 50
}
```

---

## ⚙️ 設定

### config.yaml

```yaml
service:
  name: gripper
  version: "1.0.0"
  host: "0.0.0.0"
  port: 8002

gripper:
  port: "/dev/ttyUSB0"
  slave_address: 1
  baudrate: 38400
  timeout: 1.0

logging:
  level: "INFO"
  directory: "../../logs"
```

---

## �� 依存関係

### 必須パッケージ

- `fastapi>=0.100.0`
- `uvicorn>=0.23.0`
- `minimalmodbus>=2.0.0`
- `pyserial>=3.5`

### ハードウェア

- IAI RCP2-GRSSグリッパー
- USB-RS485変換アダプタ

### インストール

```bash
pip3 install -r requirements.txt
sudo usermod -a -G dialout $USER
# ログアウト・ログインが必要
```

---

## 🔧 トラブルシューティング

### 通信エラー

```bash
# デバイス確認
ls -l /dev/ttyUSB*

# 権限確認
sudo usermod -a -G dialout $USER
```

### ボーレート不一致

グリッパー本体の設定を確認してください（デフォルト: 38400bps）

---

## 🔗 関連サービス

- **Gateway Service** (port 8000) - このサービスへのリバースプロキシ

---

## 📝 更新履歴

### v1.0.0 (2025-11-09)
- 初版リリース
- Modbus RTU通信実装
- ポジションテーブル管理実装

---

**メンテナンス**: アクティブ  
**ステータス**: 🟢 本番利用可能
