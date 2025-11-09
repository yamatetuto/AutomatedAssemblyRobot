"""
カメラ管理モジュール
OpenCVを使ったカメラキャプチャと制御を提供
"""
import cv2
import asyncio
import re
import subprocess
from typing import Optional, Dict, List
from datetime import datetime
from pathlib import Path
import logging

from src.config.settings import (
    CAMERA_DEVICE, CAMERA_WIDTH, CAMERA_HEIGHT, 
    CAMERA_FPS, CAMERA_FOURCC, SNAPSHOTS_DIR
)

logger = logging.getLogger(__name__)


class CameraManager:
    """カメラ管理クラス"""
    
    def __init__(self):
        self.camera: Optional[cv2.VideoCapture] = None
        self.current_frame: Optional[object] = None
        self.is_running = False
        self.capture_task: Optional[asyncio.Task] = None
        
        # カメラ設定
        self.settings = {
            "width": CAMERA_WIDTH,
            "height": CAMERA_HEIGHT,
            "fps": CAMERA_FPS,
            "fourcc": CAMERA_FOURCC
        }
    
    async def start(self):
        """カメラキャプチャを開始"""
        if self.is_running:
            logger.warning("カメラは既に起動しています")
            return
        
        self.is_running = True
        self.capture_task = asyncio.create_task(self._capture_loop())
        logger.info(f"カメラキャプチャを開始: device={CAMERA_DEVICE}, "
                   f"{self.settings['width']}x{self.settings['height']}@{self.settings['fps']}fps")
    
    async def stop(self):
        """カメラキャプチャを停止"""
        self.is_running = False
        if self.capture_task:
            self.capture_task.cancel()
            try:
                await self.capture_task
            except asyncio.CancelledError:
                pass
        
        if self.camera:
            self.camera.release()
            self.camera = None
        logger.info("カメラキャプチャを停止しました")
    
    async def _capture_loop(self):
        """カメラキャプチャループ（内部メソッド）"""
        try:
            while self.is_running:
                # カメラが未接続または切断された場合、再接続を試行
                if self.camera is None or not self.camera.isOpened():
                    logger.info(f"カメラ接続中: /dev/video{CAMERA_DEVICE}")
                    # V4L2バックエンドを明示的に指定
                    self.camera = cv2.VideoCapture(CAMERA_DEVICE, cv2.CAP_V4L2)
                    
                    # フォーマット設定を先に行う (MJPEG)
                    fourcc = cv2.VideoWriter_fourcc(*self.settings["fourcc"])
                    self.camera.set(cv2.CAP_PROP_FOURCC, fourcc)
                    
                    # バッファサイズを1に設定（遅延最小化、高解像度対応）
                    self.camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    
                    # 解像度とFPS設定
                    width = self.settings["width"]
                    height = self.settings["height"]
                    fps = self.settings["fps"]
                    
                    # 高解像度時はFPSを自動調整（CPU負荷軽減）
                    if width >= 1920:
                        fps = min(fps, 15)  # 1920x1080: 最大15fps
                        logger.info(f"高解像度モード: FPSを{fps}に制限")
                    elif width >= 1280:
                        fps = min(fps, 20)  # 1280x720: 最大20fps
                    
                    self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, width)
                    self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
                    self.camera.set(cv2.CAP_PROP_FPS, fps)
                    
                    if self.camera.isOpened():
                        actual_w = int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH))
                        actual_h = int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
                        actual_fps = self.camera.get(cv2.CAP_PROP_FPS)
                        logger.info(f"✅ カメラ接続成功: {actual_w}x{actual_h} @ {actual_fps}fps")
                    else:
                        logger.error(f"カメラを開けませんでした: /dev/video{CAMERA_DEVICE}")
                        await asyncio.sleep(5)  # 5秒待ってリトライ
                        continue
                
                # フレーム取得
                ret, frame = self.camera.read()
                if ret:
                    self.current_frame = frame
                else:
                    logger.warning("フレーム取得失敗")
                    self.camera = None  # 再接続を促す
                
                await asyncio.sleep(1 / self.settings["fps"])
        
        except asyncio.CancelledError:
            logger.info("カメラキャプチャループが停止されました")
        except Exception as e:
            logger.error(f"カメラキャプチャエラー: {e}")
    
    def get_frame(self) -> Optional[object]:
        """現在のフレームを取得"""
        return self.current_frame
    
    def is_opened(self) -> bool:
        """カメラが開いているか確認"""
        return self.camera is not None and self.camera.isOpened()
    
    async def take_snapshot(self) -> Optional[Dict[str, str]]:
        """スナップショットを撮影"""
        if self.current_frame is None:
            logger.error("フレームが利用できません")
            return None
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"snapshot_{timestamp}.jpg"
        filepath = SNAPSHOTS_DIR / filename
        
        # ディレクトリが存在しない場合は作成
        SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        
        success = cv2.imwrite(str(filepath), self.current_frame)
        if success:
            logger.info(f"スナップショット保存: {filename}")
            return {
                "status": "ok",
                "message": f"スナップショットを保存しました: {filename}",
                "filename": filename,
                "timestamp": timestamp,
                "path": str(filepath)
            }
        else:
            logger.error(f"スナップショット保存失敗: {filename}")
            return None
    
    def get_controls(self) -> Dict:
        """カメラコントロール一覧を取得（v4l2-ctl使用、int/bool/menu対応）"""
        if not self.is_opened():
            raise RuntimeError("カメラが接続されていません")
        
        try:
            result = subprocess.run(
                ['v4l2-ctl', '-d', f'/dev/video{CAMERA_DEVICE}', '-L'],
                capture_output=True,
                text=True,
                check=True,
                timeout=5
            )
            
            controls = {}
            current_control_name = None
            
            for line in result.stdout.splitlines():
                # セクションヘッダーをスキップ
                if line.strip() in ('User Controls', 'Camera Controls', 'Codec Controls'):
                    continue
                
                # 整数型コントロールをパース
                int_match = re.match(
                    r'\s*(\S+)\s+0x[0-9a-f]+\s+\(int\)\s*:\s*min=(-?\d+)\s+max=(-?\d+)\s+step=(\d+)\s+default=(-?\d+)\s+value=(-?\d+)',
                    line
                )
                if int_match:
                    name, min_val, max_val, step, default, value = int_match.groups()
                    current_control_name = name
                    controls[name] = {
                        'type': 'int',
                        'min': int(min_val),
                        'max': int(max_val),
                        'step': int(step),
                        'default': int(default),
                        'value': int(value)
                    }
                    continue
                
                # menu型コントロールをパース
                menu_match = re.match(
                    r'\s*(\S+)\s+0x[0-9a-f]+\s+\(menu\)\s*:\s*min=(\d+)\s+max=(\d+)\s+default=(\d+)\s+value=(\d+)',
                    line
                )
                if menu_match:
                    name, min_val, max_val, default, value = menu_match.groups()
                    current_control_name = name
                    controls[name] = {
                        'type': 'menu',
                        'min': int(min_val),
                        'max': int(max_val),
                        'step': 1,
                        'default': int(default),
                        'value': int(value),
                        'options': {}
                    }
                    continue
                
                # bool型コントロールをパース
                bool_match = re.match(
                    r'\s*(\S+)\s+0x[0-9a-f]+\s+\(bool\)\s*:\s*default=([01])\s+value=([01])',
                    line
                )
                if bool_match:
                    name, default, value = bool_match.groups()
                    current_control_name = name
                    controls[name] = {
                        'type': 'bool',
                        'min': 0,
                        'max': 1,
                        'step': 1,
                        'default': int(default),
                        'value': int(value)
                    }
                    continue
                
                # メニューオプション行をパース
                menu_opt_match = re.match(r'^\s+(\d+):\s+(.+)$', line)
                if menu_opt_match and current_control_name:
                    ctrl = controls.get(current_control_name)
                    if ctrl and ctrl.get('type') == 'menu' and 'options' in ctrl:
                        idx, label = menu_opt_match.groups()
                        ctrl['options'][int(idx)] = label.strip()
            
            return controls
        except Exception as e:
            logger.error(f"コントロール取得エラー: {e}")
            raise
    def set_control(self, name: str, value: int):
        """カメラコントロールを設定"""
        if not self.is_opened():
            raise RuntimeError("カメラが接続されていません")
        
        try:
            subprocess.run(
                ['v4l2-ctl', '-d', f'/dev/video{CAMERA_DEVICE}', '--set-ctrl', f'{name}={value}'],
                check=True,
                capture_output=True
            )
            logger.info(f"カメラコントロール設定: {name}={value}")
        except subprocess.CalledProcessError as e:
            logger.error(f"コントロール設定エラー: {e}")
            raise
    
    async def update_settings(self, width: int, height: int, fps: int):
        """解像度とFPSを更新（再起動が必要）"""
        self.settings["width"] = width
        self.settings["height"] = height
        self.settings["fps"] = fps
        
        # カメラを再起動
        await self.stop()
        await self.start()
        logger.info(f"解像度変更: {width}x{height}@{fps}fps")
