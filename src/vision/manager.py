from typing import Dict, Any, Optional
import numpy as np
import cv2
import base64
from .detectors.fiber import FiberDetector
from .detectors.bead import BeadDetector

class VisionManager:
    """
    画像処理モジュールの統括クラス
    """
    
    def __init__(self):
        self.fiber_detector = FiberDetector()
        self.bead_detector = BeadDetector()

    def _encode_image(self, image: np.ndarray) -> str:
        """画像をBase64文字列にエンコードする"""
        _, buffer = cv2.imencode('.jpg', image)
        return base64.b64encode(buffer).decode('utf-8')

    def detect_fiber(self, image: np.ndarray) -> Dict[str, Any]:
        """
        画像から光ファイバーを検出し、結果画像と共に返す
        """
        result = self.fiber_detector.detect(image)
        
        # 結果の描画
        output_image = image.copy()
        height, width = output_image.shape[:2]
        center = (width // 2, height // 2)
        
        # 中心十字
        cv2.drawMarker(output_image, center, (0, 255, 0), markerType=cv2.MARKER_CROSS, markerSize=20, thickness=2)

        if result["detected"]:
            # 検出された全ての線 (薄い青)
            for line in result["lines"]:
                cv2.line(output_image, line[0], line[1], (255, 200, 200), 1)
            
            # ペアリングされた線 (青)
            for line in result.get("paired_lines", []):
                cv2.line(output_image, line[0], line[1], (255, 0, 0), 2)
                
            # 中心線 (赤)
            if result["center_line"]:
                cl = result["center_line"]
                cv2.line(output_image, cl[0], cl[1], (0, 0, 255), 2)
            
            # オフセット線 (黄色)
            if result["offset"]:
                dx = result["offset"]["dx"]
                dy = result["offset"]["dy"]
                target_point = (int(center[0] + dx), int(center[1] + dy))
                cv2.line(output_image, center, target_point, (0, 255, 255), 2)
                cv2.circle(output_image, target_point, 4, (0, 255, 255), -1)
                
        result["image_base64"] = self._encode_image(output_image)
        return result

    def detect_bead(self, image: np.ndarray) -> Dict[str, Any]:
        """
        画像からガラス玉を検出し、結果画像と共に返す
        """
        result = self.bead_detector.detect(image)
        
        # 結果の描画
        output_image = image.copy()
        height, width = output_image.shape[:2]
        center = (width // 2, height // 2)
        
        # 中心十字
        cv2.drawMarker(output_image, center, (0, 255, 0), markerType=cv2.MARKER_CROSS, markerSize=20, thickness=2)

        if result["detected"]:
            for circle in result["circles"]:
                # 円周 (緑)
                cv2.circle(output_image, circle["center"], circle["radius"], (0, 255, 0), 2)
                # 中心点 (赤)
                cv2.circle(output_image, circle["center"], 2, (0, 0, 255), 3)
                
            # オフセット線 (中心から最も近い円へ)
            if result["offset"]:
                # 最も近い円を探す（簡易的に再計算）
                closest = min(result["circles"], key=lambda c: (c["center"][0]-center[0])**2 + (c["center"][1]-center[1])**2)
                cv2.line(output_image, center, closest["center"], (0, 255, 255), 2)

        result["image_base64"] = self._encode_image(output_image)
        return result
