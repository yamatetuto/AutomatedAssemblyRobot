from abc import ABC, abstractmethod
from typing import Dict, Any
import numpy as np

class BaseDetector(ABC):
    """
    画像検出器の基底クラス
    """
    
    @abstractmethod
    def detect(self, image: np.ndarray) -> Dict[str, Any]:
        """
        画像から物体を検出する
        
        Args:
            image: OpenCV形式の画像データ (BGR, np.ndarray)
            
        Returns:
            Dict[str, Any]: 検出結果を含む辞書
        """
        pass
