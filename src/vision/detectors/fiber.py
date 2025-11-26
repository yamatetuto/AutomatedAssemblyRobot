from typing import Dict, Any, List
import cv2
import numpy as np
from .base import BaseDetector

class FiberDetector(BaseDetector):
    """
    細長い物体（光ファイバーなど）を検出するクラス
    """
    
    def __init__(self, canny_threshold1: int = 50, canny_threshold2: int = 150, min_line_length: int = 100, max_line_gap: int = 10):
        self.canny_threshold1 = canny_threshold1
        self.canny_threshold2 = canny_threshold2
        self.min_line_length = min_line_length
        self.max_line_gap = max_line_gap

    def detect(self, image: np.ndarray) -> Dict[str, Any]:
        if image is None:
            return {"detected": False, "count": 0, "lines": []}

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
                
        return {
            "detected": len(detected_lines) > 0,
            "count": len(detected_lines),
            "lines": detected_lines
        }
