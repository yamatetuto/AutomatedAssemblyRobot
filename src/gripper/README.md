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

## デバッグ方法

### ターミナルから直接Modbusレジスタを確認する

#### 1. controller.pyを単体実行

```bash
cd /home/pi/assembly/AutomatedAssemblyRobot
python3 src/gripper/controller.py
```

デフォルトでは以下の動作を実行します:
- アラームコード確認
- ポジションテーブルNo.1のデータ読み出し

#### 2. カスタムデバッグスクリプトの作成

現在の電流値、位置、ステータスを確認:

```python
#!/usr/bin/env python3
from src.gripper.controller import CONController

PORT = '/dev/ttyUSB0'
SLAVE_ID = 1
BAUD = 38400

controller = CONController(PORT, SLAVE_ID, BAUD)

try:
    # 現在位置を取得
    position = controller.get_current_position()
    
    # 電流値を取得
    current = controller.get_current_mA()
    
    # アラームを確認
    alarm = controller.get_current_alarm()
    
    # サーボON状態を確認
    servo_on = controller.check_status_bit(
        controller.REG_DEVICE_STATUS,
        controller.BIT_SERVO_READY
    )
    
    # 移動中かどうかを確認
    moving = controller.check_status_bit(
        controller.REG_EXT_STATUS,
        controller.BIT_MOVE
    )
    
    # 押付け空振りフラグを確認
    psfl = controller.check_status_bit(
        controller.REG_DEVICE_STATUS,
        controller.BIT_PUSH_MISS
    )
    
    print("\n" + "=" * 60)
    print("グリッパーステータス")
    print("=" * 60)
    print(f"現在位置: {position} mm")
    print(f"電流値: {current} mA")
    print(f"アラーム: {alarm}")
    print(f"サーボON: {servo_on}")
    print(f"移動中: {moving}")
    print(f"押付け空振り: {psfl}")
    
finally:
    controller.close()
```

保存して実行:
```bash
python3 debug_gripper.py
```

#### 3. ポジションテーブルの内容を確認

```python
#!/usr/bin/env python3
from src.gripper.controller import CONController

controller = CONController('/dev/ttyUSB0', 1, 38400)

try:
    # ポジション0〜5のデータを確認
    for i in range(6):
        print(f"\n{'=' * 60}")
        print(f"ポジションNo.{i}")
        print('=' * 60)
        data = controller.get_position_data(i)
        
        if data:
            # 制御フラグをビット解析
            ctl_flag = int(data['control_flag_hex'], 16)
            print(f"\n制御フラグ解析 ({data['control_flag_hex']}):")
            print(f"  ビット1 (押付け有効): {(ctl_flag >> 1) & 1}")
            print(f"  ビット2 (押付け方向): {(ctl_flag >> 2) & 1}  # 0=プラス, 1=マイナス")
            
finally:
    controller.close()
```

#### 4. リアルタイムモニタリング

電流値と位置を連続監視:

```python
#!/usr/bin/env python3
import time
from src.gripper.controller import CONController

controller = CONController('/dev/ttyUSB0', 1, 38400)

try:
    print("リアルタイムモニター開始 (Ctrl+Cで終了)")
    print("時刻\t\t位置[mm]\t電流[mA]\t移動中")
    print("-" * 60)
    
    while True:
        pos = controller.get_current_position()
        current = controller.get_current_mA()
        moving = controller.check_status_bit(
            controller.REG_EXT_STATUS,
            controller.BIT_MOVE
        )
        
        timestamp = time.strftime("%H:%M:%S")
        print(f"{timestamp}\t{pos:.2f}\t\t{current}\t\t{moving}")
        
        time.sleep(0.5)  # 0.5秒間隔
        
except KeyboardInterrupt:
    print("\nモニター終了")
finally:
    controller.close()
```

#### 5. 押付け動作のデバッグ

押付け動作のデータ設定を確認:

```python
#!/usr/bin/env python3
from src.gripper.controller import CONController

controller = CONController('/dev/ttyUSB0', 1, 38400)

try:
    pos_no = 1
    
    print("設定前のデータ:")
    controller.get_position_data(pos_no)
    
    print("\n押付け動作用データを設定:")
    controller.set_position_data(
        position_number=pos_no,
        position_mm=2.0,           # 目標位置
        width_mm=0.5,              # 押付け幅
        speed_mm_s=5.0,            # 速度
        push_current_percent=50,   # 押付け電流
        push_direction=False       # False=プラス方向（閉じる）
    )
    
    print("\n設定後のデータ:")
    data = controller.get_position_data(pos_no)
    
    # ビット解析
    ctl_flag = int(data['control_flag_hex'], 16)
    print(f"\n制御フラグ詳細:")
    print(f"  Raw値: {data['control_flag_hex']} (10進数: {ctl_flag})")
    print(f"  2進数: {ctl_flag:04b}")
    print(f"  ビット1 (押付け有効): {(ctl_flag >> 1) & 1}")
    print(f"  ビット2 (押付け方向): {(ctl_flag >> 2) & 1}")
    
finally:
    controller.close()
```

### Python debugger (pdb) の使用

controller.pyのコードに以下を追加してブレークポイントを設定:

```python
import pdb
pdb.set_trace()  # ここで実行が停止
```

pdbコマンド:
- `n` (next): 次の行を実行
- `s` (step): 関数の中に入る
- `c` (continue): 次のブレークポイントまで実行
- `p 変数名`: 変数の値を表示
- `l` (list): 現在の位置のコードを表示
- `q` (quit): デバッガーを終了

例:
```python
def get_current_mA(self):
    import pdb; pdb.set_trace()  # デバッグ開始
    current_raw = self.instrument.read_long(...)
    print(f"電流値: {current_raw}")
    return current_raw
```

実行すると:
```bash
> /home/pi/.../controller.py(292)get_current_mA()
-> current_raw = self.instrument.read_long(...)
(Pdb) n  # 次の行へ
(Pdb) p current_raw  # 変数の値を表示
150
(Pdb) c  # 続行
```

### minimalmodbusのデバッグモード

controller.pyで詳細なModbus通信ログを有効化:

```python
def __init__(self, port, slave_address, baudrate):
    # ...
    self.instrument.debug = True  # ← コメントを外す
```

これにより、送受信される生のModbusフレームが表示されます。

### 通信エラーの診断

```bash
# シリアルポートの確認
ls -l /dev/ttyUSB*

# 権限の確認
groups  # dialoutグループに所属しているか確認

# グループに追加（必要な場合）
sudo usermod -a -G dialout $USER
# ログアウト/ログインが必要

# Modbusツールで通信テスト
sudo apt-get install python3-serial
python3 -m serial.tools.miniterm /dev/ttyUSB0 38400
```
