"""3Dプリンター制御の高レベルマネージャー"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional

from src.printer.octoprint_client import OctoPrintClient, OctoPrintError

logger = logging.getLogger(__name__)


class PrinterManager:
    def __init__(
        self,
        client: OctoPrintClient,
        *,
        poll_interval: float = 5.0,
        macros: Optional[Dict[str, List[str]]] = None,
    ) -> None:
        self.client = client
        self.poll_interval = poll_interval
        self.macros = {name: list(cmds) for name, cmds in (macros or {}).items()}
        self._monitor_task: Optional[asyncio.Task] = None
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
        await self.client.start()
        if not self._monitor_task or self._monitor_task.done():
            self._monitor_task = asyncio.create_task(self._monitor_loop())
            logger.info("PrinterManager: 監視タスクを開始しました")

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
        await self.client.job_control("pause", action="pause")

    async def resume_job(self) -> None:
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

