"""High-level wrapper for SPLEBO-N TEACHING modules."""
from __future__ import annotations

import importlib
import os
import sys
import threading
import time
from pathlib import Path
from typing import Optional, Dict, Any


class TeachingRobotManager:
    """Wrapper for TEACHING APIs to be used by FastAPI."""

    def __init__(
        self,
        teaching_dir: Path,
        position_file: Path,
        soft_limit_min_mm: float,
        soft_limit_max_mm: list[float],
        jog_speed_min_mm_s: float,
        jog_speed_max_mm_s: float,
        jog_speed_default_mm_s: float,
        jog_poll_interval_s: float = 0.05,
    ) -> None:
        self.teaching_dir = Path(teaching_dir)
        self.position_file = Path(position_file)
        self.soft_limit_min_mm = float(soft_limit_min_mm)
        self.soft_limit_max_mm = [float(v) for v in soft_limit_max_mm]
        self.jog_speed_min_mm_s = float(jog_speed_min_mm_s)
        self.jog_speed_max_mm_s = float(jog_speed_max_mm_s)
        self.jog_speed_default_mm_s = float(jog_speed_default_mm_s)
        self.jog_poll_interval_s = float(jog_poll_interval_s)

        if len(self.soft_limit_max_mm) < 3:
            raise ValueError("soft_limit_max_mm must have at least 3 values")

        self._lock = threading.RLock()
        self._splebo = None
        self._file_ctrl = None
        self._robot = None
        self._mc = None

        self._jog_stop_event = threading.Event()
        self._jog_monitor_thread: Optional[threading.Thread] = None
        self._current_jog_axis: Optional[int] = None
        self._current_jog_direction: Optional[bool] = None

    def connect(self) -> None:
        with self._lock:
            if self._robot is not None:
                return
            self._load_teaching_modules()
            original_cwd = Path.cwd()
            try:
                os.chdir(self.teaching_dir)
                self._robot = self._splebo.splebo_n_class()
                self._mc = self._robot.motion_class
            finally:
                os.chdir(original_cwd)

    def close(self) -> None:
        with self._lock:
            self._stop_jog_monitor()
            if self._robot is not None:
                try:
                    self.stop_all()
                except Exception:
                    pass
                try:
                    self._robot.close()
                finally:
                    self._robot = None
                    self._mc = None

    def home(self) -> None:
        with self._lock:
            self._ensure_ready()
            self._robot.motion_home()

    def get_position(self, axis: int) -> float:
        with self._lock:
            self._ensure_ready()
            self._assert_axis(axis)
            return float(self._robot.motion_getposition(axis))

    def jog_start(self, axis: int, direction_ccw: bool, speed_mm_s: float) -> None:
        with self._lock:
            self._ensure_ready()
            self._assert_axis(axis)
            speed_mm_s = self._validate_speed(speed_mm_s)
            self._assert_soft_limit(axis, direction_ccw)
            pps = self._get_pps(axis, speed_mm_s)
            self._send_jog_command(axis, direction_ccw, pps)
            self._start_jog_monitor(axis, direction_ccw)

    def jog_stop(self, axis: int) -> None:
        with self._lock:
            self._ensure_ready()
            self._assert_axis(axis)
            self._stop_jog_monitor()
            self._stop_axis(axis)

    def stop_all(self) -> None:
        with self._lock:
            if self._robot is None:
                return
            self._stop_jog_monitor()
            for axis in range(3):
                self._stop_axis(axis)

    def register_point_from_current(self, point_no: int, comment: str) -> Dict[str, Any]:
        with self._lock:
            self._ensure_ready()
            if point_no < 0:
                raise ValueError("point_no must be >= 0")

            pos_file = self._load_position_file()
            item_index = self._find_point_index(pos_file, point_no)
            if item_index is None:
                pos_file.add_point(point_no, "")
                pos_file.read_position_file()
                item_index = self._find_point_index(pos_file, point_no)

            if item_index is None:
                raise RuntimeError("Failed to register point entry")

            x = float(self._robot.motion_getposition(0))
            y = float(self._robot.motion_getposition(1))
            z = float(self._robot.motion_getposition(2))

            pos_file.update_pos(
                item_index,
                point_no,
                True,
                x,
                y,
                z,
                0,
                0,
                0,
                0,
                0,
                False,
                comment or "",
            )

            return {
                "point_no": point_no,
                "x": x,
                "y": y,
                "z": z,
                "comment": comment or "",
            }

    def move_to_point(self, point_no: int, speed_rate: float) -> None:
        with self._lock:
            self._ensure_ready()
            if point_no < 0:
                raise ValueError("point_no must be >= 0")
            speed_rate = float(speed_rate)
            if speed_rate <= 0 or speed_rate > 100:
                raise ValueError("speed_rate must be between 1 and 100")
            self._robot.motion_movePoint(0x07, int(point_no), speed_rate)

    def io_output(self, board_id: int, port_no: int, on: bool) -> bool:
        with self._lock:
            self._ensure_ready()
            return bool(self._robot.canio_output(int(board_id), int(port_no), on))

    def io_input(self, board_id: int, port_no: int) -> bool:
        with self._lock:
            self._ensure_ready()
            board_id = int(board_id)
            port_no = int(port_no)
            data = int(self._robot.canio_inputInt(board_id))
            return bool(data & (1 << port_no))

    def get_position_table_point(self, point_no: int) -> Dict[str, Any]:
        with self._lock:
            self._ensure_ready()
            if point_no < 0:
                raise ValueError("point_no must be >= 0")
            pos_file = self._load_position_file()
            item_index = self._find_point_index(pos_file, point_no)
            if item_index is None:
                raise ValueError("Point not found")
            return self._get_point_data(pos_file, item_index)

    def get_position_table_all(self) -> list[Dict[str, Any]]:
        with self._lock:
            self._ensure_ready()
            pos_file = self._load_position_file()
            results: list[Dict[str, Any]] = []
            for idx in range(len(self._file_ctrl.PositionFileClass.position_data_list)):
                try:
                    results.append(self._get_point_data(pos_file, idx))
                except Exception:
                    continue
            return results

    def update_position_table_point(self, point_no: int, x: float, y: float, z: float, comment: str) -> Dict[str, Any]:
        with self._lock:
            self._ensure_ready()
            if point_no < 0:
                raise ValueError("point_no must be >= 0")
            pos_file = self._load_position_file()
            item_index = self._find_point_index(pos_file, point_no)
            if item_index is None:
                pos_file.add_point(point_no, "")
                pos_file.read_position_file()
                item_index = self._find_point_index(pos_file, point_no)
            if item_index is None:
                raise RuntimeError("Failed to find point")

            current = self._get_point_data(pos_file, item_index)
            is_abs = bool(int(current.get("is_abs", 0)))
            is_protect = bool(int(current.get("is_protect", 0)))

            pos_file.update_pos(
                item_index,
                point_no,
                is_abs,
                float(x),
                float(y),
                float(z),
                float(current.get("u", 0.0)),
                float(current.get("s1", 0.0)),
                float(current.get("s2", 0.0)),
                float(current.get("a", 0.0)),
                float(current.get("b", 0.0)),
                is_protect,
                comment or "",
            )
            pos_file.read_position_file()
            item_index = self._find_point_index(pos_file, point_no)
            if item_index is None:
                raise RuntimeError("Failed to read updated point")
            return self._get_point_data(pos_file, item_index)

    def get_config(self) -> Dict[str, Any]:
        return {
            "jog_speed_min_mm_s": self.jog_speed_min_mm_s,
            "jog_speed_max_mm_s": self.jog_speed_max_mm_s,
            "jog_speed_default_mm_s": self.jog_speed_default_mm_s,
            "soft_limit_min_mm": self.soft_limit_min_mm,
            "soft_limit_max_mm": self.soft_limit_max_mm,
        }

    def get_emg_status(self) -> bool:
        with self._lock:
            self._ensure_ready()
            return bool(self._robot.emg_getstat())

    def get_positions(self) -> Dict[str, float]:
        with self._lock:
            self._ensure_ready()
            return {
                "x": float(self._robot.motion_getposition(0)),
                "y": float(self._robot.motion_getposition(1)),
                "z": float(self._robot.motion_getposition(2)),
            }

    def _ensure_ready(self) -> None:
        if self._robot is None:
            raise RuntimeError("Robot is not initialized")

    def _assert_axis(self, axis: int) -> None:
        if axis not in (0, 1, 2):
            raise ValueError("axis must be 0 (X), 1 (Y), or 2 (Z)")

    def _validate_speed(self, speed_mm_s: float) -> float:
        speed_mm_s = float(speed_mm_s)
        if speed_mm_s < self.jog_speed_min_mm_s or speed_mm_s > self.jog_speed_max_mm_s:
            raise ValueError(
                f"speed_mm_s must be between {self.jog_speed_min_mm_s} and {self.jog_speed_max_mm_s}"
            )
        return speed_mm_s

    def _get_pps(self, axis: int, speed_mm_s: float) -> int:
        pulse_len = self._splebo.axis_set_class[axis].pulse_length
        if pulse_len == 0:
            return 100
        return int(speed_mm_s / pulse_len)

    def _send_jog_command(self, axis: int, direction_ccw: bool, pps: int) -> None:
        self._splebo.set_order_motion_ctrl_class.axis = axis
        self._splebo.set_order_motion_ctrl_class.isCcw = bool(direction_ccw)
        self._splebo.set_order_motion_ctrl_class.dv = int(pps)
        order_id = self._mc.set_write_command(self._splebo.motion_controller_cmd_class.kMoveJOG)
        self._mc.wait_write_order_motion_ctrl(order_id)
        if not self._splebo.order_motion_ctrl_class[order_id].isFuncSuccess:
            raise RuntimeError("Failed to start JOG motion")

    def _stop_axis(self, axis: int) -> None:
        self._splebo.set_order_motion_ctrl_class.axis = axis
        order_id = self._mc.set_write_command(self._splebo.motion_controller_cmd_class.kStop)
        self._mc.wait_write_order_motion_ctrl(order_id)

    def _assert_soft_limit(self, axis: int, direction_ccw: bool) -> None:
        current_pos = float(self._robot.motion_getposition(axis))
        if direction_ccw and current_pos <= self.soft_limit_min_mm:
            raise ValueError("Soft limit reached (min)")
        if not direction_ccw and current_pos >= self.soft_limit_max_mm[axis]:
            raise ValueError("Soft limit reached (max)")

    def _start_jog_monitor(self, axis: int, direction_ccw: bool) -> None:
        self._stop_jog_monitor()
        self._jog_stop_event.clear()
        self._current_jog_axis = axis
        self._current_jog_direction = direction_ccw

        def _monitor() -> None:
            while not self._jog_stop_event.is_set():
                try:
                    pos = float(self._robot.motion_getposition(axis))
                    if direction_ccw and pos <= self.soft_limit_min_mm:
                        with self._lock:
                            self._stop_axis(axis)
                        self._jog_stop_event.set()
                        break
                    if not direction_ccw and pos >= self.soft_limit_max_mm[axis]:
                        with self._lock:
                            self._stop_axis(axis)
                        self._jog_stop_event.set()
                        break
                except Exception:
                    break
                time.sleep(self.jog_poll_interval_s)

        self._jog_monitor_thread = threading.Thread(target=_monitor, daemon=True)
        self._jog_monitor_thread.start()

    def _stop_jog_monitor(self) -> None:
        self._jog_stop_event.set()
        self._current_jog_axis = None
        self._current_jog_direction = None
        if self._jog_monitor_thread and self._jog_monitor_thread.is_alive():
            self._jog_monitor_thread.join(timeout=0.2)
        self._jog_monitor_thread = None

    def _load_position_file(self):
        pos_file = self._file_ctrl.PositionFileClass()
        pos_file.position_file_path = str(self.position_file)
        ok, message = pos_file.read_position_file()
        if not ok:
            raise RuntimeError(message)
        self._sanitize_position_list(pos_file)
        return pos_file

    def _find_point_index(self, pos_file, point_no: int) -> Optional[int]:
        for idx in range(len(self._file_ctrl.PositionFileClass.position_data_list)):
            data = self._parse_position_line(idx)
            if not data:
                continue
            if data["point_no"] == int(point_no):
                return idx
        return None

    def _get_point_data(self, pos_file, item_index: int) -> Dict[str, Any]:
        data = self._parse_position_line(item_index)
        if not data:
            raise ValueError("Invalid position data")
        return data

    def _parse_position_line(self, item_index: int) -> Optional[Dict[str, Any]]:
        try:
            line = self._file_ctrl.PositionFileClass.position_data_list[item_index]
        except Exception:
            return None
        if not line or "=" not in line:
            return None
        try:
            payload = line.split("=", 1)[1]
        except Exception:
            return None
        parts = payload.split(",")
        if len(parts) < 1:
            return None
        while len(parts) < 12:
            parts.append("")
        return {
            "point_no": self._safe_int(parts[0]),
            "is_abs": self._safe_int(parts[1]),
            "x": self._safe_float(parts[2]),
            "y": self._safe_float(parts[3]),
            "z": self._safe_float(parts[4]),
            "u": self._safe_float(parts[5]),
            "s1": self._safe_float(parts[6]),
            "s2": self._safe_float(parts[7]),
            "a": self._safe_float(parts[8]),
            "b": self._safe_float(parts[9]),
            "is_protect": self._safe_int(parts[10]),
            "comment": str(parts[11]),
        }

    def _sanitize_position_list(self, pos_file) -> None:
        original = list(self._file_ctrl.PositionFileClass.position_data_list)
        cleaned = [line for line in original if isinstance(line, str) and "=" in line]
        if len(cleaned) != len(original):
            self._file_ctrl.PositionFileClass.position_data_list = cleaned
            pos_file.create_position_file()

    def _safe_float(self, value: Any, default: float = 0.0) -> float:
        try:
            if value is None:
                return default
            text = str(value).strip()
            if text == "":
                return default
            return float(text)
        except Exception:
            return default

    def _safe_int(self, value: Any, default: int = 0) -> int:
        try:
            if value is None:
                return default
            text = str(value).strip()
            if text == "":
                return default
            return int(float(text))
        except Exception:
            return default

    def _load_teaching_modules(self) -> None:
        if self._splebo is not None:
            return

        if str(self.teaching_dir) not in sys.path:
            sys.path.insert(0, str(self.teaching_dir))

        so_path = self.teaching_dir / "libcsms_splebo_n.so"
        if not so_path.exists():
            raise RuntimeError(f"Missing shared library: {so_path}")

        ld_path = os.environ.get("LD_LIBRARY_PATH", "")
        if str(self.teaching_dir) not in ld_path.split(":" ):
            os.environ["LD_LIBRARY_PATH"] = f"{self.teaching_dir}:{ld_path}" if ld_path else str(self.teaching_dir)

        original_cwd = Path.cwd()
        try:
            os.chdir(self.teaching_dir)
            self._splebo = importlib.import_module("splebo_n")
            self._file_ctrl = importlib.import_module("file_ctrl")
        finally:
            os.chdir(original_cwd)
