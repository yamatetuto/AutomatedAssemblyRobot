"""OpenCV capture implementation for the camera_controller package."""
from __future__ import annotations

import cv2
from typing import Tuple, Optional


class Capture:
    """Abstract capture interface."""

    def read(self) -> Tuple[bool, Optional[any]]:
        """Read a frame. Return (ret, frame)"""
        raise NotImplementedError()


class OpenCVCapture(Capture):
    def __init__(self, device: int = 0, width: int = 0, height: int = 0):
        self.device = device
        self.cap = cv2.VideoCapture(device)
        if width:
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        if height:
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

    def read(self):
        return self.cap.read()

    def release(self):
        try:
            self.cap.release()
        except Exception:
            pass
