#!/usr/bin/env python3
"""
統合Web UI - WebRTC対応版
カメラストリーミング(WebRTC)、カメラパラメータ調整、グリッパー制御
"""
import os
import sys
import asyncio
import json
import uuid
from pathlib import Path
from typing import Optional, Dict

import cv2
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from aiohttp import web
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
import av

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from gripper_controller.CONController import CONController

# 環境変数
CAMERA_DEVICE = int(os.getenv("CAMERA_DEVICE", "0"))
GRIPPER_PORT = os.getenv("GRIPPER_PORT", "/dev/ttyUSB0")
GRIPPER_BAUDRATE = int(os.getenv("GRIPPER_BAUDRATE", "38400"))
GRIPPER_SLAVE_ADDR = int(os.getenv("GRIPPER_SLAVE_ADDR", "1"))

# FastAPIアプリ
app = FastAPI(title="自動組立ロボット制御 - WebRTC版")

# テンプレート
templates_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

# WebRTC関連
pcs = set()  # アクティブなRTCPeerConnection
shared_frame = {"frame": None, "lock": asyncio.Lock()}


class CameraVideoTrack(VideoStreamTrack):
    """WebRTC用カメラビデオトラック"""
    
    def __init__(self, device: int, width: int = 640, height: int = 480):
        super().__init__()
        self.device = device
        self.width = width
        self.height = height
        self.cap = None
        self._frame_count = 0
        
    async def recv(self):
        """フレーム取得"""
        pts, time_base = await self.next_timestamp()
        
        # 共有フレームから取得
        async with shared_frame["lock"]:
            frame = shared_frame.get("frame")
        
        if frame is None:
            # フォールバック: 黒画面
            frame = av.VideoFrame.from_ndarray(
                [[0, 0, 0] for _ in range(self.height)] * self.height,
                format="bgr24"
            )
        else:
            # NumPy配列からVideoFrameに変換
            frame = av.VideoFrame.from_ndarray(frame, format="bgr24")
        
        frame.pts = pts
        frame.time_base = time_base
        self._frame_count += 1
        
        return frame
    
    def stop(self):
        """トラック停止"""
        super().stop()


async def camera_frame_reader():
    """バックグラウンドでカメラフレームを読み取り"""
    cap = cv2.VideoCapture(CAMERA_DEVICE)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    try:
        while True:
            ret, frame = cap.read()
            if ret:
                async with shared_frame["lock"]:
                    shared_frame["frame"] = frame
            await asyncio.sleep(1/30)  # 30fps
    finally:
        cap.release()


# グリッパーコントローラー初期化
gripper: Optional[CONController] = None

try:
    gripper = CONController(
        port=GRIPPER_PORT,
        slave_address=GRIPPER_SLAVE_ADDR,
        baudrate=GRIPPER_BAUDRATE
    )
except Exception as e:
    print(f"⚠️  グリッパー接続失敗: {e}")


@app.on_event("startup")
async def startup_event():
    """起動時処理"""
    # カメラフレームリーダー起動
    asyncio.create_task(camera_frame_reader())
    print("🚀 Web UI起動完了 (WebRTC対応)")
    print(f"   カメラ: /dev/video{CAMERA_DEVICE}")
    print(f"   グリッパー: {GRIPPER_PORT} @ {GRIPPER_BAUDRATE}bps")


@app.on_event("shutdown")
async def shutdown_event():
    """終了時処理"""
    # WebRTC接続をクローズ
    coros = [pc.close() for pc in pcs]
    await asyncio.gather(*coros)
    pcs.clear()
    
    # グリッパークローズ
    if gripper:
        try:
            gripper.close()
        except:
            pass


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """メインページ"""
    return templates.TemplateResponse("index_webrtc.html", {"request": request})


# ============ WebRTC Signaling ============

@app.post("/api/webrtc/offer")
async def webrtc_offer(request: Request):
    """WebRTC Offer処理"""
    params = await request.json()
    offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])
    
    pc = RTCPeerConnection()
    pcs.add(pc)
    
    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        print(f"WebRTC状態: {pc.connectionState}")
        if pc.connectionState in ["failed", "closed"]:
            await pc.close()
            pcs.discard(pc)
    
    # ビデオトラック追加
    width = params.get("width", 640)
    height = params.get("height", 480)
    video_track = CameraVideoTrack(device=CAMERA_DEVICE, width=width, height=height)
    pc.addTrack(video_track)
    
    await pc.setRemoteDescription(offer)
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)
    
    return JSONResponse({
        "sdp": pc.localDescription.sdp,
        "type": pc.localDescription.type
    })


# ============ カメラAPI ============

@app.get("/api/camera/status")
async def camera_status():
    """カメラ状態取得"""
    try:
        cap = cv2.VideoCapture(CAMERA_DEVICE)
        if not cap.isOpened():
            return JSONResponse({"status": "error", "message": "カメラを開けません"}, status_code=500)
        
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        cap.release()
        
        return {
            "status": "ok",
            "device": CAMERA_DEVICE,
            "width": width,
            "height": height,
            "fps": fps
        }
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@app.get("/api/camera/controls")
async def camera_controls():
    """カメラ制御パラメータ一覧取得"""
    import subprocess
    try:
        result = subprocess.run(
            ["v4l2-ctl", f"--device=/dev/video{CAMERA_DEVICE}", "--list-ctrls"],
            capture_output=True, text=True, check=True
        )
        
        # パース処理 (簡易版)
        controls = {}
        for line in result.stdout.split('\n'):
            if 'min=' in line and 'max=' in line:
                parts = line.strip().split()
                if len(parts) > 0:
                    name = parts[0]
                    min_val = max_val = default_val = value = None
                    for part in parts:
                        if part.startswith('min='):
                            min_val = int(part.split('=')[1])
                        elif part.startswith('max='):
                            max_val = int(part.split('=')[1])
                        elif part.startswith('default='):
                            default_val = int(part.split('=')[1])
                        elif part.startswith('value='):
                            value = int(part.split('=')[1])
                    
                    if min_val is not None and max_val is not None:
                        controls[name] = {
                            "min": min_val,
                            "max": max_val,
                            "default": default_val,
                            "value": value
                        }
        
        return {"status": "ok", "controls": controls}
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@app.post("/api/camera/control/{control_name}/{value}")
async def set_camera_control(control_name: str, value: int):
    """カメラパラメータ設定"""
    import subprocess
    try:
        subprocess.run(
            ["v4l2-ctl", f"--device=/dev/video{CAMERA_DEVICE}", f"--set-ctrl={control_name}={value}"],
            check=True, capture_output=True
        )
        return {"status": "ok", "message": f"{control_name}を{value}に設定しました"}
    except subprocess.CalledProcessError as e:
        return JSONResponse({
            "status": "error", 
            "message": f"設定失敗: {e.stderr.decode()}"
        }, status_code=500)


# ============ グリッパーAPI ============

@app.get("/api/gripper/status")
async def gripper_status():
    """グリッパー状態取得"""
    if not gripper:
        return JSONResponse({"status": "error", "message": "グリッパー未接続"}, status_code=503)
    
    try:
        position = gripper.instrument.read_register(gripper.REG_CURRENT_POS, functioncode=3)
        alarm = gripper.instrument.read_register(gripper.REG_CURRENT_ALARM, functioncode=3)
        device_status = gripper.instrument.read_register(gripper.REG_DEVICE_STATUS, functioncode=3)
        servo_on = bool((device_status >> gripper.BIT_SERVO_READY) & 1)
        
        return {
            "status": "ok",
            "position": position,  # 0.01mm単位
            "position_mm": position * 0.01,  # mm表示
            "alarm": alarm,
            "servo_on": servo_on
        }
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@app.post("/api/gripper/servo/{action}")
async def gripper_servo(action: str):
    """グリッパーサーボON/OFF"""
    if not gripper:
        return JSONResponse({"status": "error", "message": "グリッパー未接続"}, status_code=503)
    
    try:
        if action == "on":
            gripper.instrument.write_register(gripper.REG_CONTROL, gripper.VAL_SERVO_ON, functioncode=6)
            return {"status": "ok", "message": "サーボON"}
        elif action == "off":
            gripper.instrument.write_register(gripper.REG_CONTROL, 0x0000, functioncode=6)
            return {"status": "ok", "message": "サーボOFF"}
        else:
            return JSONResponse({"status": "error", "message": "無効なアクション"}, status_code=400)
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@app.post("/api/gripper/home")
async def gripper_home():
    """グリッパー原点復帰"""
    if not gripper:
        return JSONResponse({"status": "error", "message": "グリッパー未接続"}, status_code=503)
    
    try:
        gripper.instrument.write_register(gripper.REG_CONTROL, gripper.VAL_HOME, functioncode=6)
        # 原点復帰完了待機 (簡易版)
        await asyncio.sleep(3)
        return {"status": "ok", "message": "原点復帰完了"}
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@app.post("/api/gripper/move/{position}")
async def gripper_move(position: int):
    """グリッパー位置決め"""
    if not gripper:
        return JSONResponse({"status": "error", "message": "グリッパー未接続"}, status_code=503)
    
    # 範囲チェック (0-99)
    if not (0 <= position <= 99):
        return JSONResponse({
            "status": "error", 
            "message": f"無効なポジション: {position} (0-99の範囲で指定してください)"
        }, status_code=400)
    
    try:
        # ポジション指定
        gripper.instrument.write_register(gripper.REG_POS_SELECT, position, functioncode=6)
        # 位置決め起動
        gripper.instrument.write_register(gripper.REG_CONTROL, gripper.VAL_START, functioncode=6)
        # 移動完了待機 (簡易版)
        await asyncio.sleep(2)
        return {"status": "ok", "message": f"ポジション{position}へ移動完了"}
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

