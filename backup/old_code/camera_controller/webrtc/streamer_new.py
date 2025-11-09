"""WebRTC streamer module (aiohttp + aiortc) for camera_controller package.

This file is largely a copy of the working implementation under
camera_controll/webrtc_streamer.py but placed under the new package.
"""
from __future__ import annotations

import asyncio
import json
import re
import shlex
import shutil
import subprocess
import os
import datetime
from fractions import Fraction
from pathlib import Path
from typing import Optional

import av
import time
import numpy as np
from aiohttp import web

try:
    from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack
except Exception:  # pragma: no cover - runtime
    raise

import cv2

# module-level active tracks map
active_tracks: dict[int, 'OpenCVVideoTrack'] = {}


def v4l2_ctl_available() -> bool:
    return shutil.which('v4l2-ctl') is not None


def get_camera_properties(cap) -> dict:
    """Get camera properties like resolution, FPS, codec, etc."""
    props = {}
    try:
        props['width'] = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        props['height'] = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        props['fps'] = cap.get(cv2.CAP_PROP_FPS)
        props['fourcc'] = int(cap.get(cv2.CAP_PROP_FOURCC))
        # Decode fourcc to readable format
        fourcc_int = int(props['fourcc'])
        props['codec'] = "".join([chr((fourcc_int >> 8 * i) & 0xFF) for i in range(4)])
        props['brightness'] = cap.get(cv2.CAP_PROP_BRIGHTNESS)
        props['contrast'] = cap.get(cv2.CAP_PROP_CONTRAST)
        props['saturation'] = cap.get(cv2.CAP_PROP_SATURATION)
        props['hue'] = cap.get(cv2.CAP_PROP_HUE)
        props['gain'] = cap.get(cv2.CAP_PROP_GAIN)
        props['exposure'] = cap.get(cv2.CAP_PROP_EXPOSURE)
    except Exception as e:
        print(f"Error getting camera properties: {e}")
    return props


def set_v4l2_control(device: int, ctrl: str, value) -> bool:
    dev_path = f"/dev/video{device}"
    if not v4l2_ctl_available():
        return False
    cmd = f"v4l2-ctl -d {shlex.quote(dev_path)} --set-ctrl={shlex.quote(ctrl)}={shlex.quote(str(value))}"
    try:
        subprocess.check_call(cmd, shell=True)
        return True
    except Exception:
        try:
            out = subprocess.check_output(f"v4l2-ctl -d {shlex.quote(dev_path)} -L", shell=True, text=True, stderr=subprocess.STDOUT)
        except Exception as e:
            print(f"v4l2-ctl list failed: {e}")
            return False
        cand = None
        for line in out.splitlines():
            if ctrl.lower() in line.lower():
                parts = line.strip().split()
                if parts:
                    cand = parts[0]
                    break
        if cand is None and ("white" in ctrl.lower() or "awb" in ctrl.lower()):
            for alt in ('white_balance_automatic', 'white_balance_temperature_auto', 'auto_white_balance'):
                if alt.lower() in out.lower():
                    cand = alt
                    break
        if cand:
            cmd2 = f"v4l2-ctl -d {shlex.quote(dev_path)} --set-ctrl={shlex.quote(cand)}={shlex.quote(str(value))}"
            try:
                subprocess.check_call(cmd2, shell=True)
                return True
            except Exception as e2:
                print(f"v4l2-ctl set failed with candidate '{cand}': {e2}")
                return False
        print(f"Could not find matching control for '{ctrl}'")
        return False


def apply_control_to_cap(cap, ctrl: str, value, device: int):
    if cap is None:
        set_v4l2_control(device, ctrl, value)
        return
    prop_map = {
        'brightness': cv2.CAP_PROP_BRIGHTNESS,
        'contrast': cv2.CAP_PROP_CONTRAST,
        'saturation': cv2.CAP_PROP_SATURATION,
        'hue': cv2.CAP_PROP_HUE,
        'white_balance_automatic': cv2.CAP_PROP_AUTO_WB
    }
    prop = prop_map.get(ctrl)
    if prop is not None:
        try:
            cap.set(prop, float(value))
        except Exception as e:
            print(f"cv2 set failed for '{ctrl}': {e}")
            set_v4l2_control(device, ctrl, value)
    else:
        set_v4l2_control(device, ctrl, value)


def probe_v4l2_controls(device: int) -> dict:
    dev_path = f"/dev/video{device}"
    if not v4l2_ctl_available():
        return {}
    try:
        out = subprocess.check_output(f"v4l2-ctl -d {shlex.quote(dev_path)} -L", shell=True, text=True, stderr=subprocess.STDOUT)
    except Exception as e:
        print(f"v4l2-ctl list failed: {e}")
        return {}
    controls = {}
    rx = re.compile(r"^(?P<name>\S+)\s+0x[0-9a-fA-F]+\s+\([^)]+\)\s*:\s*(?P<rest>.*)$")
    for line in out.splitlines():
        m = rx.match(line.strip())
        if not m:
            continue
        name = m.group('name')
        rest = m.group('rest')
        meta = {}
        for kv in re.finditer(r"(min|max|step|default|value)=([0-9-]+)", rest):
            meta[kv.group(1)] = int(kv.group(2))
        if meta:
            controls[name] = meta
    return controls


class OpenCVVideoTrack(VideoStreamTrack):
    """VideoStreamTrack that reads from either a dedicated cv2.VideoCapture or from a shared_frame buffer.

    If shared_frame is not None, the track will pull frames from the shared_frame buffer populated by a background
    reader task (see `run_webrtc_server` startup handler). This avoids opening the camera per-peer.
    """
    def __init__(self, device: int, width: int, height: int, rotation: int, flip: bool, cap=None, shared_frame=None):
        super().__init__()
        self.device = device
        self.width = width
        self.height = height
        self.rotation = rotation
        self.flip = flip
        self._frame_count = 0

        # Either use an explicitly supplied cv2.VideoCapture, a shared_frame buffer, or open our own
        self._cap = cap
        self._shared_frame = shared_frame
        if self._cap is None and self._shared_frame is None:
            # Per-track mode: open our own VideoCapture
            self._cap = cv2.VideoCapture(self.device)
            if self.width:
                self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            if self.height:
                self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)

    async def recv(self):
        loop = asyncio.get_event_loop()

        # Pull a frame from either the shared frame buffer or from self._cap
        if self._shared_frame is not None:
            # Shared mode: fetch from shared_frame dict
            frm = self._shared_frame.get('frame')
            # wait if not yet available
            while frm is None:
                await asyncio.sleep(0.01)
                frm = self._shared_frame.get('frame')
            try:
                h = self.height or 480
                w = self.width or 640
                frame = np.zeros((h, w, 3), dtype=np.uint8)
            except Exception:
                pass
            else:
                frame = frm.copy()
        else:
            # Dedicated mode
            if self._cap is None:
                h = self.height or 480
                w = self.width or 640
                frame = np.zeros((h, w, 3), dtype=np.uint8)
            else:
                try:
                    ret, frm = await loop.run_in_executor(None, self._cap.read)
                except Exception:
                    ret = False
                    frm = None
                if not ret or frm is None:
                    await asyncio.sleep(0.01)
                    h = self.height or 480
                    w = self.width or 640
                    frame = np.zeros((h, w, 3), dtype=np.uint8)
                else:
                    frame = frm

        # Apply transformations
        if 'frame' not in locals():
            h = self.height or 480
            w = self.width or 640
            frame = np.zeros((h, w, 3), dtype=np.uint8)
        if self.rotation % 360 != 0:
            k = (self.rotation // 90) % 4
            if k == 1:
                frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
            elif k == 2:
                frame = cv2.rotate(frame, cv2.ROTATE_180)
            elif k == 3:
                frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
        if self.flip:
            frame = cv2.flip(frame, 1)

        video_frame = av.VideoFrame.from_ndarray(frame, format="bgr24")
        pts = int(time.time() * 1000)
        video_frame.pts = pts
        video_frame.time_base = Fraction(1, 1000)
        self._frame_count += 1
        if self._frame_count % 300 == 0:
            print(f"OpenCVVideoTrack: captured {self._frame_count} frames")
        return video_frame


class OpenCVPipelineTrack(VideoStreamTrack):
    """VideoTrack that uses an injected capture and processor."""

    def __init__(self, device: int, rotation: int, flip: bool, capture, processor):
        super().__init__()
        self.capture = capture
        self.processor = processor
        self.device = device
        self.rotation = rotation
        self.flip = flip
        self._frame_count = 0

    async def recv(self):
        loop = asyncio.get_event_loop()
        # capture.read() is blocking; run in executor
        ret, frame = await loop.run_in_executor(None, self.capture.read)
        if not ret:
            await asyncio.sleep(0.01)
            h = 480
            w = 640
            frame = np.zeros((h, w, 3), dtype=np.uint8)

        # Apply transformations
        if self.rotation % 360 != 0:
            k = (self.rotation // 90) % 4
            if k == 1:
                frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
            elif k == 2:
                frame = cv2.rotate(frame, cv2.ROTATE_180)
            elif k == 3:
                frame = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
        if self.flip:
            frame = cv2.flip(frame, 1)

        # Apply processor if provided
        if self.processor is not None:
            try:
                frame = self.processor.process(frame)
            except Exception as e:
                print(f"Processor error: {e}")

        video_frame = av.VideoFrame.from_ndarray(frame, format="bgr24")
        pts = int(time.time() * 1000)
        video_frame.pts = pts
        video_frame.time_base = Fraction(1, 1000)
        self._frame_count += 1
        if self._frame_count % 300 == 0:
            print(f"OpenCVPipelineTrack: captured {self._frame_count} frames")
        return video_frame


async def _index(request):
    return web.Response(content_type='text/html', text=request.app['index_html'])


async def _offer(request):
    params = await request.json()
    offer = RTCSessionDescription(sdp=params['sdp'], type=params['type'])
    pc = RTCPeerConnection()
    pcs = request.app.setdefault('pcs', set())
    pcs.add(pc)

    @pc.on('connectionstatechange')
    async def on_state_change():
        if pc.connectionState == 'failed':
            asyncio.ensure_future(pc.close())

    print("[webrtc] Received offer from client. Setting remote description...")
    await pc.setRemoteDescription(offer)
    print("[webrtc] Remote description set.")

    device = request.app['device']
    width = request.app['width']
    height = request.app['height']
    rotation = request.app['rotation']
    flip = request.app['flip']

    cap_obj = request.app.get('capture')
    proc_obj = request.app.get('processor')

    if cap_obj is not None and proc_obj is not None:
        track = OpenCVPipelineTrack(device, rotation, flip, cap_obj, proc_obj)
    else:
        shared_frame = request.app.get('shared_frame')
        shared_cap = request.app.get('shared_cap')
        track = OpenCVVideoTrack(device, width, height, rotation, flip, cap=shared_cap, shared_frame=shared_frame)

    active_tracks[id(track)] = track

    pc.addTrack(track)

    # Apply controls to the track's capture if it exists
    # If in shared_cap mode, apply to the shared capture object
    for key, val in request.app.get('controls', {}).items():
        if val is not None:
            if hasattr(track, '_cap') and track._cap is not None:
                cap_to_apply = track._cap
            else:
                cap_to_apply = request.app.get('shared_cap') or request.app.get('capture')
            apply_control_to_cap(cap_to_apply, key, val, device)

    # If the client wants video back, they'll typically signal recvonly (server sends)
    if pc.getTransceivers():
        trs = pc.getTransceivers()
        for tr in trs:
            if tr.kind == 'video':
                tr.direction = 'sendonly'

    answer = await pc.createAnswer()
    await pc.setLocalDescription(answer)
    print("[webrtc] Created answer and set local description.")
    return web.Response(content_type='application/json', text=json.dumps({'sdp': pc.localDescription.sdp, 'type': pc.localDescription.type}))


async def _settings(request):
    data = await request.json()
    app = request.app
    device = app['device']

    track = None
    for tid, t in active_tracks.items():
        track = t
        break

    for key in ('brightness', 'contrast', 'saturation', 'hue'):
        if key in data:
            app['controls'][key] = data[key]
            if track is not None:
                apply_control_to_cap(track._cap, key, data[key], device)
            else:
                set_v4l2_control(device, key, data[key])
    if 'awb' in data:
        val = 1 if data['awb'] else 0
        app['controls']['white_balance_automatic'] = val
        if track is not None:
            apply_control_to_cap(track._cap, 'white_balance_automatic', val, device)
        else:
            set_v4l2_control(device, 'white_balance_temperature_auto', val)
    return web.Response(content_type='application/json', text=json.dumps({'ok': True, 'controls': app['controls']}))


async def _get_settings(request):
    app = request.app
    # Get camera properties from shared_cap
    camera_info = {}
    cap = app.get('shared_cap') or app.get('capture')
    if cap:
        camera_info = get_camera_properties(cap)
    
    return web.Response(content_type='application/json', text=json.dumps({
        'controls': app.get('controls', {}),
        'meta': app.get('controls_meta', {}),
        'camera_info': camera_info
    }))


async def _snapshot(request):
    """Save a snapshot of the current frame."""
    app = request.app
    shared_frame = app.get('shared_frame')
    
    if shared_frame is None or shared_frame.get('frame') is None:
        return web.Response(
            content_type='application/json',
            status=503,
            text=json.dumps({'error': 'No frame available'})
        )
    
    frame = shared_frame['frame'].copy()
    
    # Create snapshots directory if it doesn't exist
    snapshots_dir = Path('snapshots')
    snapshots_dir.mkdir(exist_ok=True)
    
    # Generate filename with timestamp
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"snapshot_{timestamp}.jpg"
    filepath = snapshots_dir / filename
    
    # Save the image
    try:
        cv2.imwrite(str(filepath), frame)
        return web.Response(
            content_type='application/json',
            text=json.dumps({
                'ok': True,
                'filename': filename,
                'filepath': str(filepath.absolute())
            })
        )
    except Exception as e:
        return web.Response(
            content_type='application/json',
            status=500,
            text=json.dumps({'error': str(e)})
        )


def run_webrtc_server(device: int, width: int, height: int, rotation: int, flip: bool, port: int = 8080, controls_init: dict | None = None, capture=None, processor=None):
    app = web.Application()
    here = Path(__file__).resolve().parent
    index_path = here / '..' / 'webrtc_index.html'
    # index_path above resolves to package root's webrtc_index.html; fallback to package parent
    if not index_path.exists():
        index_path = here / 'webrtc_index.html'
    if not index_path.exists():
        raise RuntimeError(f'WebRTC client HTML not found at {index_path}')
    index_html = index_path.read_text(encoding='utf-8')
    app['index_html'] = index_html
    app['device'] = device
    app['width'] = width
    app['height'] = height
    app['rotation'] = rotation
    app['flip'] = flip
    meta = probe_v4l2_controls(device)
    app['controls_meta'] = meta
    app['controls'] = {'brightness': None, 'contrast': None, 'saturation': None, 'hue': None, 'white_balance_automatic': None}
    if controls_init:
        for k, v in controls_init.items():
            if v is not None:
                app['controls'][k] = v
    for common in ('brightness', 'contrast', 'saturation', 'hue'):
        if app['controls'][common] is None:
            if common in meta and 'value' in meta[common]:
                app['controls'][common] = meta[common].get('value')
    if app['controls']['white_balance_automatic'] is None:
        for cand in ('white_balance_automatic', 'white_balance_auto', 'white_balance_temperature_auto', 'auto_white_balance'):
            if cand in meta and 'value' in meta[cand]:
                app['controls']['white_balance_automatic'] = meta[cand].get('value')
                break

    # attach optional injected objects for capture/processing
    if capture is not None:
        app['capture'] = capture
    if processor is not None:
        app['processor'] = processor

    # Setup a shared cv2.VideoCapture and a background reader task to populate the latest frame
    async def _capture_loop(app: web.Application):
        cap = app.get('shared_cap')
        shared = app.get('shared_frame')
        loop = asyncio.get_event_loop()
        try:
            while True:
                try:
                    ret, frame = await loop.run_in_executor(None, cap.read)
                except Exception:
                    ret = False
                    frame = None
                if ret and frame is not None:
                    shared['frame'] = frame
                else:
                    # no frame yet; small sleep
                    await asyncio.sleep(0.01)
                await asyncio.sleep(0)  # yield to event loop
        except asyncio.CancelledError:
            return

    async def _start_shared_capture(app: web.Application):
        # Only create shared capture if no injected capture object was provided
        if app.get('capture') is None:
            cap = cv2.VideoCapture(device)
            if width:
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            if height:
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            app['shared_cap'] = cap
            app['shared_frame'] = {'frame': None}
            app['frame_task'] = asyncio.create_task(_capture_loop(app))

    async def _stop_shared_capture(app: web.Application):
        task = app.get('frame_task')
        if task is not None:
            task.cancel()
            try:
                await task
            except Exception:
                pass
        cap = app.get('shared_cap')
        if cap is not None:
            try:
                cap.release()
            except Exception:
                pass
    
    app.router.add_get('/', _index)
    app.router.add_post('/offer', _offer)
    app.router.add_post('/settings', _settings)
    app.router.add_get('/settings', _get_settings)
    app.router.add_post('/snapshot', _snapshot)  # New snapshot endpoint
    app.on_startup.append(_start_shared_capture)
    app.on_cleanup.append(_stop_shared_capture)
    print(f'Starting WebRTC server on http://0.0.0.0:{port} — open this URL in a browser to view the stream')
    web.run_app(app, port=port)
