"""
設定管理モジュール
環境変数や設定ファイルを一元管理
"""
import os
from pathlib import Path

# プロジェクトルート
PROJECT_ROOT = Path(__file__).parent.parent.parent

# カメラ設定
CAMERA_DEVICE = int(os.getenv('CAMERA_DEVICE', '0'))
CAMERA_WIDTH = int(os.getenv('CAMERA_WIDTH', '640'))
CAMERA_HEIGHT = int(os.getenv('CAMERA_HEIGHT', '480'))
CAMERA_FPS = int(os.getenv('CAMERA_FPS', '30'))
CAMERA_FOURCC = os.getenv('CAMERA_FOURCC', 'MJPG')

# グリッパー設定
GRIPPER_PORT = os.getenv('GRIPPER_PORT', '/dev/gripper')
GRIPPER_SLAVE_ADDR = int(os.getenv('GRIPPER_SLAVE_ADDR', '1'))
GRIPPER_BAUDRATE = int(os.getenv('GRIPPER_BAUDRATE', '38400'))

# WebRTC設定
STUN_SERVER = os.getenv('STUN_SERVER', 'stun:stun.l.google.com:19302')

# ログ設定
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# スナップショット保存先
SNAPSHOTS_DIR = PROJECT_ROOT / 'snapshots'
SNAPSHOTS_DIR.mkdir(exist_ok=True)

# ポジションテーブル保存先  
POSITION_TABLE_FILE = PROJECT_ROOT / 'position_table.json'

# OctoPrint設定
OCTOPRINT_URL = os.getenv('OCTOPRINT_URL', 'http://127.0.0.1:5000')
OCTOPRINT_API_KEY = os.getenv('OCTOPRINT_API_KEY')
OCTOPRINT_POLL_INTERVAL = float(os.getenv('OCTOPRINT_POLL_INTERVAL', '5.0'))

# プリンター接続設定 (Noneの場合はAUTO)
PRINTER_PORT = os.getenv('PRINTER_PORT', '/dev/printer')  # 例: '/dev/ttyUSB0'
PRINTER_BAUDRATE = os.getenv('PRINTER_BAUDRATE', None)  # 例: 115200

# プリンターサイズ設定
PRINTER_BED_WIDTH = int(os.getenv('PRINTER_BED_WIDTH', '220'))
PRINTER_BED_DEPTH = int(os.getenv('PRINTER_BED_DEPTH', '220'))


# 画像処理設定 (Vision)

# ファイバー検出 (Fiber Detection)
# Cannyエッジ検出のヒステリシス閾値1（最小値）。これ以下の勾配はエッジとみなされない。
VISION_FIBER_CANNY_THRESHOLD1 = int(os.getenv('VISION_FIBER_CANNY_THRESHOLD1', '50'))
# Cannyエッジ検出のヒステリシス閾値2（最大値）。これ以上の勾配は確実にエッジとみなされる。
VISION_FIBER_CANNY_THRESHOLD2 = int(os.getenv('VISION_FIBER_CANNY_THRESHOLD2', '150'))
# 検出する直線の最小長さ（ピクセル）。これより短い線分は棄却される。
VISION_FIBER_MIN_LINE_LENGTH = int(os.getenv('VISION_FIBER_MIN_LINE_LENGTH', '100'))
# 同一直線とみなす線分間の最大隙間（ピクセル）。これ以下の隙間は埋められる。
VISION_FIBER_MAX_LINE_GAP = int(os.getenv('VISION_FIBER_MAX_LINE_GAP', '10'))

# ビーズ検出 (Bead Detection)
# 検出される円の中心間の最小距離。これより近い円は除外される（重複検出防止）。
VISION_BEAD_MIN_DIST = int(os.getenv('VISION_BEAD_MIN_DIST', '20'))
# Cannyエッジ検出器の高い方の閾値（HoughCircles内部で使用）。低い方はこの半分になる。
VISION_BEAD_PARAM1 = int(os.getenv('VISION_BEAD_PARAM1', '50'))
# 円の中心検出の閾値。小さいほど多くの（誤検出含む）円が検出され、大きいほど真円に近いものだけが検出される。
VISION_BEAD_PARAM2 = int(os.getenv('VISION_BEAD_PARAM2', '30'))
# 検出する円の最小半径。
VISION_BEAD_MIN_RADIUS = int(os.getenv('VISION_BEAD_MIN_RADIUS', '10'))
# 検出する円の最大半径。
VISION_BEAD_MAX_RADIUS = int(os.getenv('VISION_BEAD_MAX_RADIUS', '50'))


# ============================================================
# ロボット（TEACHING/SPLEBO-N）設定
# ============================================================

# シミュレーションモード
# True: ハードウェアなしで動作（開発PC、CI/CDで使用）
# False: 実機接続（Raspberry Piで使用）
ROBOT_SIMULATION_MODE = os.getenv("ROBOT_SIMULATION_MODE", "true").lower() in ("true", "1", "yes")

# CAN通信設定
ROBOT_CAN_SPI_BUS = int(os.getenv("ROBOT_CAN_SPI_BUS", "0"))
ROBOT_CAN_SPI_DEVICE = int(os.getenv("ROBOT_CAN_SPI_DEVICE", "0"))
ROBOT_CAN_SPEED_HZ = int(os.getenv("ROBOT_CAN_SPEED_HZ", "500000"))

# GPIO設定
ROBOT_GPIO_NOVA_RESET = int(os.getenv("ROBOT_GPIO_NOVA_RESET", "14"))
ROBOT_GPIO_POWER = int(os.getenv("ROBOT_GPIO_POWER", "12"))
ROBOT_GPIO_CAN_CS = int(os.getenv("ROBOT_GPIO_CAN_CS", "8"))
ROBOT_GPIO_EMG_SW = int(os.getenv("ROBOT_GPIO_EMG_SW", "15"))

# 軸設定
ROBOT_AXIS_COUNT = int(os.getenv("ROBOT_AXIS_COUNT", "8"))
ROBOT_ENABLED_AXES = os.getenv("ROBOT_ENABLED_AXES", "X,Y,Z,U").split(",")

# 速度制限
ROBOT_MAX_SPEED = int(os.getenv("ROBOT_MAX_SPEED", "100"))
ROBOT_DEFAULT_SPEED = int(os.getenv("ROBOT_DEFAULT_SPEED", "50"))

# I/Oポーリング間隔（秒）
ROBOT_IO_POLL_INTERVAL = float(os.getenv("ROBOT_IO_POLL_INTERVAL", "0.01"))

# 位置データファイル
ROBOT_DATA_DIR = PROJECT_ROOT / "data" / "robot"
ROBOT_DATA_DIR.mkdir(parents=True, exist_ok=True)
ROBOT_POSITION_FILE = ROBOT_DATA_DIR / "positions.json"
ROBOT_SEQUENCES_FILE = ROBOT_DATA_DIR / "sequences.json"
