"""Simplified WebRTC streamer - camera opens only on client connect"""
from __future__ import annotations

import asyncio
import json
import re
import subprocess
import datetime
import signal
from pathlib import Path
import time

import av
import cv2
import numpy as np
from aiohttp import web
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack

# Active peer connections
pcs = set()
# Active video tracks
active_tracks: dict[int, 'OpenCVVideoTrack'] = {}

def get_v4l2_formats(device='/dev/video0'):
    """Parse v4l2-ctl --list-formats-ext to get available formats."""
    try:
        result = subprocess.run(
            ['v4l2-ctl', '-d', device, '--list-formats-ext'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode != 0:
            return {}
    except Exception:
        return {}
    
    formats = {}
    current_format = None
    current_size = None
    
    for line in result.stdout.splitlines():
        fmt_match = re.match(r"\s*\[\d+\]:\s+'([^']+)'", line)
        if fmt_match:
            current_format = fmt_match.group(1)
            formats[current_format] = []
            continue
        
        size_match = re.match(r"\s*Size:\s+Discrete\s+(\d+)x(\d+)", line)
        if size_match and current_format:
            width = int(size_match.group(1))
            height = int(size_match.group(2))
            current_size = (width, height)
            continue
        
        fps_match = re.match(r"\s*Interval:\s+Discrete\s+[\d.]+s\s+\(([\d.]+)\s+fps\)", line)
        if fps_match and current_format and current_size:
            fps = float(fps_match.group(1))
            formats[current_format].append({
                'width': current_size[0],
                'height': current_size[1],
                'fps': fps
            })
    
    return formats


def get_v4l2_controls(device='/dev/video0'):
    """Get all available V4L2 controls with their metadata."""
    try:
        result = subprocess.run(
            ['v4l2-ctl', '-d', device, '-L'],  # Use -L to get menu options
            capture_output=True, text=True, timeout=5
        )
        if result.returncode != 0:
            return {}
    except Exception:
        return {}
    
    controls = {}
    current_control_name = None
    
    for line in result.stdout.splitlines():
        # Skip section headers
        if line.strip() in ('User Controls', 'Camera Controls', 'Codec Controls'):
            continue
        
        # Parse integer controls: brightness 0x00980900 (int)    : min=0 max=255 step=1 default=128 value=128
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
        
        # Parse menu controls: power_line_frequency 0x00980918 (menu)   : min=0 max=2 default=2 value=0 (Disabled)
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
                'menu': {}
            }
            continue
        
        # Parse boolean controls: white_balance_automatic 0x0098090c (bool)   : default=1 value=1
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
        
        # Parse menu options: "                                0: Disabled"
        menu_opt_match = re.match(r'^\s+(\d+):\s+(.+)$', line)
        if menu_opt_match and current_control_name:
            ctrl = controls.get(current_control_name)
            if ctrl and ctrl.get('type') == 'menu' and 'menu' in ctrl:
                idx, label = menu_opt_match.groups()
                ctrl['menu'][int(idx)] = label.strip()
    
    return controls


def set_v4l2_control(device, control_name, value):
    """Set a V4L2 control using v4l2-ctl."""
    try:
        subprocess.run(
            ['v4l2-ctl', '-d', device, '--set-ctrl', f'{control_name}={value}'],
            capture_output=True, timeout=2
        )
        return True
    except Exception:
        return False


def fourcc_from_string(codec_str: str) -> int:
    """Convert codec string (e.g. 'MJPG') to fourcc int."""
    if len(codec_str) != 4:
        return 0
    return cv2.VideoWriter_fourcc(*codec_str)


class OpenCVVideoTrack(VideoStreamTrack):
    """Simple VideoStreamTrack that opens camera on init and closes on stop."""
    
    def __init__(self, device: str, width: int, height: int, fps: float, codec: str):
        super().__init__()
        self.device = device
        self.width = width
        self.height = height
        self.fps = fps
        self.codec = codec
        
        # Open camera
        self._cap = cv2.VideoCapture(device, cv2.CAP_V4L2)
        if not self._cap.isOpened():
            raise RuntimeError(f"Cannot open camera {device}")
        
        # Set format
        fourcc = fourcc_from_string(codec)
        if fourcc:
            self._cap.set(cv2.CAP_PROP_FOURCC, fourcc)
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self._cap.set(cv2.CAP_PROP_FPS, fps)
        
        # Register in active tracks
        active_tracks[id(self)] = self
    
    async def recv(self):
        pts, time_base = await self.next_timestamp()
        
        loop = asyncio.get_event_loop()
        ret, frame = await loop.run_in_executor(None, self._cap.read)
        
        if not ret or frame is None:
            # Return black frame on error
            frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        
        # Convert to av.VideoFrame
        video_frame = av.VideoFrame.from_ndarray(frame, format="bgr24")
        video_frame.pts = pts
        video_frame.time_base = time_base
        
        return video_frame
    
    def stop(self):
        super().stop()
        if self._cap:
            self._cap.release()
            self._cap = None
        active_tracks.pop(id(self), None)


async def _offer(request):
    """Handle WebRTC offer from client."""
    params = await request.json()
    offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])
    
    pc = RTCPeerConnection()
    pcs.add(pc)
    
    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        if pc.connectionState == "failed" or pc.connectionState == "closed":
            await pc.close()
            pcs.discard(pc)
    
    # Set remote description
    await pc.setRemoteDescription(offer)
    
    # Get camera settings from app state
    app = request.app
    device = app.get('device', '/dev/video0')
    width = app.get('width', 640)
    height = app.get('height', 480)
    fps = app.get('fps', 30.0)
    codec = app.get('codec', 'MJPG')
    
    # Create video track
    try:
        video_track = OpenCVVideoTrack(device, width, height, fps, codec)
        pc.addTrack(video_track)
    except Exception as e:
        return web.Response(
            content_type="application/json",
            text=json.dumps({"error": f"Failed to open camera: {e}"})
        )
    
    # Create answer
    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)
    
    return web.Response(
        content_type="application/json",
        text=json.dumps({"sdp": pc.localDescription.sdp, "type": pc.localDescription.type})
    )


async def _formats(request):
    """Return available camera formats."""
    app = request.app
    device = app.get('device', '/dev/video0')
    formats = get_v4l2_formats(device)
    return web.Response(content_type="application/json", text=json.dumps(formats))


async def _controls(request):
    """Return available camera controls."""
    app = request.app
    device = app.get('device', '/dev/video0')
    controls = get_v4l2_controls(device)
    return web.Response(content_type="application/json", text=json.dumps(controls))


async def _settings(request):
    """Apply camera settings."""
    data = await request.json()
    app = request.app
    device = app.get('device', '/dev/video0')
    
    # Update app state for resolution/fps/codec
    if 'width' in data:
        app['width'] = int(data['width'])
    if 'height' in data:
        app['height'] = int(data['height'])
    if 'fps' in data:
        app['fps'] = float(data['fps'])
    if 'codec' in data:
        app['codec'] = data['codec']
    
    # Apply V4L2 controls
    for key, value in data.items():
        if key in ('width', 'height', 'fps', 'codec'):
            continue
        # Use v4l2-ctl to set the control
        set_v4l2_control(device, key, value)
    
    return web.Response(
        content_type="application/json",
        text=json.dumps({
            'ok': True,
            'width': app.get('width'),
            'height': app.get('height'),
            'fps': app.get('fps'),
            'codec': app.get('codec')
        })
    )


async def _snapshot(request):
    """Take snapshot from first active track."""
    # Find first active track
    track = None
    for t in active_tracks.values():
        track = t
        break
    
    if not track or not hasattr(track, '_cap') or not track._cap:
        return web.Response(
            content_type="application/json",
            status=503,
            text=json.dumps({'error': 'No active camera'})
        )
    
    # Read frame
    ret, frame = track._cap.read()
    if not ret or frame is None:
        return web.Response(
            content_type="application/json",
            status=500,
            text=json.dumps({'error': 'Failed to capture frame'})
        )
    
    # Save
    snapshots_dir = Path('snapshots')
    snapshots_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"snapshot_{timestamp}.jpg"
    filepath = snapshots_dir / filename
    
    cv2.imwrite(str(filepath), frame)
    
    return web.Response(
        content_type="application/json",
        text=json.dumps({
            'ok': True,
            'filename': filename,
            'filepath': str(filepath.absolute())
        })
    )


async def on_shutdown(app):
    """Clean up on server shutdown."""
    # Close all peer connections
    coros = [pc.close() for pc in pcs]
    await asyncio.gather(*coros)
    pcs.clear()


def run_webrtc_server(device: str, width: int, height: int, fps: float, codec: str, port: int, index_html: str):
    """Run WebRTC server with graceful shutdown support."""
    app = web.Application()
    app['device'] = device
    app['width'] = width
    app['height'] = height
    app['fps'] = fps
    app['codec'] = codec
    
    # Routes
    app.router.add_post('/offer', _offer)
    app.router.add_get('/formats', _formats)
    app.router.add_get('/controls', _controls)
    app.router.add_get('/settings', _settings)
    app.router.add_post('/settings', _settings)
    app.router.add_post('/snapshot', _snapshot)
    
    # Serve HTML
    async def index(request):
        with open(index_html, 'r') as f:
            html = f.read()
        return web.Response(content_type='text/html', text=html)
    
    app.router.add_get('/', index)
    
    app.on_shutdown.append(on_shutdown)
    
    print(f"Starting WebRTC server on http://0.0.0.0:{port}")
    print("Press Ctrl+C to stop the server.")
    
    # Use web.run_app which handles Ctrl+C (SIGINT) gracefully
    try:
        web.run_app(app, host='0.0.0.0', port=port, print=None)
    except KeyboardInterrupt:
        pass
    print("\nServer stopped.")
