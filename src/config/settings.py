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
VISION_FIBER_CANNY_THRESHOLD1 = int(os.getenv('VISION_FIBER_CANNY_THRESHOLD1', '50'))
VISION_FIBER_CANNY_THRESHOLD2 = int(os.getenv('VISION_FIBER_CANNY_THRESHOLD2', '150'))
VISION_FIBER_MIN_LINE_LENGTH = int(os.getenv('VISION_FIBER_MIN_LINE_LENGTH', '100'))
VISION_FIBER_MAX_LINE_GAP = int(os.getenv('VISION_FIBER_MAX_LINE_GAP', '10'))

# ビーズ検出 (Bead Detection)
VISION_BEAD_MIN_DIST = int(os.getenv('VISION_BEAD_MIN_DIST', '20'))
VISION_BEAD_PARAM1 = int(os.getenv('VISION_BEAD_PARAM1', '50'))
VISION_BEAD_PARAM2 = int(os.getenv('VISION_BEAD_PARAM2', '30'))
VISION_BEAD_MIN_RADIUS = int(os.getenv('VISION_BEAD_MIN_RADIUS', '10'))
VISION_BEAD_MAX_RADIUS = int(os.getenv('VISION_BEAD_MAX_RADIUS', '50'))
