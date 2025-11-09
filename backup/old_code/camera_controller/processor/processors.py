"""processor.py

Image processing pipeline abstraction and simple processors.
"""
from __future__ import annotations

from typing import Any
import cv2
import numpy as np


class Processor:
    """Abstract processor. Implement process(frame) -> frame."""

    def process(self, frame: Any) -> Any:
        raise NotImplementedError()


class PassthroughProcessor(Processor):
    def process(self, frame: Any) -> Any:
        return frame


class CannyProcessor(Processor):
    def __init__(self, threshold1: int = 50, threshold2: int = 150):
        self.t1 = threshold1
        self.t2 = threshold2

    def process(self, frame: Any) -> Any:
        # convert to gray, apply Canny, return BGR for display
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, self.t1, self.t2)
        return cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR)
