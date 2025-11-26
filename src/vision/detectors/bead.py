from typing import Dict, Any, List
import cv2
import numpy as np
from .base import BaseDetector

class BeadDetector(BaseDetector):
    """
    丸い物体（ガラス玉など）を検出するクラス
    """
    
    def __init__(self, min_dist: int = 20, param1: int = 50, param2: int = 30, min_radius: int = 10, max_radius: int = 50):
        self.min_dist = min_dist
        self.param1 = param1
        self.param2 = param2
        self.min_radius = min_radius
        self.max_radius = max_radius

    def detect(self, image: np.ndarray) -> Dict[str, Any]:
        if image is None:
            return {"detected": False, "count": 0, "circles": []}

        # グレースケール変換
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # ノイズ除去 (Median Blurは円検出に効果的)
        blurred = cv2.medianBlur(gray, 5)
        
        # 円検出 (Hough Circle Transform)
        circles = cv2.HoughCircles(
            blurred,
            cv2.HOUGH_GRADIENT,
            dp=1,
            minDist=self.min_dist,
            param1=self.param1,
            param2=self.param2,
            minRadius=self.min_radius,
            maxRadius=self.max_radius
        )
        
        detected_circles = []
        if circles is not None:
            circles = np.uint16(np.around(circles))
            for i in circles[0, :]:
                center = (int(i[0]), int(i[1]))
                radius = int(i[2])
                detected_circles.append({"center": center, "radius": radius})
                
        return {
            "detected": len(detected_circles) > 0,
            "count": len(detected_circles),
            "circles": detected_circles
        }
