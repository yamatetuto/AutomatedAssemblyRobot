"""OctoPrintとの通信を担当するクライアント"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import aiohttp

logger = logging.getLogger(__name__)


class OctoPrintError(Exception):
    """OctoPrint通信で発生した例外"""


class OctoPrintClient:
    """OctoPrint REST API をラップする非同期クライアント"""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        *,
        timeout: float = 10.0,
        session: Optional[aiohttp.ClientSession] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._timeout = aiohttp.ClientTimeout(total=timeout)
        self._external_session = session
        self._session: Optional[aiohttp.ClientSession] = session
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        if self._session is None:
            self._session = aiohttp.ClientSession(timeout=self._timeout)
            logger.info("OctoPrintClient: セッションを開始しました")

    async def close(self) -> None:
        if self._session and self._session is not self._external_session:
            await self._session.close()
            logger.info("OctoPrintClient: セッションを終了しました")
        self._session = None

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        if not self._session:
            raise RuntimeError("OctoPrintClient session is not started")

        headers = kwargs.pop("headers", {})
        headers["X-Api-Key"] = self.api_key
        url = f"{self.base_url}{path}"

        async with self._session.request(method, url, headers=headers, **kwargs) as resp:
            content_type = resp.headers.get("Content-Type", "")
            if resp.status >= 400:
                text = await resp.text()
                raise OctoPrintError(f"{method} {path} failed: {resp.status} {text}")

            if "application/json" in content_type:
                return await resp.json()
            return await resp.text()

    async def get_job(self) -> Dict[str, Any]:
        return await self._request("GET", "/api/job")

    async def get_printer_state(self) -> Dict[str, Any]:
        return await self._request("GET", "/api/printer")

    async def send_gcode(self, command: str) -> None:
        payload = {"command": command}
        await self._request("POST", "/api/printer/command", json=payload)

    async def send_gcode_batch(self, commands: List[str]) -> None:
        payload = {"commands": commands}
        await self._request("POST", "/api/printer/command", json=payload)

    async def job_control(self, command: str, action: Optional[str] = None) -> None:
        payload: Dict[str, Any] = {"command": command}
        if action:
            payload["action"] = action
        await self._request("POST", "/api/job", json=payload)

    async def start_job(self, file_path: str) -> None:
        # OctoPrintのAPI仕様: /api/files/local/<path> にPOSTでselect/print
        quoted = quote(file_path.lstrip("/"))
        payload = {"command": "select", "print": True}
        await self._request("POST", f"/api/files/local/{quoted}", json=payload)

    async def list_files(self) -> Dict[str, Any]:
        return await self._request("GET", "/api/files")

    async def estop(self) -> None:
        # ヒーターOFF + 動作中ジョブキャンセル
        async with self._lock:
            try:
                await self.job_control("cancel")
            except OctoPrintError as e:
                logger.warning("ジョブキャンセルに失敗: %s", e)
            await self.send_gcode_batch(["M112", "M104 S0", "M140 S0", "M84"])  # 緊急停止 + ヒーターOFF + モーターOFF

