from typing import Dict, Any, Optional
import numpy as np
from .detectors.fiber import FiberDetector
from .detectors.bead import BeadDetector

class VisionManager:
    """
    画像処理モジュールの統括クラス
    """
    
    def __init__(self):
        self.fiber_detector = FiberDetector()
        self.bead_detector = BeadDetector()

    def detect_fiber(self, image: np.ndarray) -> Dict[str, Any]:
        """
        画像から光ファイバーを検出する
        """
        return self.fiber_detector.detect(image)

    def detect_bead(self, image: np.ndarray) -> Dict[str, Any]:
        """
        画像からガラス玉を検出する
        """
        return self.bead_detector.detect(image)
