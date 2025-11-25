"""3Dプリンター制御の高レベルマネージャー"""
from __future__ import annotations

import asyncio
import re
import logging
import socket
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.config.settings import PRINTER_BAUDRATE, PRINTER_PORT, PRINTER_BED_DEPTH
from src.printer.octoprint_client import OctoPrintClient, OctoPrintError

logger = logging.getLogger(__name__)


class PrinterManager:
    def __init__(
        self,
        client: OctoPrintClient,
        *,
        poll_interval: float = 5.0,
        macros: Optional[Dict[str, List[str]]] = None,
        octoprint_cmd: str = "/home/pi/.local/bin/octoprint serve",
    ) -> None:
        self.client = client
        self.poll_interval = poll_interval
        self.macros = {name: list(cmds) for name, cmds in (macros or {}).items()}
        self.octoprint_cmd = octoprint_cmd
        self._monitor_task: Optional[asyncio.Task] = None
        self._octoprint_process: Optional[subprocess.Popen] = None
        self._macro_lock = asyncio.Lock()
        self._status: Dict[str, Any] = {
            "state": "offline",
            "progress": 0.0,
            "eta": None,
            "job": None,
            "temperatures": {"tool0": None, "bed": None},
            "message": None,
        }
        self._status_lock = asyncio.Lock()

    async def start(self) -> None:
        # OctoPrintサーバーの確認と起動
        await self._ensure_octoprint_server()
        
        await self.client.start()
        
        # 自動接続を試行
        try:
            await self._ensure_connection()
        except Exception as e:
            logger.warning("プリンターへの自動接続に失敗しました: %s", e)

        if not self._monitor_task or self._monitor_task.done():
            self._monitor_task = asyncio.create_task(self._monitor_loop())
            logger.info("PrinterManager: 監視タスクを開始しました")

    async def _ensure_octoprint_server(self) -> None:
        """OctoPrintサーバーが起動しているか確認し、なければ起動する"""
        if self._is_port_open(5000):
            logger.info("OctoPrintサーバーは既に稼働しています")
            return

        logger.info("OctoPrintサーバーを起動しています...")
        try:
            # コマンドを分割して実行
            cmd_parts = self.octoprint_cmd.split()
            self._octoprint_process = subprocess.Popen(
                cmd_parts,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            
            # 起動待機 (最大60秒)
            for i in range(60):
                if self._is_port_open(5000):
                    logger.info("OctoPrintサーバーの起動を確認しました")
                    # サーバー安定化のために少し待つ
                    await asyncio.sleep(5)
                    return
                if i % 5 == 0:
                    logger.info("OctoPrintサーバーの起動を待機中... (%ds)", i)
                await asyncio.sleep(1)
            
            raise RuntimeError("OctoPrintサーバーの起動がタイムアウトしました")
            
        except Exception as e:
            logger.error("OctoPrintサーバーの起動に失敗しました: %s", e)
            raise

    def _is_port_open(self, port: int, host: str = "127.0.0.1") -> bool:
        """指定したポートが開いているか確認"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(1)
            return s.connect_ex((host, port)) == 0

    async def _ensure_connection(self) -> None:
        """OctoPrintがプリンターに未接続なら接続を試みる"""
        try:
            conn = await self.client.get_connection()
            current_state = conn.get("current", {}).get("state", "Closed")
            
            if current_state in ["Closed", "Offline", "Error"]:
                logger.info("プリンターに接続を試みます (Port: %s, Baud: %s)...", 
                          PRINTER_PORT or "Auto", PRINTER_BAUDRATE or "Auto")
                
                await self.client.connect(
                    port=PRINTER_PORT,
                    baudrate=int(PRINTER_BAUDRATE) if PRINTER_BAUDRATE else None,
                    autoconnect=True
                )
            else:
                logger.info("プリンターは既に接続されています: %s", current_state)
                
        except OctoPrintError as e:
            logger.error("接続状態の確認に失敗しました: %s", e)

    async def stop(self) -> None:
        if self._monitor_task and not self._monitor_task.done():
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            logger.info("PrinterManager: 監視タスクを停止しました")
        self._monitor_task = None
        await self.client.close()
        
        # OctoPrintプロセスを起動していた場合は終了させる
        if self._octoprint_process:
            logger.info("OctoPrintサーバーを停止しています...")
            self._octoprint_process.terminate()
            try:
                self._octoprint_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._octoprint_process.kill()
            logger.info("OctoPrintサーバーを停止しました")
            self._octoprint_process = None

    async def _monitor_loop(self) -> None:
        while True:
            try:
                job = await self.client.get_job()
                printer = await self.client.get_printer_state()
                await self._update_status(job, printer)
            except OctoPrintError as e:
                logger.warning("OctoPrint監視エラー: %s", e)
                await self._set_offline(str(e))
            except Exception as e:  # pylint: disable=broad-except
                logger.exception("Printer監視タスクで予期せぬエラー: %s", e)
                await self._set_offline(str(e))
            await asyncio.sleep(self.poll_interval)

    async def _update_status(self, job: Dict[str, Any], printer: Dict[str, Any]) -> None:
        async with self._status_lock:
            progress = job.get("progress") or {}
            state = job.get("state") or "unknown"
            temps = printer.get("temperature") or {}
            self._status.update(
                {
                    "state": state,
                    "progress": progress.get("completion"),
                    "eta": progress.get("printTimeLeft"),
                    "job": job.get("job"),
                    "temperatures": {
                        "tool0": temps.get("tool0"),
                        "bed": temps.get("bed"),
                    },
                    "message": None,
                }
            )

    async def _set_offline(self, message: Optional[str] = None) -> None:
        async with self._status_lock:
            self._status.update(
                {
                    "state": "offline",
                    "progress": None,
                    "eta": None,
                    "job": None,
                    "temperatures": {"tool0": None, "bed": None},
                    "message": message,
                }
            )

    async def get_status(self) -> Dict[str, Any]:
        async with self._status_lock:
            return dict(self._status)

    async def list_files(self) -> Dict[str, Any]:
        return await self.client.list_files()

    async def list_macros(self) -> Dict[str, List[str]]:
        """定義済みマクロの浅いコピーを返す"""
        async with self._macro_lock:
            return {name: list(cmds) for name, cmds in self.macros.items()}

    async def upsert_macro(self, name: str, commands: List[str]) -> None:
        """マクロを追加または上書き"""
        cleaned = [cmd.strip() for cmd in commands if cmd.strip()]
        if not cleaned:
            raise ValueError('マクロには1行以上のG-codeが必要です')
        async with self._macro_lock:
            self.macros[name] = cleaned

    async def delete_macro(self, name: str) -> None:
        """マクロを削除"""
        async with self._macro_lock:
            if name not in self.macros:
                raise ValueError(f'未定義のマクロ: {name}')
            del self.macros[name]

    async def start_job(self, file_path: str) -> None:
        await self.client.start_job(file_path)

    async def pause_job(self) -> None:
        """一時停止: API Pause -> 待機 -> M114で位置取得 -> 退避"""
        # 1. APIで一時停止
        await self.client.job_control("pause", action="pause")
        
        # 2. 状態がPausedになるまで待機
        for _ in range(40):
            status = await self.get_status()
            state = status.get("state", "").lower()
            if "paused" in state:
                break
            await asyncio.sleep(0.5)
            
        # 3. 現在位置を取得 (M114)
        # G60が使えないため、M114の結果をserial.logから読み取る
        await self.client.send_gcode("M114")
        await asyncio.sleep(1.0) # ログ書き込み待ち
        
        # ログから座標を解析
        try:
            log_path = Path("/home/pi/.octoprint/logs/serial.log")
            if log_path.exists():
                # 末尾4KBを読む
                file_size = log_path.stat().st_size
                with open(log_path, "rb") as f:
                    if file_size > 4096:
                        f.seek(-4096, 2)
                    log_content = f.read().decode("utf-8", errors="ignore")
                    
                # 最新のM114レスポンスを探す
                # Recv: X:98.97 Y:218.72 Z:0.30 E:17.59 Count X:15836 Y:34995 Z:240
                matches = list(re.finditer(r"Recv: X:([0-9.-]+) Y:([0-9.-]+) Z:([0-9.-]+) E:([0-9.-]+)", log_content))
                if matches:
                    last_match = matches[-1]
                    self._paused_position = {
                        "x": float(last_match.group(1)),
                        "y": float(last_match.group(2)),
                        "z": float(last_match.group(3)),
                        "e": float(last_match.group(4))
                    }
                    logger.info(f"Paused position saved: {self._paused_position}")
                else:
                    logger.warning("M114 response not found in serial.log")
                    self._paused_position = None
            else:
                logger.warning("serial.log not found")
                self._paused_position = None
        except Exception as e:
            logger.error(f"Failed to parse position from log: {e}")
            self._paused_position = None

        # 4. 退避動作
        cmds = [
            "G91",              # 相対座標
            "G1 Z10 F3000",     # Z 10mm上昇
            "G90",              # 絶対座標
            f"G1 X0 Y{PRINTER_BED_DEPTH} F3000" # ベッド手前へ退避
        ]
        await self.client.send_gcode_batch(cmds)

    async def resume_job(self) -> None:
        """再開: 保存した位置へ復帰 -> API Resume"""
        if hasattr(self, "_paused_position") and self._paused_position:
            pos = self._paused_position
            logger.info(f"Restoring position: {pos}")
            
            # 1. XY位置復帰 (Zは高いまま)
            # 現在は Z+10 の高さにいるはず
            cmds_xy = [
                "G90",
                f"G1 X{pos['x']} Y{pos['y']} F3000"
            ]
            await self.client.send_gcode_batch(cmds_xy)
            
            # 2. Z位置復帰
            cmds_z = [
                f"G1 Z{pos['z']} F3000"
            ]
            await self.client.send_gcode_batch(cmds_z)
        else:
            logger.warning("No paused position found, skipping position restore")
            # 位置不明の場合は、とりあえずZだけ相対で戻すか、何もしないか...
            # 安全のため、相対で戻す (pauseで上げた分)
            cmds_fallback = [
                "G91",
                "G1 Z-10 F3000",
                "G90"
            ]
            await self.client.send_gcode_batch(cmds_fallback)
        
        # 3. APIで再開
        await self.client.job_control("pause", action="resume")

    async def cancel_job(self) -> None:
        await self.client.job_control("cancel")

    async def run_macro(self, name: str) -> None:
        async with self._macro_lock:
            commands = self.macros.get(name)
        if not commands:
            raise ValueError(f"未定義のマクロ: {name}")
        await self.client.send_gcode_batch(commands)

    async def send_command(self, command: str) -> None:
        await self.client.send_gcode(command)

    async def estop(self) -> None:
        await self.client.estop()

    async def present_bed(self) -> None:
        """ベッドを最大限手前に出す"""
        # G90: 絶対座標モード
        # G0 Y{max}: Y軸最大へ移動
        cmd = ["G90", f"G0 Y{PRINTER_BED_DEPTH} F3000"]
        await self.client.send_gcode_batch(cmd)
