#!/usr/bin/env python3
"""
統合Web UI - WebRTC対応版 (camera_controller方式採用)
- WebRTC低遅延ストリーミング (shared_frame方式)
- カメラパラメータ調整
- グリッパーポジションテーブル詳細表示・編集
- スナップショット機能
"""
import os
import sys
import asyncio
import json
import traceback
import datetime
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
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

# スナップショットディレクトリ
SNAPSHOT_DIR = PROJECT_ROOT / "snapshots"
SNAPSHOT_DIR.mkdir(exist_ok=True)

# FastAPIアプリ
app = FastAPI(title="自動組立ロボット制御 - WebRTC版")

# テンプレート
templates_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

# WebRTC関連 (shared_frame方式)
pcs = set()
shared_frame = {"frame": None}
camera_capture = None
frame_reader_task = None

camera_settings = {
    "width": 640,
    "height": 480,
    "fps": 30,
    "fourcc": "MJPG"
}


class CameraVideoTrack(VideoStreamTrack):
    """camera_controller方式のVideoTrack (shared_frame使用)"""
    
    kind = "video"
    
    def __init__(self, device: int, width: int = 640, height: int = 480):
        super().__init__()
        self.device = device
        self.width = width
        self.height = height
        self._frame_count = 0
        print(f"🎥 CameraVideoTrack初期化: {width}x{height}")
        
    async def recv(self):
        """フレーム取得 (shared_frameから)"""
        if self._frame_count == 0:
            print(f"🎬 recv() 初回呼び出し: VideoTrack開始")
        
        if self._frame_count % 10 == 0:
            print(f"📞 recv() 呼び出し: count={self._frame_count}")
        
        pts, time_base = await self.next_timestamp()
        
        # shared_frameから取得
        frame = shared_frame.get("frame")
        
        # フレームが取得できるまで待機
        retry_count = 0
        while frame is None and retry_count < 100:
            await asyncio.sleep(0.01)
            frame = shared_frame.get("frame")
            retry_count += 1
        
        if frame is None or not isinstance(frame, np.ndarray):
            # フォールバック: 黒画面
            frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
            if self._frame_count % 30 == 0:
                print(f"⚫ フレーム未取得: 黒画面を送信 (count={self._frame_count})")
        else:
            # コピーして使用
            frame = frame.copy()
            
            # リサイズが必要な場合
            if frame.shape[0] != self.height or frame.shape[1] != self.width:
                frame = cv2.resize(frame, (self.width, self.height))
            
            if self._frame_count % 30 == 0:
                print(f"📹 フレーム送信: {frame.shape} (count={self._frame_count})")
        
        # av.VideoFrameに変換
        try:
            video_frame = av.VideoFrame.from_ndarray(frame, format="bgr24")
            video_frame.pts = pts
            video_frame.time_base = time_base
            self._frame_count += 1
            
            if self._frame_count % 30 == 0:
                print(f"✅ VideoFrame作成成功: {video_frame.width}x{video_frame.height}, pts={pts}")
            
            return video_frame
        except Exception as e:
            print(f"❌ VideoFrame作成エラー: {e}")
            traceback.print_exc()
            raise


async def camera_frame_reader():
    """バックグラウンドでカメラフレームを読み取り (camera_controller方式)"""
    global camera_capture
    
    loop = asyncio.get_event_loop()
    frame_count = 0
    
    print(f"📷 カメラフレームリーダー起動: /dev/video{CAMERA_DEVICE}")
    
    while True:
        try:
            if camera_capture is None or not camera_capture.isOpened():
                print(f"📷 カメラ接続中: /dev/video{CAMERA_DEVICE}")
                camera_capture = cv2.VideoCapture(CAMERA_DEVICE)
                
                # カメラ設定を反映
                camera_capture.set(cv2.CAP_PROP_FRAME_WIDTH, camera_settings["width"])
                camera_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, camera_settings["height"])
                camera_capture.set(cv2.CAP_PROP_FPS, camera_settings["fps"])
                
                # フォーマット設定 (MJPEG)
                fourcc = cv2.VideoWriter_fourcc(*camera_settings["fourcc"])
                camera_capture.set(cv2.CAP_PROP_FOURCC, fourcc)
                
                if camera_capture.isOpened():
                    actual_w = int(camera_capture.get(cv2.CAP_PROP_FRAME_WIDTH))
                    actual_h = int(camera_capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    actual_fps = camera_capture.get(cv2.CAP_PROP_FPS)
                    print(f"✅ カメラ接続成功: {actual_w}x{actual_h} @ {actual_fps}fps")
                else:
                    print("❌ カメラ接続失敗")
                    await asyncio.sleep(1)
                    continue
            
            # フレーム読み取り (非同期実行)
            try:
                ret, frame = await loop.run_in_executor(None, camera_capture.read)
            except Exception as e:
                print(f"⚠️ フレーム読み取りエラー: {e}")
                ret = False
                frame = None
            
            if ret and frame is not None:
                # shared_frameに保存
                shared_frame["frame"] = frame
                frame_count += 1
                
                if frame_count % 100 == 0:
                    print(f"📸 カメラフレーム取得: {frame.shape} (count={frame_count})")
            else:
                print("⚠️ カメラフレーム取得失敗: カメラを再接続します")
                if camera_capture:
                    camera_capture.release()
                camera_capture = None
                await asyncio.sleep(1)
                continue
            
            # 次のフレームまで待機
            await asyncio.sleep(0)  # イベントループに制御を戻す
            
        except asyncio.CancelledError:
            print("📷 カメラフレームリーダー停止")
            break
        except Exception as e:
            print(f"❌ カメラエラー: {e}")
            traceback.print_exc()
            if camera_capture:
                camera_capture.release()
            camera_capture = None
            await asyncio.sleep(1)


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
    global frame_reader_task
    
    # カメラフレームリーダー起動
    frame_reader_task = asyncio.create_task(camera_frame_reader())
    
    print("🚀 Web UI起動完了 (WebRTC対応 - camera_controller方式)")
    print(f"   カメラ: /dev/video{CAMERA_DEVICE}")
    print(f"   グリッパー: {GRIPPER_PORT} @ {GRIPPER_BAUDRATE}bps")
    print(f"   スナップショット: {SNAPSHOT_DIR}")


@app.on_event("shutdown")
async def shutdown_event():
    """終了時処理"""
    global frame_reader_task, camera_capture
    
    # フレームリーダー停止
    if frame_reader_task:
        frame_reader_task.cancel()
        try:
            await frame_reader_task
        except asyncio.CancelledError:
            pass
    
    # カメラクローズ
    if camera_capture:
        try:
            camera_capture.release()
        except:
            pass
    
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
    return templates.TemplateResponse("index_webrtc_fixed.html", {"request": request})


# ============ WebRTC Signaling ============

@app.post("/api/webrtc/offer")
async def webrtc_offer(request: Request):
    """WebRTC Offer処理 (camera_controller方式)"""
    try:
        params = await request.json()
        offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])
        
        pc = RTCPeerConnection()
        pcs.add(pc)
        print(f"🔗 WebRTC接続数: {len(pcs)}")
        
        @pc.on("connectionstatechange")
        async def on_connectionstatechange():
            print(f"📡 WebRTC状態変化: {pc.connectionState}")
            if pc.connectionState in ["failed", "closed"]:
                await pc.close()
                pcs.discard(pc)
        
        @pc.on("iceconnectionstatechange")
        async def on_iceconnectionstatechange():
            print(f"🧊 ICE接続状態変化: {pc.iceConnectionState}")
        
        @pc.on("track")
        def on_track(track):
            print(f"🎵 Track追加: kind={track.kind}, id={track.id}")
        
        # リモートDescriptionを設定
        await pc.setRemoteDescription(offer)
        print(f"📥 Offer受信: {len(offer.sdp)} bytes")
        
        # 解像度取得
        width = params.get("width", camera_settings["width"])
        height = params.get("height", camera_settings["height"])
        print(f"🎬 要求解像度: {width}x{height}")
        
        # transceiverの状態をデバッグ
        transceivers = pc.getTransceivers()
        print(f"🔍 Transceiver数: {len(transceivers)}")
        for i, transceiver in enumerate(transceivers):
            print(f"  [{i}] kind={transceiver.kind}, direction={transceiver.direction}, mid={transceiver.mid}")
        
        # 既存のtransceiverにカメラトラックを割り当て
        video_track_set = False
        for transceiver in transceivers:
            if transceiver.kind == "video":
                video_track = CameraVideoTrack(device=CAMERA_DEVICE, width=width, height=height)
                print(f"🎥 VideoTrack作成: {video_track}, kind={video_track.kind}")
                
                # transceiverのdirectionをsendonlyに設定（サーバーは送信のみ）
                transceiver.direction = "sendonly"
                
                transceiver.sender.replaceTrack(video_track)
                print(f"✅ ビデオトラック設定完了: {width}x{height}, direction={transceiver.direction}")
                print(f"   sender={transceiver.sender}, sender.track={transceiver.sender.track}")
                video_track_set = True
        
        if not video_track_set:
            print("⚠️ ビデオtransceiverが見つかりません!")
        
        # Answerを作成
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)
        print(f"📤 Answer送信: {len(answer.sdp)} bytes")
        
        return JSONResponse({
            "sdp": pc.localDescription.sdp,
            "type": pc.localDescription.type
        })
    except Exception as e:
        error_detail = traceback.format_exc()
        print(f"❌ WebRTC Offer エラー:\n{error_detail}")
        return JSONResponse({
            "status": "error",
            "message": str(e),
            "detail": error_detail
        }, status_code=500)


# ============ カメラAPI ============

@app.get("/api/camera/status")
async def camera_status():
    """カメラ状態取得"""
    try:
        if camera_capture and camera_capture.isOpened():
            width = int(camera_capture.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(camera_capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = camera_capture.get(cv2.CAP_PROP_FPS)
            
            return {
                "status": "ok",
                "device": CAMERA_DEVICE,
                "width": width,
                "height": height,
                "fps": fps,
                "current_settings": camera_settings,
                "has_frame": shared_frame.get("frame") is not None
            }
        else:
            return JSONResponse({
                "status": "error",
                "message": "カメラ未接続"
            }, status_code=503)
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@app.get("/api/camera/resolutions")
async def camera_resolutions():
    """カメラ対応解像度一覧"""
    common_resolutions = [
        {"width": 320, "height": 240, "label": "QVGA (320x240)"},
        {"width": 640, "height": 480, "label": "VGA (640x480)"},
        {"width": 800, "height": 600, "label": "SVGA (800x600)"},
        {"width": 1280, "height": 720, "label": "HD (1280x720)"},
        {"width": 1920, "height": 1080, "label": "Full HD (1920x1080)"},
    ]
    
    return {
        "status": "ok",
        "resolutions": common_resolutions,
        "current": camera_settings
    }


@app.post("/api/camera/resolution")
async def set_camera_resolution(request: Request):
    """カメラ解像度変更"""
    global camera_capture
    
    try:
        params = await request.json()
        width = params.get("width")
        height = params.get("height")
        fps = params.get("fps", 30)
        
        if width and height:
            camera_settings["width"] = width
            camera_settings["height"] = height
            camera_settings["fps"] = fps
            
            # カメラ再起動
            if camera_capture:
                camera_capture.release()
                camera_capture = None
            
            return {
                "status": "ok",
                "message": f"解像度を{width}x{height}に変更しました",
                "settings": camera_settings
            }
        else:
            return JSONResponse({
                "status": "error",
                "message": "widthとheightが必要です"
            }, status_code=400)
            
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
        
        # パース処理
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
        return {"status": "ok"}
    except subprocess.CalledProcessError as e:
        return JSONResponse({
            "status": "error", 
            "message": f"設定失敗: {e.stderr.decode()}"
        }, status_code=500)


@app.post("/api/camera/codec")
async def change_codec(request: Request):
    """カメラコーデック変更"""
    global camera_capture, frame_reader_task
    
    data = await request.json()
    codec = data.get("codec", "MJPG")
    
    if codec not in ["MJPG", "YUYV"]:
        return JSONResponse({
            "status": "error",
            "message": "サポートされていないコーデックです"
        }, status_code=400)
    
    try:
        # カメラ設定を更新
        camera_settings["fourcc"] = codec
        fourcc = cv2.VideoWriter_fourcc(*codec)
        
        # カメラを再初期化
        if camera_capture:
            camera_capture.release()
            camera_capture = None
        
        # 既存のフレームリーダータスクをキャンセル
        if frame_reader_task and not frame_reader_task.done():
            frame_reader_task.cancel()
            try:
                await frame_reader_task
            except asyncio.CancelledError:
                pass
        
        # カメラを再オープン
        camera_capture = cv2.VideoCapture(0, cv2.CAP_V4L2)
        camera_capture.set(cv2.CAP_PROP_FOURCC, fourcc)
        camera_capture.set(cv2.CAP_PROP_FRAME_WIDTH, camera_settings["width"])
        camera_capture.set(cv2.CAP_PROP_FRAME_HEIGHT, camera_settings["height"])
        
        if not camera_capture.isOpened():
            return JSONResponse({
                "status": "error",
                "message": "カメラの再初期化に失敗しました"
            }, status_code=500)
        
        # フレームリーダータスクを再起動
        frame_reader_task = asyncio.create_task(camera_frame_reader())
        
        return {
            "status": "ok",
            "message": f"コーデックを{codec}に変更しました"
        }
    except Exception as e:
        return JSONResponse({
            "status": "error",
            "message": f"コーデック変更失敗: {str(e)}"
        }, status_code=500)


@app.post("/api/camera/snapshot")
async def take_snapshot():
    """スナップショット撮影"""
    try:
        frame = shared_frame.get("frame")
        
        if frame is None:
            return JSONResponse({
                "status": "error",
                "message": "フレームが取得できません"
            }, status_code=503)
        
        # ファイル名生成
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"snapshot_{timestamp}.jpg"
        filepath = SNAPSHOT_DIR / filename
        
        # 保存
        cv2.imwrite(str(filepath), frame)
        
        return {
            "status": "ok",
            "filename": filename,
            "path": str(filepath),
            "message": f"スナップショット保存: {filename}"
        }
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@app.get("/api/camera/snapshots")
async def list_snapshots():
    """スナップショット一覧"""
    try:
        files = sorted(SNAPSHOT_DIR.glob("snapshot_*.jpg"), reverse=True)
        snapshots = [
            {
                "filename": f.name,
                "path": str(f),
                "size": f.stat().st_size,
                "timestamp": f.stat().st_mtime
            }
            for f in files[:20]  # 最新20件
        ]
        
        return {
            "status": "ok",
            "snapshots": snapshots
        }
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@app.get("/api/camera/snapshot/{filename}")
async def get_snapshot(filename: str):
    """スナップショット取得"""
    filepath = SNAPSHOT_DIR / filename
    
    if not filepath.exists() or not filepath.is_file():
        return JSONResponse({
            "status": "error",
            "message": "ファイルが見つかりません"
        }, status_code=404)
    
    return FileResponse(filepath)


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
            "position": position,
            "position_mm": position * 0.01,
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
            gripper.servo_on()
            return {"status": "ok"}
        elif action == "off":
            gripper.servo_off()
            return {"status": "ok"}
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
        gripper.home()
        return {"status": "ok"}
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@app.post("/api/gripper/move/{position}")
async def gripper_move(position: int):
    """グリッパー位置決め"""
    if not gripper:
        return JSONResponse({"status": "error", "message": "グリッパー未接続"}, status_code=503)
    
    if not (0 <= position <= 63):
        return JSONResponse({
            "status": "error", 
            "message": f"無効なポジション: {position}"
        }, status_code=400)
    
    try:
        gripper.move_to_pos(position)
        return {"status": "ok"}
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@app.get("/api/gripper/position_table/{position}")
async def get_position_data(position: int):
    """ポジションテーブルデータ取得"""
    if not gripper:
        return JSONResponse({"status": "error", "message": "グリッパー未接続"}, status_code=503)
    
    if not (0 <= position <= 63):
        return JSONResponse({"status": "error", "message": "無効なポジション"}, status_code=400)
    
    try:
        data = gripper.get_position_data(position)
        return {"status": "ok", "position": position, "data": data}
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@app.post("/api/gripper/position_table/{position}")
async def set_position_data(position: int, request: Request):
    """ポジションテーブルデータ設定"""
    if not gripper:
        return JSONResponse({"status": "error", "message": "グリッパー未接続"}, status_code=503)
    
    if not (0 <= position <= 63):
        return JSONResponse({"status": "error", "message": "無効なポジション"}, status_code=400)
    
    try:
        data = await request.json()
        gripper.set_position_data(
            position,
            target_position=data.get("target_position"),
            positioning_speed=data.get("positioning_speed"),
            moving_force=data.get("moving_force"),
            gripping_speed=data.get("gripping_speed"),
            gripping_force=data.get("gripping_force"),
            gripping_width=data.get("gripping_width"),
            area_1=data.get("area_1")
        )
        return {"status": "ok", "message": f"ポジション{position}のデータを設定しました"}
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
