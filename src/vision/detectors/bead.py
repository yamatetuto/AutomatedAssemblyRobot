from typing import Dict, Any, List
import cv2
import numpy as np
import math
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
            return {"detected": False, "count": 0, "circles": [], "offset": None}

        height, width = image.shape[:2]
        image_center = (width // 2, height // 2)

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
        offset = None
        
        if circles is not None:
            circles = np.uint16(np.around(circles))
            for i in circles[0, :]:
                center = (int(i[0]), int(i[1]))
                radius = int(i[2])
                detected_circles.append({"center": center, "radius": radius})
            
            # 最も画像中心に近い円を選択してオフセットを計算
            if detected_circles:
                closest_circle = min(detected_circles, key=lambda c: math.hypot(c["center"][0] - image_center[0], c["center"][1] - image_center[1]))
                
                # オフセット (dx, dy)
                dx = closest_circle["center"][0] - image_center[0]
                dy = closest_circle["center"][1] - image_center[1]
                offset = {"dx": dx, "dy": dy}
                
        return {
            "detected": len(detected_circles) > 0,
            "count": len(detected_circles),
            "circles": detected_circles,
            "offset": offset
        }
