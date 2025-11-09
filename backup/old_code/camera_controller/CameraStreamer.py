#!/usr/bin/env python3
"""CLI entrypoint for camera_controller package.

This file mirrors the previous CameraStreamer script but uses imports from the
`camera_controller` package. It also uses a safe import pattern so that it can be
run either as a module (python -m camera_controller.CameraStreamer) or directly
as a script (python camera_controller/CameraStreamer.py) from the package root.
"""
from __future__ import annotations

import argparse
import datetime
import sys
import time
from typing import Optional
import asyncio
import json
import re

from pathlib import Path
import numpy as np
from fractions import Fraction
import shutil
import subprocess
import shlex

try:
    # Prefer package import when running as a package
    if __package__:
        from .webrtc.streamer import run_webrtc_server as webrtc_run
    else:
        from camera_controller.webrtc.streamer import run_webrtc_server as webrtc_run
except Exception:
    # Fallbacks for older layouts
    try:
        from camera_controll.webrtc_streamer import run_webrtc_server as webrtc_run
    except Exception:
        # Last resort: try local module name
        from webrtc.streamer import run_webrtc_server as webrtc_run

try:
    import cv2
except Exception:
    print("OpenCV (cv2) is required. Install with: pip3 install opencv-python")
    raise


def save_snapshot(frame) -> str:
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"snapshot_{ts}.jpg"
    cv2.imwrite(filename, frame)
    return filename


def rotate_frame(frame, rotation: int):
    r = rotation % 360
    if r == 90:
        return cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
    if r == 180:
        return cv2.rotate(frame, cv2.ROTATE_180)
    if r == 270:
        return cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
    return frame


def run_opencv(device: int, width: int, height: int, rotation: int, flip: bool):
    cap = cv2.VideoCapture(device)
    if width:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    if height:
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

    if not cap.isOpened():
        raise RuntimeError(f"Unable to open VideoCapture device {device}")

    paused = False
    window = "CameraStreamer - OpenCV"
    cv2.namedWindow(window, cv2.WINDOW_NORMAL)

    while True:
        if not paused:
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.05)
                continue

            frame = rotate_frame(frame, rotation)
            if flip:
                frame = cv2.flip(frame, 1)

            cv2.imshow(window, frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        elif key == ord("s"):
            if not paused and 'frame' in locals():
                fn = save_snapshot(frame)
                print(f"Saved snapshot: {fn}")
        elif key == ord("p"):
            paused = not paused
            print("Paused" if paused else "Resumed")

    cap.release()
    cv2.destroyAllWindows()


def parse_args():
    p = argparse.ArgumentParser(description="Simple Raspberry Pi camera capture and display")
    p.add_argument("--device", "-d", type=int, default=0, help="OpenCV video device index (default:0)")
    p.add_argument("--width", type=int, default=0, help="Requested capture width")
    p.add_argument("--height", type=int, default=0, help="Requested capture height")
    p.add_argument("--rotation", type=int, default=0, help="Rotate frame by degrees (90/180/270)")
    p.add_argument("--flip", action="store_true", help="Flip frame horizontally")
    p.add_argument("--use-picamera2", action="store_true", help="Use picamera2 if available")
    p.add_argument("--webrtc", action="store_true", help="Start a WebRTC server for headless streaming")
    p.add_argument("--webrtc-port", type=int, default=8080, help="Port for WebRTC HTTP server (default: 8080)")
    p.add_argument('--brightness', type=int, help='Set camera brightness (1-255)')
    p.add_argument('--contrast', type=int, help='Set camera contrast')
    p.add_argument('--saturation', type=int, help='Set camera saturation')
    p.add_argument('--hue', type=int, help='Set camera hue (1-255)')
    p.add_argument('--awb', type=int, choices=[0,1], help='White balance automatic (1=on,0=off)')
    return p.parse_args()


def main():
    args = parse_args()

    if args.use_picamera2:
        try:
            # Try to use picamera2 preview CLI; keep fallback to OpenCV if unavailable
            from picamera2 import Picamera2  # type: ignore
            # If user explicitly requested picamera2 capture, delegate to the module's implementation
            # (Picamera2 integration can be added to the capture package later)
            raise RuntimeError("picamera2 path not implemented in this packaged CLI; use --webrtc with OpenCV capture for now")
        except Exception as e:
            print(f"picamera2 failed or not available: {e}. Falling back to OpenCV.")

    if args.webrtc:
        try:
            controls_init = {
                'brightness': args.brightness,
                'contrast': args.contrast,
                'saturation': args.saturation,
                'hue': args.hue,
                'white_balance_automatic': args.awb
            }
            # Build device path
            device_path = f"/dev/video{args.device}"
            
            # Default to MJPG 640x480@30 if not specified
            width = args.width if args.width > 0 else 640
            height = args.height if args.height > 0 else 480
            fps = 30.0
            codec = 'MJPG'
            
            # Find index.html
            import os
            index_html = os.path.join(os.path.dirname(__file__), 'webrtc_index.html')
            
            webrtc_run(device_path, width, height, fps, codec, args.webrtc_port, index_html)
            return
        except Exception as e:
            print(f"WebRTC server failed to start: {e}. Falling back to OpenCV local display.")

    try:
        run_opencv(args.device, args.width, args.height, args.rotation, args.flip)
    except Exception as e:
        print(f"Error running camera: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
