# Gripper Module

IAI製電動グリッパー（RCP2-GRSS）のModbus RTU制御モジュール

## 概要

このモジュールは、IAI社の電動グリッパーをModbus RTU（RS-485）経由で制御するための機能を提供します。

### 主な機能

- **位置決め制御**: 64個のポジションテーブルによる高精度位置決め
- **把持状態判定**: 電流値、PSFL、MOVEビットによる多重判定
- **電流値モニタリング**: リアルタイム電流値取得
- **リトライ機構**: Modbus半二重通信の仕様に基づく自動リトライ（最大3回）
- **タイムアウト計算**: 通信速度とレスポンスサイズに応じた動的タイムアウト

## ファイル構成

```
src/gripper/
├── __init__.py           # モジュール初期化
├── controller.py         # 低レベルModbus RTU通信
├── gripper_manager.py    # 高レベルグリッパー管理
└── README.md            # このファイル
```

## 使用方法

### 基本的な使い方

```python
from src.gripper.gripper_manager import GripperManager

# 初期化
gripper = GripperManager()
await gripper.connect()

# サーボON
await gripper.servo_on()

# 原点復帰
await gripper.home()

# ポジション移動
await gripper.move_to_position(0)

# ステータス取得
status = await gripper.get_status()
print(f"位置: {status['position_mm']}mm")

# 電流値取得
current = await gripper.get_current()
print(f"電流: {current}mA")

# 把持状態判定
grip_status = await gripper.check_grip_status()
print(f"把持状態: {grip_status['status']}")

# 切断
await gripper.disconnect()
```

### ポジションテーブルの設定

```python
# ポジションデータ取得
data = await gripper.get_position_table(0)

# ポジションデータ設定
await gripper.update_position_table(0, {
    "position": 50.0,      # 位置 [mm]
    "width": 10.0,         # 幅 [mm]
    "speed": 100,          # 速度 [mm/s]
    "accel": 0.3,          # 加速度 [G]
    "decel": 0.3,          # 減速度 [G]
    "push_current": 30     # 押当電流 [%]
})
```

## Modbus RTU半二重通信の仕様

### タイムアウト計算

```
Tout = To + α + (10 × Bprt / Kbr) [ms]

To: 内部処理時間 × 安全率3
  - 読み出し: 4ms × 3 = 12ms
  - 書き込み: 18ms × 3 = 54ms
α: 従局トランスミッター活性化最小遅延時間（5ms）
Kbr: 通信速度 [kbps] （デフォルト: 38.4kbps）
Bprt: レスポンスメッセージのバイト数 + 8
```

### リトライ仕様

- **最大リトライ回数**: 3回
- **リトライ間隔**: 10ms
- **書き込み後待機**: 2ms（RCコントローラーが次のクエリー受信に備えるため）

### 通信の注意点

1. **排他制御**: `asyncio.Lock()`により同時アクセスを防止
2. **順次実行**: マスターはクエリー送信後、レスポンス受信まで待機
3. **エラーハンドリング**: タイムアウト後は自動的にリトライ

## Modbusレジスタマップ

| アドレス | 名称 | 説明 | アクセス |
|---------|------|------|---------|
| 0x9000 | PNOW | 現在位置（0.01mm単位） | 読み取り |
| 0x900C | CNOW | 現在電流値（mA） | 読み取り |
| 0x9005 | DSS1 | デバイスステータス1 | 読み取り |
| 0x9007 | DSSE | 拡張デバイスステータス | 読み取り |
| 0x9802 | SCON | サーボON/OFF | 書き込み |
| 0x9803 | HPOS | 原点復帰 | 書き込み |
| 0x9806 | TPOS | ポジション移動 | 書き込み |

### 重要なステータスビット

- **DSS1 (0x9005)**
  - bit 11: PSFL（押付け空振りフラグ）
  - bit 3: PEND（位置決め完了 - 使用非推奨）
  
- **DSSE (0x9007)**
  - bit 5: MOVE（移動中信号）

## 設定

環境変数で動作をカスタマイズできます:

```bash
export GRIPPER_PORT=/dev/ttyUSB0
export GRIPPER_BAUDRATE=38400
export GRIPPER_SLAVE_ADDR=1
```

## トラブルシューティング

### "No communication with the instrument"

**原因**: Modbusタイムアウト、通信競合

**対策**:
1. デバイス接続確認: `ls -l /dev/ttyUSB*`
2. 権限確認: `sudo usermod -a -G dialout $USER`
3. ボーレート確認（グリッパー本体設定と一致すること）
4. リトライログ確認

### 電流値が取得できない

**原因**: 通信タイミング、レジスタアドレス

**対策**:
1. サーボON状態を確認
2. ログでリトライ回数を確認
3. タイムアウト値を確認

### ポジション移動が失敗する

**原因**: サーボOFF、ポジションテーブル未設定

**対策**:
1. `servo_on()`を実行
2. ポジションテーブルデータを確認
3. アラーム状態を確認

## 技術仕様

- **通信方式**: Modbus RTU（RS-485）
- **デフォルトボーレート**: 38400 bps
- **データビット**: 8
- **パリティ**: なし
- **ストップビット**: 1
- **スレーブアドレス**: 1（変更可能）

## 開発者向け情報

### controller.py

低レベルのModbus RTU通信を担当:
- シリアルポート管理
- タイムアウト計算
- レジスタ読み書き

### gripper_manager.py

高レベルのグリッパー管理を担当:
- 非同期操作
- リトライロジック
- 排他制御
- エラーハンドリング

## 参考資料

- [IAI RCP2-GRSSマニュアル](docs/device_specifications.md)
- [Modbus RTU仕様](https://modbus.org/docs/Modbus_Application_Protocol_V1_1b3.pdf)
- [把持判定ロジック](docs/reports/gripper_current_and_grip_detection.md)

---

**最終更新**: 2025-11-10  
**バージョン**: v2.3
