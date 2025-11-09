#!/usr/bin/env python3
"""
自動組立ロボット WebUI
カメラとグリッパーの操作インターフェース
"""
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
import sys
import os
import cv2
import time

# パスを追加
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gripper_controller.CONController import CONController

app = FastAPI(title="自動組立ロボット制御システム")

# グリッパーの設定
GRIPPER_PORT = os.getenv("GRIPPER_PORT", "/dev/ttyUSB0")
GRIPPER_SLAVE_ADDRESS = int(os.getenv("GRIPPER_SLAVE_ADDRESS", "1"))
GRIPPER_BAUDRATE = int(os.getenv("GRIPPER_BAUDRATE", "38400"))

# グリッパーインスタンス（遅延初期化）
gripper = None

def get_gripper():
    """グリッパーインスタンスを取得"""
    global gripper
    if gripper is None:
        try:
            gripper = CONController(GRIPPER_PORT, GRIPPER_SLAVE_ADDRESS, GRIPPER_BAUDRATE)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"グリッパー接続エラー: {e}")
    return gripper

def generate_frames():
    """カメラフレームを生成"""
    camera = cv2.VideoCapture(0)
    try:
        while True:
            success, frame = camera.read()
            if not success:
                break
            
            # JPEG形式にエンコード
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            
            # ストリーミング形式で返す
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            
            time.sleep(0.033)  # 約30fps
    finally:
        camera.release()

@app.get("/", response_class=HTMLResponse)
async def index():
    """メインページ"""
    with open("web_app/templates/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(content=f.read())

@app.get("/api/camera/stream")
async def camera_stream():
    """カメラストリーム"""
    return StreamingResponse(
        generate_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

@app.get("/api/camera/status")
async def camera_status():
    """カメラ状態取得"""
    try:
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            return {"status": "error", "message": "カメラが開けません"}
        
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        cap.release()
        
        return {
            "status": "ok",
            "width": width,
            "height": height,
            "fps": fps
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/gripper/status")
async def gripper_status():
    """グリッパー状態取得"""
    try:
        g = get_gripper()
        
        current_pos = g.instrument.read_register(g.REG_CURRENT_POS, functioncode=3)
        alarm = g.instrument.read_register(g.REG_CURRENT_ALARM, functioncode=3)
        status = g.instrument.read_register(g.REG_DEVICE_STATUS, functioncode=3)
        servo_on = (status >> g.BIT_SERVO_READY) & 1
        
        return {
            "status": "ok",
            "position": current_pos,
            "alarm": alarm,
            "servo_on": bool(servo_on),
            "device_status": status
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/gripper/servo/{action}")
async def gripper_servo(action: str):
    """サーボON/OFF"""
    try:
        g = get_gripper()
        
        if action == "on":
            g.instrument.write_register(g.REG_CONTROL, g.VAL_SERVO_ON, functioncode=6)
            return {"status": "ok", "message": "サーボON"}
        elif action == "off":
            g.instrument.write_register(g.REG_CONTROL, 0x0000, functioncode=6)
            return {"status": "ok", "message": "サーボOFF"}
        else:
            raise HTTPException(status_code=400, detail="無効なアクション")
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/gripper/home")
async def gripper_home():
    """原点復帰"""
    try:
        g = get_gripper()
        g.instrument.write_register(g.REG_CONTROL, g.VAL_HOME, functioncode=6)
        
        # 完了待ち
        if g.wait_for_status_bit(g.REG_DEVICE_STATUS, g.BIT_HOME_END, expected_state=1, timeout=15):
            return {"status": "ok", "message": "原点復帰完了"}
        else:
            return {"status": "error", "message": "原点復帰タイムアウト"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.post("/api/gripper/move/{position}")
async def gripper_move(position: int):
    """位置決め動作"""
    try:
        g = get_gripper()
        
        # ポジション番号を設定
        g.instrument.write_register(g.REG_POS_SELECT, position, functioncode=6)
        
        # 位置決め起動
        g.instrument.write_register(g.REG_CONTROL, g.VAL_START, functioncode=6)
        
        # 完了待ち
        if g.wait_for_motion_to_stop(timeout=10):
            return {"status": "ok", "message": f"位置{position}へ移動完了"}
        else:
            return {"status": "error", "message": "移動タイムアウト"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
