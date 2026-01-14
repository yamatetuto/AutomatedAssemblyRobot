# SPLEBO-N TEACHINGフォルダ コード解説

このフォルダは**SPLEBO-N**というテーブルロボット（産業用自動化装置）のティーチング（教示）システムです。Raspberry Piをベースとした制御システムで、ネジ締め作業などを自動化するためのソフトウェアです。

---

## 📁 ファイル構成と役割

| ファイル | 役割 |
|---------|------|
| `splebo_n.py` | メインライブラリ。ロボット制御の中核クラス |
| `can.py` | CANバス通信制御（MCP2515チップ経由） |
| `constant.py` | 定数定義（ビットマスク、7セグLED表示値など） |
| `file_ctrl.py` | ファイル操作（位置データ、プロジェクト設定の読み書き） |
| `sample.py` | サンプルプログラム（ネジ締め作業のステートマシン） |
| `setting.xml` | 速度設定などの設定ファイル |
| `SPLEBO-N.pos` | ポイント（位置座標）データファイル |
| `SPLEBO-N.sys` | システムパラメータ（軸設定）ファイル |

---

## 🔧 can.py - CAN通信制御

**MCP2515** CANコントローラをSPI経由で制御するモジュールです。

### 主な機能
- MCP2515の初期化・リセット
- CANメッセージの送受信
- I/Oエキスパンダとの通信

### 主要クラス

#### `can_data_st`
CANメッセージデータ構造体
```python
class can_data_st:
    kMAXCHAR_ONEMESSAGE = 8  # 1回の送信最大文字数
    id = 0                    # CAN ID
    eid_en = False            # 拡張ID有効フラグ
    bnum = 0                  # バッファ番号
    data = bytearray(8)       # データ配列
    len = 0                   # データ長
```

#### `can_ctrl_class`
CAN制御クラスの主要メソッド

| メソッド | 説明 |
|---------|------|
| `initialize_can()` | CAN初期化（500kbps設定） |
| `reset_mcp2515()` | MCP2515リセット |
| `send_can_data()` | データ送信 |
| `input(boardId, portNo)` | デジタル入力読み取り |
| `output(boardId, portNo, onoff)` | デジタル出力制御 |
| `canio_thread_proc()` | バックグラウンドI/O更新スレッド |
| `start_canio_thread()` | I/Oスレッド開始 |
| `stop_canio_thread()` | I/Oスレッド停止 |

### MCP2515コマンド定数
```python
kMCP2515_CMD_RESET = 0xC0    # リセット
kMCP2515_CMD_READ = 0x03     # レジスタ読み込み
kMCP2515_CMD_WRITE = 0x02    # レジスタ書き込み
kMCP2515_CMD_RTS = 0x80      # 送信要求
kMCP2515_CMD_STATUS = 0xA0   # ステータス読み込み
```

---

## 📐 constant.py - 定数定義

### Bitクラス
ビットマスク定数
```python
class Bit:
    BitOn0 = 0x01   # ビット0 ON
    BitOn1 = 0x02   # ビット1 ON
    # ... BitOn7 まで
    BitOff0 = 0xFE  # ビット0 OFF（反転マスク）
    BitOff1 = 0xFD  # ビット1 OFF
    # ... BitOff7 まで
```

### DEFSwStatクラス
スイッチ状態定義
```python
class DEFSwStat:
    LEFTSW = 21
    RIGHTSW = 22
    StartSw1ON = 0x20
    StartSw2ON = 0x40
    StartSw1Sw2ON = 0x60
```

### Led7SegClassクラス
7セグメントLED表示パターン

| 定数 | 値 | 表示 |
|-----|-----|-----|
| LED_0 | 0x3F | 0 |
| LED_1 | 0x06 | 1 |
| ... | ... | ... |
| LED_A | 0x77 | A |
| LED_E | 0x79 | E |
| LED_R | 0x50 | r |

#### 定型表示パターン
```python
SEG_ORG = [LED_O, LED_R, LED_G]      # "ORG" - 原点
SEG_STB = [LED_S, LED_T, LED_B]      # "STB" - スタンバイ
SEG_RUN = [LED_R, LED_U, LED_N]      # "RUN" - 運転中
SEG_RDY = [LED_R, LED_D, LED_Y]      # "RDY" - 準備完了
SEG_END = [LED_E, LED_N, LED_D]      # "END" - 終了
SEG_ERR = [LED_E, LED_R, LED_R]      # "ERR" - エラー
SEG_EMG = [LED_E, LED_M, LED_G]      # "EMG" - 非常停止
SEG_PRG = [LED_P, LED_R, LED_G]      # "PRG" - プログラム
```

#### ユーティリティメソッド
```python
@staticmethod
def get_led_value(num: int):
    """数字(0-9)を7セグ表示値に変換"""
    
@staticmethod
def get_led_list(num: int, prog: bool):
    """2桁数値を3桁7セグ配列に変換（P01形式など）"""
```

---

## 📂 file_ctrl.py - ファイル管理

位置データとシステム設定の永続化を担当

### PositionFileClass
SPLEBO-N.posファイル管理

#### 主要メソッド
| メソッド | 説明 |
|---------|------|
| `create_position_file()` | 位置ファイル作成 |
| `read_position_file()` | 位置ファイル読み込み |
| `update_pos()` | ポイント更新 |
| `add_point()` | ポイント追加 |
| `delete_point()` | ポイント削除 |
| `copy_point()` | ポイントコピー |
| `modify_point()` | ポイント番号変更 |

#### ポイントデータ形式
```
Item番号=ポイント番号,座標タイプ,X,Y,Z,U,S1,S2,A,B,保護フラグ,コメント
```

### ProjectFileClass
SPLEBO-N.sysファイル管理

#### 管理するパラメータ
- MaxSpeed: 各軸の最大速度
- MaxAccel: 各軸の加速度
- MaxDecel: 各軸の減速度
- StartSpeed: 開始速度
- OffsetSpeed: オフセット速度
- OriginSpeed: 原点復帰速度
- OriginOffset: 原点オフセット
- LimitPlus: 正方向ソフトリミット
- LimitMinus: 負方向ソフトリミット
- PulseLength: パルス長
- OriginOrder: 原点復帰順序
- OriginDir: 原点復帰方向
- OriginSensor: 原点センサー
- InPosition: インポジション
- MotorType: モータータイプ

---

## 🤖 splebo_n.py - メインライブラリ

2246行の大規模なメインモジュール。ロボット全体を統括します。

### 主要クラス一覧

| クラス | 説明 |
|--------|------|
| `NOVA_Class` | モーションコントローラのレジスタ定義 |
| `gpio_class` | Raspberry Pi GPIOピン定義 |
| `axis_type_class` | 軸定義（X,Y,Z,U,S1,S2,A,B の8軸） |
| `axis_setting_class` | 軸パラメータ（速度、加速度、リミットなど） |
| `axis_status_class` | 軸状態（座標、アラーム、原点復帰状態など） |
| `homing_class` | 原点復帰シーケンス管理 |
| `axis_move_type_class` | 移動タイプ（相対/絶対/JOG） |
| `motion_controller_cmd_class` | モーションコントローラコマンド |
| `splebo_n_class` | メインクラス |

### gpio_class - GPIOピン定義
```python
class gpio_class:
    kNova_reset_pin = 14   # NOVAリセットピン
    kNova_Power_pin = 12   # NOVA電源ピン
    kCan_CS_pin = 8        # CAN CSピン
    kEmergencyBtn = 15     # 非常停止ボタン
```

### axis_type_class - 軸定義
```python
class axis_type_class:
    axis_ALL = -1  # 全軸
    axis_X = 0     # X軸
    axis_Y = 1     # Y軸
    axis_Z = 2     # Z軸
    axis_U = 3     # U軸（回転）
    axis_S1 = 4    # S1軸（補助1）
    axis_S2 = 5    # S2軸（補助2）
    axis_A = 6     # A軸
    axis_B = 7     # B軸
    axis_count = 8 # 総軸数
```

### axis_maker_Class - モータータイプ
```python
class axis_maker_Class:
    kNone = 0      # なし
    kIAI = 2       # IAI電動アクチュエータ
    kStepping = 4  # ステッピングモーター
    kaSTEP = 5     # オリエンタルモーター aSTEP
```

### splebo_n_class - メインクラス

#### 主要メソッド
```python
# 初期化・終了
init()                         # 初期化
close()                        # 終了処理
param_init()                   # パラメータ初期化
motion_init()                  # モーション制御初期化

# モーション制御
motion_movePoint(axisbit, pointNo, speedRate)  # ポイント番号へ移動
motion_movePoint_start(axisbit, pointNo, speedRate)  # 移動開始
motion_move_start(axis, targetPos, speedRate)  # 軸移動開始
motion_wait_move_end_All()     # 移動完了待ち

# I/O制御
io_ex_input(portNo)            # 入力読み取り
io_ex_output(portNo, onoff)    # 出力制御

# 表示制御
Disp7SegLine1(segData)         # 7セグ1行目表示
Disp7SegLine2(segData)         # 7セグ2行目表示

# ファイル操作
read_position_file()           # 位置ファイル読み込み
read_syspara_file()            # システムパラメータ読み込み
```

### homing_class - 原点復帰シーケンス
```python
class homing_class:
    kHomeMoveStart = 0      # 原点移動開始
    kHomeMoveCheck = 1      # 原点移動確認
    kNovaHomeMoveStart = 2  # NOVA原点移動開始
    kNovaHomeMoveCheck = 3  # NOVA原点移動確認
    kOriginSensorCheck = 4  # 原点センサー確認
    kOffsetMoveStart = 5    # オフセット移動開始
    kOffsetMoveCheck = 6    # オフセット移動確認
    kParameterSet = 7       # パラメータ設定
    kEnd = 8                # 終了
```

---

## 🔩 sample.py - サンプルアプリケーション

ネジ締め自動化システムのステートマシン実装

### 軸指定ビット定義
```python
DEF_axX = 1      # X軸のみ
DEF_axY = 2      # Y軸のみ
DEF_axXY = 3     # X+Y軸
DEF_axZ = 4      # Z軸のみ
DEF_axXZ = 5     # X+Z軸
DEF_axYZ = 6     # Y+Z軸
DEF_axXYZ = 7    # X+Y+Z軸
```

### EnumLoopState - メインループ状態
```python
class EnumLoopState(Enum):
    HomeInit = 0      # 原点復帰初期化
    HomeWait = 1      # 原点復帰待機
    Homing = 2        # 原点復帰中
    SelectInit = 3    # 選択初期化
    SelectLoop = 4    # 選択待ち
    StartWait = 5     # Start待ち
    ScrewPickup = 6   # ねじ取り
    ScrewTight = 7    # ねじ締め
    MoveStartPos = 8  # スタート位置移動
    WorkPickCheck = 9 # ワーク取り出し
    Error = 10        # エラー
    Reset = 11        # リセット
```

### EnumScrewPickupState - ネジ取りシーケンス
```python
class EnumScrewPickupState(Enum):
    ScrewPickupUpper = 1    # ねじ取り上空
    ScrewNonCheck = 2       # ネジ無しチェック
    FeederScrewCheck = 3    # フィーダーネジチェック
    GuideOpenCheck = 4      # ガイドオープン確認
    RotateCheck = 5         # 回転確認
    ScrewPickupDown = 6     # ねじ取り下降
    SylinderOnCheck = 7     # シリンダON確認
    ScrewPickupUp = 8       # ねじ取り上昇
    SylinderOffCheck = 9    # シリンダOFF確認
    GuideCloseCheck = 10    # ガイドクローズ確認
    ScrewPickupSuccessCheck = 11  # ねじあり確認
    ScrewPickupFinish = 100 # 終了
```

### EnumScrewTightState - ネジ締めシーケンス
```python
class EnumScrewTightState(Enum):
    ScrewTightUpper = 1           # ねじ締め上空
    DisplacementSensorReset = 2   # 変位センサーリセット
    GuideOpenCheck = 3            # ガイドオープン確認
    ScrewTightDown = 4            # ねじ締め下降
    TorqueUpCheck = 5             # トルクアップ確認
    DisplacementSensorTiming = 6  # 変位センサータイミング
    ZAxisUp = 7                   # Z軸上昇
    SylinderOffCheck = 8          # シリンダOFF確認
    GuideCloseCheck = 9           # ガイドクローズ確認
    ScrewTightFinish = 100        # 終了
```

### I/Oポート定義

#### OutPort - 出力ポート
```python
class OutPort(Enum):
    OUT00_DriverSV = 100      # ドライバー上下シリンダ
    OUT02_ScrewGuide = 102    # ネジガイド開閉
    OUT04_ScrewVacuum = 104   # ネジ吸着
    OUT06_DS_Timing = 106     # 変位センサーTiming信号
    OUT07_DS_Reset = 107      # 変位センサーReset信号
    OUT09_Driver = 109        # 電動ドライバーON/OFF
    OUT10_WorkLock = 110      # ワークロック
    OUT12_EMGLed = 112        # 非常停止LED
    OUT13_StartLeft = 113     # スタート左LED
    OUT14_StartRight = 114    # スタート右LED
    OUT15_Buzzer = 115        # ブザー
```

#### InPort - 入力ポート
```python
class InPort(Enum):
    IN00_DriverSV_Up = 0      # ドライバー上（原点）
    IN01_DriverSV_Down = 1    # ドライバー下（移動端）
    IN02_ScrewGuide_Close = 2 # ガイド閉（原点）
    IN03_ScrewGuide_Open = 3  # ガイド開（移動端）
    IN04_ScrewDetect = 4      # ネジ有無検出
    IN05_FeederScrew = 5      # フィーダーネジ検出
    IN06_DS_High = 6          # 変位センサーHigh信号
    IN07_DS_OK = 7            # 変位センサーOK信号
    IN08_DS_LOW = 8           # 変位センサーLOW信号
    IN09_DriverTorqueUp = 9   # トルクアップ検出
    IN10_WorkLock_Org = 10    # ワークロック解除
    IN11_WorkLock_Lock = 11   # ワークロック
    IN12_WorkEnable = 12      # ワーク有無検出
    IN13_StartLeftSW = 13     # スタート左SW
    IN14_StartRightSW = 14    # スタート右SW
```

### 主要関数

```python
def EMG_callback(msg: str):
    """非常停止コールバック"""

def BlinkStartSw1Sw2():
    """スタートスイッチLED点滅"""

def WaitInput(portNo: int, expect: int = 1, timeout_ms: int = 500) -> bool:
    """入力待機（タイムアウト付き）"""

def InitOutput() -> None:
    """出力初期化（全てOFF）"""

def NotificationBuzzer() -> None:
    """通知ブザー鳴動"""

def StartWaitProc() -> EnumReturnStatus:
    """スタート待機処理"""

def ScrewPickup(Speed: int) -> EnumScrewPickupError:
    """ネジ取りシーケンス"""
```

---

## 📊 データファイル形式

### SPLEBO-N.pos（位置データ）
```ini
[Position]
DataType=SPLEBO-N.POS
Version=1.00
TimeStamp=2025/06/04 23:26:50

[Point]
Count=10
Item1=1,0,0.0,0.0,0.0,,,,,,0,#Home1
Item2=2,0,,,,,,,,,0,
Item3=3,0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0,
Item4=99,0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0,0,
Item5=100,0,427.9,88.75,67.0,,,,,,0,sakai to 105
```

#### ポイントデータフォーマット
```
Item番号=ポイント番号,座標タイプ,X,Y,Z,U,S1,S2,A,B,保護フラグ,コメント
```

| フィールド | 説明 |
|-----------|------|
| ポイント番号 | プログラムから参照する番号 |
| 座標タイプ | 0=絶対座標 |
| X～B | 各軸座標（空白=使用しない） |
| 保護フラグ | 0=編集可, 1=保護 |
| コメント | 説明文 |

### SPLEBO-N.sys（システムパラメータ）
```ini
[Project]
DataType=SPLEBO-N.SYS
Version=1.00
TimeStamp=2025/06/04 14:47:01

[SysParam]
MaxSpeed=800,800,225,10,10,10,10,10
MaxAccel=2940,2940,1960,10,10,10,10,10
MaxDecel=2940,2940,1960,10,10,10,10,10
StartSpeed=200,200,50,10,10,10,10,10
OffsetSpeed=10,10,10,10,10,10,10,10
OriginSpeed=10,10,10,10,10,10,10,10
OriginOffset=0.0,0.0,0.0,0.0,0.0,0.0,0.0,0.0
LimitPlus=800.5,250.5,100.5,0.0,0.0,0.0,0.0,0.0
LimitMinus=-0.5,-0.5,-0.5,0.0,0.0,0.0,0.0,0.0
PulseLength=0.01,0.01,0.01,0.01,0.01,0.01,0.01,0.01
OriginOrder=2,2,1,1,1,1,1,1
OriginDir=0,0,0,0,0,0,0,0
OriginSensor=0,0,0,0,0,0,0,0
InPosition=1,1,1,1,0,0,0,0
MotorType=2,2,2,0,0,0,0,0
```

#### パラメータ配列順序
```
インデックス: [X軸, Y軸, Z軸, U軸, S1軸, S2軸, A軸, B軸]
```

#### MotorType値
| 値 | モータータイプ |
|---|--------------|
| 0 | なし |
| 2 | IAI電動アクチュエータ |
| 4 | ステッピングモーター |
| 5 | オリエンタルモーター aSTEP |

---

## 🏗️ システム構成図

```
┌─────────────────────────────────────────────────────────────┐
│                    Raspberry Pi                             │
├─────────────────────────────────────────────────────────────┤
│  sample.py (アプリケーション層)                              │
│      │                                                      │
│      ▼                                                      │
│  splebo_n.py (ライブラリ層)                                  │
│      ├── file_ctrl.py (ファイル管理)                         │
│      │       ├── SPLEBO-N.pos (位置データ)                   │
│      │       └── SPLEBO-N.sys (システム設定)                 │
│      ├── motion_control.py (モーション制御)                   │
│      ├── constant.py (定数定義)                              │
│      └── can.py (CAN通信)                                   │
│              │                                              │
│              ▼                                              │
│         SPI経由                                             │
│              │                                              │
│              ▼                                              │
│         MCP2515 (CANコントローラ)                            │
│              │                                              │
│              ▼                                              │
│         CANバス                                             │
│              │                                              │
│      ┌───────┴───────┐                                      │
│      ▼               ▼                                      │
│  I/Oエキスパンダ  モーターコントローラ                        │
│      │               │                                      │
│      ▼               ▼                                      │
│  センサー/SW      モーター(X,Y,Z,U軸)                        │
│  シリンダ         IAI/ステッピング/aSTEP                     │
│  LED/ブザー                                                 │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔄 処理フロー

### 1. 初期化フロー
```
splebo_n_class.__init__()
    │
    ├── param_init()          # パラメータ初期化
    ├── init_gpio()           # GPIO初期化
    ├── start_chk_EMG_thread() # 非常停止監視開始
    ├── PositionFileClass()   # 位置ファイル読込
    ├── ProjectFileClass()    # 設定ファイル読込
    ├── motion_init()         # モーション初期化
    ├── homing_class.init()   # 原点復帰初期化
    └── canio_init()          # CAN I/O初期化
```

### 2. ネジ締め作業フロー
```
原点復帰 → スタート待機 → ネジ取り → ネジ締め → 完了
    │           │            │          │
    ▼           ▼            ▼          ▼
  全軸を      両手SW      フィーダー   トルク
  原点へ      同時押し    からネジ取得  アップ確認
```

---

## 📝 更新履歴

| バージョン | 日付 | 内容 |
|-----------|------|------|
| 0.0.1 | 2024.10.22 | splebo_n.py 新規作成 |
| 0.0.1 | 2024.10.24 | sample.py 新規作成 |
| 0.0.1 | 2024.06.03 | can.py 新規作成 |
| 0.0.1 | 2024.05.16 | file_ctrl.py 新規作成 |
| 0.0.1 | 2022.07.11 | constant.py 新規作成 |

---

## ⚠️ 注意事項

1. **ハードウェア依存**: このコードはRaspberry Pi + MCP2515環境専用です
2. **安全装置**: 非常停止ボタン（GPIO15）は常時監視されています
3. **両手操作**: 安全のため、スタートには左右両方のスイッチ同時押しが必要です
4. **モータータイプ**: 軸ごとに異なるモーター（IAI/ステッピング/aSTEP）に対応

---

*このドキュメントは SPLEBO-N Teaching System の技術解説資料です。*
