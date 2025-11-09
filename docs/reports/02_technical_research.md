# 技術調査レポート: デバイス制御実装方法

**作成日**: 2025-11-05  
**目的**: 未実装デバイス（3Dプリンター、ディスペンサー、ロボットアーム）の制御方法を調査し、実装方針を決定

---

## 1. 3Dプリンター制御 (OctoPrint)

### 1.1 概要
- **対象機種**: Tronxy社 GEMINI S
- **制御方法**: OctoPrint REST API
- **通信方式**: HTTP/HTTPS

### 1.2 OctoPrint REST API 仕様

#### 認証
```python
headers = {
    "X-Api-Key": "YOUR_OCTOPRINT_API_KEY"
}
```

#### 主要エンドポイント

| エンドポイント | メソッド | 機能 |
|--------------|---------|------|
| `/api/version` | GET | バージョン情報取得 |
| `/api/connection` | GET/POST | 接続状態確認・制御 |
| `/api/printer` | GET | プリンター状態取得 |
| `/api/job` | GET/POST | ジョブ情報・制御 |
| `/api/files/local` | GET/POST | ファイル一覧・アップロード |
| `/api/printer/tool` | POST | ノズル温度設定 |
| `/api/printer/bed` | POST | ベッド温度設定 |
| `/api/printer/command` | POST | Gコード送信 |

### 1.3 実装例

```python
import requests

class OctoPrintController:
    def __init__(self, host: str, api_key: str, port: int = 80):
        self.base_url = f"http://{host}:{port}"
        self.headers = {"X-Api-Key": api_key}
    
    def get_printer_state(self) -> dict:
        """プリンター状態を取得"""
        response = requests.get(
            f"{self.base_url}/api/printer",
            headers=self.headers
        )
        return response.json()
    
    def set_tool_temperature(self, temp: int):
        """ノズル温度を設定"""
        data = {"command": "target", "targets": {"tool0": temp}}
        requests.post(
            f"{self.base_url}/api/printer/tool",
            headers=self.headers,
            json=data
        )
    
    def start_print(self, filename: str):
        """プリント開始"""
        data = {"command": "select", "print": True}
        requests.post(
            f"{self.base_url}/api/files/local/{filename}",
            headers=self.headers,
            json=data
        )
    
    def send_gcode(self, commands: list[str]):
        """Gコード送信"""
        data = {"commands": commands}
        requests.post(
            f"{self.base_url}/api/printer/command",
            headers=self.headers,
            json=data
        )
```

### 1.4 必要情報（ユーザー確認事項）
- [ ] OctoPrintサーバーのIPアドレス
- [ ] OctoPrint APIキー（Settings > API から取得）
- [ ] 使用ポート番号（デフォルト: 80 または 5000）

### 1.5 依存ライブラリ
```
requests>=2.31.0
```

---

## 2. ディスペンサー制御 (GPIO)

### 2.1 概要
- **制御方式**: I/O制御（デジタル出力）
- **使用インターフェース**: Raspberry Pi GPIO
- **想定動作**: ON/OFFによる吐出制御

### 2.2 GPIO制御方法

#### オプション1: RPi.GPIO
```python
import RPi.GPIO as GPIO
import time

class DispenserController:
    def __init__(self, pin: int):
        self.pin = pin
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pin, GPIO.OUT)
        GPIO.output(self.pin, GPIO.LOW)
    
    def dispense(self, duration: float):
        """指定時間吐出"""
        GPIO.output(self.pin, GPIO.HIGH)
        time.sleep(duration)
        GPIO.output(self.pin, GPIO.LOW)
    
    def cleanup(self):
        GPIO.cleanup()
```

#### オプション2: gpiozero（推奨：より簡潔）
```python
from gpiozero import OutputDevice
import time

class DispenserController:
    def __init__(self, pin: int):
        self.device = OutputDevice(pin)
    
    def dispense(self, duration: float):
        """指定時間吐出"""
        self.device.on()
        time.sleep(duration)
        self.device.off()
    
    def dispense_pulse(self, duration: float, interval: float, count: int):
        """パルス吐出"""
        for _ in range(count):
            self.device.on()
            time.sleep(duration)
            self.device.off()
            time.sleep(interval)
    
    def close(self):
        self.device.close()
```

### 2.3 必要情報（ユーザー確認事項）
- [ ] ディスペンサーの型番・仕様
- [ ] 使用するGPIOピン番号
- [ ] 制御電圧レベル（3.3V / 5V）
- [ ] リレーの有無（高電圧制御の場合）
- [ ] 吐出量の制御方法（時間制御 or パルス制御）

### 2.4 依存ライブラリ
```
RPi.GPIO>=0.7.1
# または
gpiozero>=2.0.1
```

### 2.5 配線注意事項
- Raspberry PiのGPIOは3.3V出力
- 5V駆動のディスペンサーの場合はレベル変換またはリレーが必要
- GPIO 2, 3以外のピンを使用推奨（I2Cとの競合回避）

---

## 3. ロボットアーム制御 (企業ライブラリ)

### 3.1 概要
- **制御対象**: XYZ直交ロボット（株式会社コスモスウェブ製）
- **ストローク**: X: 800mm, Y: 250mm, Z: 100mm
- **制御方法**: 企業提供のPythonライブラリ

### 3.2 想定インターフェース

企業ライブラリの一般的な構造を想定:

```python
# 想定される企業ライブラリの使用例
from cosmos_robot import RobotController  # 仮名

class RobotWrapper:
    def __init__(self, port: str = "/dev/ttyUSB0"):
        self.robot = RobotController(port)
    
    def move_to(self, x: float, y: float, z: float):
        """絶対座標へ移動"""
        self.robot.move_absolute(x, y, z)
    
    def move_relative(self, dx: float, dy: float, dz: float):
        """相対移動"""
        self.robot.move_relative(dx, dy, dz)
    
    def get_position(self) -> tuple[float, float, float]:
        """現在位置取得"""
        return self.robot.get_current_position()
    
    def home(self):
        """原点復帰"""
        self.robot.home_all_axes()
```

### 3.3 必要情報（ユーザー確認事項）⚠️
- [ ] **企業ライブラリの場所** (インストール済みか、ファイルで提供されているか)
- [ ] ライブラリのモジュール名
- [ ] APIドキュメントまたはサンプルコード
- [ ] 通信方式（USB, Ethernet, RS-232C など）
- [ ] 座標系の定義（原点位置、単位）
- [ ] 速度・加速度の設定方法
- [ ] エラーハンドリング方法

### 3.4 統合時の考慮事項

#### 座標変換
カメラ座標系とロボット座標系の変換が必要:
```python
import numpy as np

class CoordinateTransformer:
    def __init__(self, calibration_matrix: np.ndarray):
        self.matrix = calibration_matrix
    
    def camera_to_robot(self, x_cam: float, y_cam: float) -> tuple[float, float]:
        """カメラ座標をロボット座標に変換"""
        cam_point = np.array([x_cam, y_cam, 1])
        robot_point = self.matrix @ cam_point
        return robot_point[0], robot_point[1]
```

キャリブレーション手順:
1. カメラで既知のロボット座標にある物体を撮影
2. 複数点（最低4点）でカメラ座標とロボット座標の対応を記録
3. アフィン変換行列を計算

---

## 4. 画像処理アルゴリズム

### 4.1 必要機能

#### 4.1.1 物体検出
```python
import cv2
import numpy as np

def detect_objects(frame: np.ndarray, 
                   lower_color: tuple, 
                   upper_color: tuple) -> list[dict]:
    """色ベースの物体検出"""
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, lower_color, upper_color)
    
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, 
                                    cv2.CHAIN_APPROX_SIMPLE)
    
    objects = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area > 100:  # ノイズ除去
            M = cv2.moments(cnt)
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
                objects.append({
                    "center": (cx, cy),
                    "area": area,
                    "contour": cnt
                })
    return objects
```

#### 4.1.2 部品認識（テンプレートマッチング）
```python
def template_matching(frame: np.ndarray, 
                      template: np.ndarray, 
                      threshold: float = 0.8) -> list[tuple]:
    """テンプレートマッチングで部品位置を検出"""
    result = cv2.matchTemplate(frame, template, cv2.TM_CCOEFF_NORMED)
    locations = np.where(result >= threshold)
    return list(zip(*locations[::-1]))
```

#### 4.1.3 エッジ検出・位置補正
```python
def detect_edges(frame: np.ndarray) -> np.ndarray:
    """Cannyエッジ検出"""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    edges = cv2.Canny(blurred, 50, 150)
    return edges
```

### 4.2 実装場所
`camera_controller/processor/processors.py` に実装

---

## 5. 統合システムアーキテクチャ

### 5.1 レイヤー構造

```
┌─────────────────────────────────────┐
│     Web Application (FastAPI)       │  ← ユーザーインターフェース
├─────────────────────────────────────┤
│   Assembly Controller (統合制御)     │  ← オーケストレーション層
├─────────────────────────────────────┤
│  デバイスコントローラー層              │
│  - CameraController                 │
│  - RobotController                  │
│  - GripperController (CONController)│
│  - PrinterController (OctoPrint)    │
│  - DispenserController              │
├─────────────────────────────────────┤
│    ハードウェア抽象化層               │
│  - GPIO / Modbus / HTTP             │
└─────────────────────────────────────┘
```

### 5.2 通信フロー

```python
# 組立シーケンスの例
class AssemblyController:
    def __init__(self):
        self.camera = CameraController()
        self.robot = RobotController()
        self.gripper = CONController()
        self.printer = OctoPrintController()
        self.dispenser = DispenserController()
    
    async def assembly_sequence(self):
        """組立シーケンス実行"""
        # 1. 3Dプリンターで部品印刷
        await self.printer.start_print("part.gcode")
        await self.printer.wait_for_completion()
        
        # 2. カメラで部品位置を検出
        frame = self.camera.capture()
        objects = detect_objects(frame)
        target = objects[0]["center"]
        
        # 3. ロボットで部品をピックアップ
        robot_pos = self.transform_coordinates(target)
        self.robot.move_to(*robot_pos)
        self.gripper.grip()
        
        # 4. 接着剤を塗布
        self.robot.move_to(adhesive_position)
        self.dispenser.dispense(duration=0.5)
        
        # 5. 組み立て
        self.robot.move_to(assembly_position)
        self.gripper.release()
```

---

## 6. 通信プロトコル一覧

| デバイス | プロトコル | ライブラリ | 通信速度 |
|---------|-----------|-----------|---------|
| カメラ | USB/CSI | OpenCV | 30 FPS |
| グリッパー | Modbus RTU | minimalmodbus | 9600 baud |
| ロボット | 不明（確認必要） | 企業ライブラリ | - |
| プリンター | HTTP/REST | requests | - |
| ディスペンサー | GPIO | RPi.GPIO/gpiozero | - |

---

## 7. セキュリティとエラーハンドリング

### 7.1 セキュリティ
- OctoPrint APIキーは環境変数で管理
- 設定ファイルは `.gitignore` に追加
- 例: `.env` ファイル使用
  ```
  OCTOPRINT_HOST=192.168.1.100
  OCTOPRINT_API_KEY=your_api_key_here
  ```

### 7.2 エラーハンドリング
```python
class AssemblyError(Exception):
    """組立エラー基底クラス"""
    pass

class DeviceConnectionError(AssemblyError):
    """デバイス接続エラー"""
    pass

class MotionError(AssemblyError):
    """動作エラー"""
    pass

# 使用例
try:
    controller.gripper.grip()
except ModbusError as e:
    raise DeviceConnectionError(f"グリッパー通信エラー: {e}")
```

---

## 8. 推奨ライブラリ・バージョン

```txt
# 既存
opencv-python==4.8.1.78
aiortc==1.6.0
aiohttp==3.9.1
minimalmodbus==2.1.1
pyserial==3.5

# 追加必要
requests==2.31.0
RPi.GPIO==0.7.1  # または gpiozero==2.0.1
python-dotenv==1.0.0
fastapi==0.104.1
uvicorn[standard]==0.24.0
websockets==12.0
pydantic==2.5.0
numpy==1.24.3
pytest==7.4.3
pytest-asyncio==0.21.1
```

---

## 9. 次のステップ

### ユーザーへの確認事項 ❓
1. **ロボットライブラリの詳細情報提供**
   - ライブラリファイルの場所
   - APIドキュメント
   - サンプルコード

2. **ディスペンサー仕様**
   - 型番
   - 制御電圧
   - 使用GPIOピン

3. **OctoPrint情報**
   - IPアドレス
   - APIキー
   - ポート番号

4. **Raspberry Pi 2台の役割分担**
   - どちらをメイン制御に使用するか
   - 通信方法（SSH, ネットワーク経由など）

### 実装優先順位
1. ✅ 3Dプリンター制御（OctoPrint）← 最も標準的
2. ✅ ディスペンサー制御（GPIO）← 比較的単純
3. ⚠️ ロボットアーム統合 ← ライブラリ確認後
4. ✅ 画像処理アルゴリズム ← 並行実装可能

---

**次のレポート**: `03_implementation_plan.md` で具体的な実装手順を策定
