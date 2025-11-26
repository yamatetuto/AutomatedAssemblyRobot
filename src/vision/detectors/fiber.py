from typing import Dict, Any, List, Tuple, Optional
import cv2
import numpy as np
import math
from .base import BaseDetector
from src.config.settings import (
    VISION_FIBER_CANNY_THRESHOLD1,
    VISION_FIBER_CANNY_THRESHOLD2,
    VISION_FIBER_MIN_LINE_LENGTH,
    VISION_FIBER_MAX_LINE_GAP
)

class FiberDetector(BaseDetector):
    """
    細長い物体（光ファイバーなど）を検出するクラス
    2本の平行線を検出し、その中心線と画像中心との距離を計算する
    """
    
    def __init__(self, 
                 canny_threshold1: int = VISION_FIBER_CANNY_THRESHOLD1, 
                 canny_threshold2: int = VISION_FIBER_CANNY_THRESHOLD2, 
                 min_line_length: int = VISION_FIBER_MIN_LINE_LENGTH, 
                 max_line_gap: int = VISION_FIBER_MAX_LINE_GAP):
        self.canny_threshold1 = canny_threshold1
        self.canny_threshold2 = canny_threshold2
        self.min_line_length = min_line_length
        self.max_line_gap = max_line_gap

    def detect(self, image: np.ndarray) -> Dict[str, Any]:
        if image is None:
            return {"detected": False, "count": 0, "lines": [], "center_line": None, "offset": None}

        height, width = image.shape[:2]
        image_center = (width // 2, height // 2)

        # グレースケール変換
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # ノイズ除去
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # エッジ検出
        edges = cv2.Canny(blurred, self.canny_threshold1, self.canny_threshold2)
        
        # 直線検出 (確率的Hough変換)
        lines = cv2.HoughLinesP(
            edges,
            rho=1,
            theta=np.pi/180,
            threshold=50,
            minLineLength=self.min_line_length,
            maxLineGap=self.max_line_gap
        )
        
        detected_lines = []
        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]
                detected_lines.append(((int(x1), int(y1)), (int(x2), int(y2))))
        
        # 平行線のペアリングと中心線の算出
        center_line = None
        offset = None
        paired_lines = []

        if len(detected_lines) >= 2:
            # 最も長く、平行に近いペアを探す簡易ロジック
            # 今回は単純に最も長い2本を選ぶ（実運用では角度フィルタリングが必要）
            # 長さでソート
            detected_lines.sort(key=lambda l: math.hypot(l[1][0]-l[0][0], l[1][1]-l[0][1]), reverse=True)
            line1 = detected_lines[0]
            line2 = detected_lines[1]
            paired_lines = [line1, line2]

            # 中心線の計算
            # 各線分の中点
            mid1 = ((line1[0][0] + line1[1][0]) / 2, (line1[0][1] + line1[1][1]) / 2)
            mid2 = ((line2[0][0] + line2[1][0]) / 2, (line2[0][1] + line2[1][1]) / 2)
            
            # 中心線の中点
            center_mid = ((mid1[0] + mid2[0]) / 2, (mid1[1] + mid2[1]) / 2)
            
            # 平均角度 (簡易的に線分1の角度を採用、本来は平均をとる)
            angle = math.atan2(line1[1][1] - line1[0][1], line1[1][0] - line1[0][0])
            
            # 中心線 (点と角度で表現)
            # 表示用に直線を伸ばす
            length = max(width, height)
            cx1 = int(center_mid[0] - length * math.cos(angle))
            cy1 = int(center_mid[1] - length * math.sin(angle))
            cx2 = int(center_mid[0] + length * math.cos(angle))
            cy2 = int(center_mid[1] + length * math.sin(angle))
            center_line = ((cx1, cy1), (cx2, cy2))

            # 画像中心からの距離 (点と直線の距離)
            # 直線の方程式 ax + by + c = 0
            # m = tan(angle) => y - y0 = m(x - x0) => mx - y + (y0 - mx0) = 0
            # a = m, b = -1, c = y0 - mx0
            # ただし垂直に近い場合は別途考慮が必要だが、ここでは一般形を使う
            
            # ベクトルによる距離計算 (符号付き)
            # 中心線上の点 P(center_mid) と方向ベクトル V(cos, sin)
            # 画像中心 C から直線へのベクトル PC = C - P
            # 距離 = PC と 法線ベクトル N(-sin, cos) の内積
            
            vx = math.cos(angle)
            vy = math.sin(angle)
            nx = -vy
            ny = vx
            
            pc_x = image_center[0] - center_mid[0]
            pc_y = image_center[1] - center_mid[1]
            
            offset = pc_x * nx + pc_y * ny

        elif len(detected_lines) == 1:
             # 1本だけの場合はその線を中心線とする
             line = detected_lines[0]
             center_line = line
             paired_lines = [line]
             
             # 距離計算 (同上)
             mid = ((line[0][0] + line[1][0]) / 2, (line[0][1] + line[1][1]) / 2)
             angle = math.atan2(line[1][1] - line[0][1], line[1][0] - line[0][0])
             
             vx = math.cos(angle)
             vy = math.sin(angle)
             nx = -vy
             ny = vx
             
             pc_x = image_center[0] - mid[0]
             pc_y = image_center[1] - mid[1]
             
             offset = pc_x * nx + pc_y * ny

        return {
            "detected": len(detected_lines) > 0,
            "count": len(detected_lines),
            "lines": detected_lines,
            "paired_lines": paired_lines,
            "center_line": center_line,
            "offset": offset
        }
