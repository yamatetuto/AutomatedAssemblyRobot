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
        """
        カメラコントロール一覧を取得（v4l2-ctl使用、全型対応）
        
        対応する型:
        - int: 整数値（min/max/step/default/value）
        - bool: ブール値（0/1）
        - menu: メニュー選択（オプション一覧付き）
        - int64: 64bit整数値
        - button: ボタン（値なし）
        - bitmask: ビットマスク
        
        Returns:
            Dict: {
                'control_name': {
                    'type': 'int' | 'bool' | 'menu' | ...,
                    'min': int,
                    'max': int,
                    'step': int,
                    'default': int,
                    'value': int,
                    'flags': str,  # 'inactive', 'grabbed', 'disabled' など
                    'options': Dict[int, str]  # menu型の場合
                }
            }
        """
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
            current_section = None
            
            for line in result.stdout.splitlines():
                # セクションヘッダーを記録
                if line.strip() in ('User Controls', 'Camera Controls', 'Codec Controls', 
                                    'JPEG Compression Controls', 'Image Processing Controls',
                                    'Image Source Controls'):
                    current_section = line.strip()
                    continue
                
                # 空行をスキップ
                if not line.strip():
                    continue
                
                # 整数型コントロール (int)
                int_match = re.match(
                    r'\s*(\S+)\s+0x([0-9a-f]+)\s+\(int\)\s*:\s*min=(-?\d+)\s+max=(-?\d+)\s+step=(\d+)\s+default=(-?\d+)\s+value=(-?\d+)(?:\s+flags=(.+))?',
                    line
                )
                if int_match:
                    name, ctrl_id, min_val, max_val, step, default, value, flags = int_match.groups()
                    current_control_name = name
                    controls[name] = {
                        'type': 'int',
                        'id': f'0x{ctrl_id}',
                        'min': int(min_val),
                        'max': int(max_val),
                        'step': int(step),
                        'default': int(default),
                        'value': int(value),
                        'flags': flags or '',
                        'section': current_section
                    }
                    continue
                
                # 64bit整数型コントロール (int64)
                int64_match = re.match(
                    r'\s*(\S+)\s+0x([0-9a-f]+)\s+\(int64\)\s*:\s*min=(-?\d+)\s+max=(-?\d+)\s+step=(\d+)\s+default=(-?\d+)\s+value=(-?\d+)(?:\s+flags=(.+))?',
                    line
                )
                if int64_match:
                    name, ctrl_id, min_val, max_val, step, default, value, flags = int64_match.groups()
                    current_control_name = name
                    controls[name] = {
                        'type': 'int64',
                        'id': f'0x{ctrl_id}',
                        'min': int(min_val),
                        'max': int(max_val),
                        'step': int(step),
                        'default': int(default),
                        'value': int(value),
                        'flags': flags or '',
                        'section': current_section
                    }
                    continue
                
                # menu型コントロール
                menu_match = re.match(
                    r'\s*(\S+)\s+0x([0-9a-f]+)\s+\(menu\)\s*:\s*min=(\d+)\s+max=(\d+)\s+default=(\d+)\s+value=(\d+)(?:\s+flags=(.+))?',
                    line
                )
                if menu_match:
                    name, ctrl_id, min_val, max_val, default, value, flags = menu_match.groups()
                    current_control_name = name
                    controls[name] = {
                        'type': 'menu',
                        'id': f'0x{ctrl_id}',
                        'min': int(min_val),
                        'max': int(max_val),
                        'step': 1,
                        'default': int(default),
                        'value': int(value),
                        'flags': flags or '',
                        'options': {},
                        'section': current_section
                    }
                    continue
                
                # bool型コントロール
                bool_match = re.match(
                    r'\s*(\S+)\s+0x([0-9a-f]+)\s+\(bool\)\s*:\s*default=([01])\s+value=([01])(?:\s+flags=(.+))?',
                    line
                )
                if bool_match:
                    name, ctrl_id, default, value, flags = bool_match.groups()
                    current_control_name = name
                    controls[name] = {
                        'type': 'bool',
                        'id': f'0x{ctrl_id}',
                        'min': 0,
                        'max': 1,
                        'step': 1,
                        'default': int(default),
                        'value': int(value),
                        'flags': flags or '',
                        'section': current_section
                    }
                    continue
                
                # button型コントロール
                button_match = re.match(
                    r'\s*(\S+)\s+0x([0-9a-f]+)\s+\(button\)\s*(?:\s+flags=(.+))?',
                    line
                )
                if button_match:
                    name, ctrl_id, flags = button_match.groups()
                    current_control_name = name
                    controls[name] = {
                        'type': 'button',
                        'id': f'0x{ctrl_id}',
                        'flags': flags or '',
                        'section': current_section
                    }
                    continue
                
                # bitmask型コントロール
                bitmask_match = re.match(
                    r'\s*(\S+)\s+0x([0-9a-f]+)\s+\(bitmask\)\s*:\s*max=0x([0-9a-f]+)\s+default=0x([0-9a-f]+)\s+value=0x([0-9a-f]+)(?:\s+flags=(.+))?',
                    line
                )
                if bitmask_match:
                    name, ctrl_id, max_val, default, value, flags = bitmask_match.groups()
                    current_control_name = name
                    controls[name] = {
                        'type': 'bitmask',
                        'id': f'0x{ctrl_id}',
                        'min': 0,
                        'max': int(max_val, 16),
                        'default': int(default, 16),
                        'value': int(value, 16),
                        'flags': flags or '',
                        'section': current_section
                    }
                    continue
                
                # メニューオプション行をパース
                menu_opt_match = re.match(r'^\s+(\d+):\s+(.+)$', line)
                if menu_opt_match and current_control_name:
                    ctrl = controls.get(current_control_name)
                    if ctrl and ctrl.get('type') == 'menu' and 'options' in ctrl:
                        idx, label = menu_opt_match.groups()
                        ctrl['options'][int(idx)] = label.strip()
            
            logger.info(f"カメラコントロール取得: {len(controls)}個")
            return controls
        
        except subprocess.CalledProcessError as e:
            logger.error(f"v4l2-ctlコマンド実行エラー: {e.stderr}")
            raise RuntimeError(f"カメラコントロール取得失敗: {e.stderr}")
        except FileNotFoundError:
            logger.error("v4l2-ctlコマンドが見つかりません。v4l-utilsをインストールしてください。")
            raise RuntimeError("v4l2-ctlコマンドが見つかりません")
        except Exception as e:
            logger.error(f"コントロール取得エラー: {e}")
            raise
    def set_control(self, name: str, value: int) -> bool:
        """
        カメラコントロールを設定
        
        Args:
            name: コントロール名
            value: 設定値
        
        Returns:
            bool: 設定成功時True
        
        Raises:
            RuntimeError: カメラ未接続
            ValueError: 無効な値、または設定不可能なコントロール
        """
        if not self.is_opened():
            raise RuntimeError("カメラが接続されていません")
        
        # コントロールの存在と設定可能性を確認
        try:
            controls = self.get_controls()
            if name not in controls:
                raise ValueError(f"コントロール '{name}' が見つかりません")
            
            ctrl = controls[name]
            
            # flagsチェック（inactive, disabled, grabbed等）
            flags = ctrl.get('flags', '')
            if 'inactive' in flags.lower():
                raise ValueError(f"コントロール '{name}' は現在無効です (inactive)")
            if 'disabled' in flags.lower():
                raise ValueError(f"コントロール '{name}' は無効化されています (disabled)")
            if 'grabbed' in flags.lower():
                logger.warning(f"コントロール '{name}' は他のプロセスで使用中です (grabbed)")
            
            # 型別バリデーション
            ctrl_type = ctrl.get('type')
            
            if ctrl_type == 'button':
                # ボタンは値を持たない（押下のみ）
                pass
            elif ctrl_type in ('int', 'int64', 'menu'):
                min_val = ctrl.get('min', 0)
                max_val = ctrl.get('max', 0)
                if not (min_val <= value <= max_val):
                    raise ValueError(
                        f"値 {value} は範囲外です。{name}の範囲: {min_val}〜{max_val}"
                    )
            elif ctrl_type == 'bool':
                if value not in (0, 1):
                    raise ValueError(f"bool型コントロールには0または1を指定してください")
            elif ctrl_type == 'bitmask':
                max_val = ctrl.get('max', 0)
                if value > max_val or value < 0:
                    raise ValueError(f"bitmask値 {value} は範囲外です (0〜0x{max_val:x})")
            
        except ValueError:
            raise
        except Exception as e:
            logger.warning(f"コントロール検証エラー: {e}。設定を試行します。")
        
        # v4l2-ctlで設定
        try:
            result = subprocess.run(
                ['v4l2-ctl', '-d', f'/dev/video{CAMERA_DEVICE}', '--set-ctrl', f'{name}={value}'],
                check=True,
                capture_output=True,
                text=True
            )
            logger.info(f"カメラコントロール設定: {name}={value}")
            return True
        
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.strip() if e.stderr else str(e)
            logger.error(f"コントロール設定エラー: {error_msg}")
            raise RuntimeError(f"コントロール設定失敗 ({name}={value}): {error_msg}")
        except FileNotFoundError:
            logger.error("v4l2-ctlコマンドが見つかりません")
            raise RuntimeError("v4l2-ctlコマンドが見つかりません")
    
    
    def reset_control(self, name: str) -> bool:
        """
        カメラコントロールをデフォルト値にリセット
        
        Args:
            name: コントロール名
        
        Returns:
            bool: リセット成功時True
        """
        controls = self.get_controls()
        if name not in controls:
            raise ValueError(f"コントロール '{name}' が見つかりません")
        
        ctrl = controls[name]
        default_value = ctrl.get('default')
        
        if default_value is None:
            raise ValueError(f"コントロール '{name}' はデフォルト値を持ちません")
        
        return self.set_control(name, default_value)
    
    def reset_all_controls(self) -> Dict[str, bool]:
        """
        すべてのカメラコントロールをデフォルト値にリセット
        
        Returns:
            Dict[str, bool]: {control_name: success}
        """
        controls = self.get_controls()
        results = {}
        
        for name, ctrl in controls.items():
            # button型やdefaultを持たないものはスキップ
            if ctrl.get('type') == 'button' or 'default' not in ctrl:
                continue
            
            # inactive/disabledはスキップ
            flags = ctrl.get('flags', '')
            if 'inactive' in flags.lower() or 'disabled' in flags.lower():
                continue
            
            try:
                default_value = ctrl['default']
                self.set_control(name, default_value)
                results[name] = True
            except Exception as e:
                logger.warning(f"コントロール '{name}' のリセット失敗: {e}")
                results[name] = False
        
        logger.info(f"カメラコントロールリセット完了: {sum(results.values())}/{len(results)}個")
        return results
    
    async def update_settings(self, width: int, height: int, fps: int):
        """解像度とFPSを更新（再起動が必要）"""
        self.settings["width"] = width
        self.settings["height"] = height
        self.settings["fps"] = fps
        
        # カメラを再起動
        await self.stop()
        await self.start()
        logger.info(f"解像度変更: {width}x{height}@{fps}fps")
