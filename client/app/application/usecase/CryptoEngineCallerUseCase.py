from __future__ import annotations

import logging

from xime.adapters.socket import SocketClient
from xime.core.config.runtime import RuntimeConfig

from app.application.dto.crypto import DownloadRequest, EncryptRequest, HashRequest

_log = logging.getLogger(__name__)


class CryptoEngineCallerUseCase:
    """Calls the socket "Crypto Engine" over a Unix Domain Socket.

    Unlike the gRPC client there is no generated SDK and no DI-managed channel:
    we build a SocketClient by hand from the path in application.yml. Responses
    come back as plain dicts (msgpack), not typed DTOs - so we read them by key.
    Khác client gRPC: không có SDK sinh tự động, không channel quản lý bởi DI - ta
    tự dựng SocketClient từ path trong application.yml. Response trả về là dict
    (msgpack) thuần, không phải DTO typed - nên đọc theo key.
    """

    def __init__(self, config: RuntimeConfig) -> None:
        # Path must match the server's bound socket file.
        # Path phải trùng file socket server bind.
        self._socket_path = config.get("crypto_engine.socket_path", "/tmp/xime/crypto.sock")

    async def run_demo(self) -> None:
        client = SocketClient(self._socket_path)
        await client.connect()
        try:
            # 1. command - request/response đơn.
            hashed = await client.command("hash", HashRequest(blob_id="report.pdf"))
            _log.info("[1/3] command  hash     -> digest=%s", hashed["digest"][:16] + "...")

            # 2. upload stream - client gửi từng chunk lên engine.
            async with client.upload("encrypt", EncryptRequest(name="report.pdf")) as up:
                await up.write(b"12345")
                await up.write(b"678")
                result = await up.finish()
            _log.info("[2/3] upload   encrypt  -> name=%s total_bytes=%d",
                      result["name"], result["total_bytes"])

            # 3. download stream - engine gửi từng chunk về.
            chunks = [
                chunk async for chunk in client.download(
                    "download", DownloadRequest(name="report.pdf", parts=3)
                )
            ]
            _log.info("[3/3] download download -> %d chunks: %s",
                      len(chunks), [c.decode() for c in chunks])
        finally:
            await client.close()
