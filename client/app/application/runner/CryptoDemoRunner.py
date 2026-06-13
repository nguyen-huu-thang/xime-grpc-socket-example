from __future__ import annotations

import asyncio
import logging

from app.application.usecase.CryptoEngineCallerUseCase import CryptoEngineCallerUseCase

_log = logging.getLogger(__name__)


class CryptoDemoRunner:
    """PostConstruct hook that calls the socket Crypto Engine once at startup.

    Unix Domain Sockets exist only on Linux/macOS, so on Windows (dev) this skips
    with a notice instead of failing - the gRPC demo still runs. On Linux it
    exercises command + upload + download over the socket.
    Hook PostConstruct gọi Crypto Engine qua socket một lần lúc khởi động. UDS chỉ
    có trên Linux/macOS, nên trên Windows (dev) sẽ bỏ qua kèm thông báo thay vì lỗi
    - demo gRPC vẫn chạy. Trên Linux chạy command + upload + download qua socket.
    """

    def __init__(self, caller: CryptoEngineCallerUseCase) -> None:
        self._caller = caller

    async def post_construct(self) -> None:
        if not hasattr(asyncio, "open_unix_connection"):
            _log.info(
                "Crypto Engine demo: bỏ qua trên nền tảng không có Unix socket "
                "(vd Windows). Chạy thật trên Linux."
            )
            return
        _log.info("Crypto Engine demo: calling the engine over the Unix socket...")
        try:
            await self._caller.run_demo()
            _log.info("Crypto Engine demo: done.")
        except Exception as e:
            # Socket server chưa chạy hoặc sai path - log rõ, không làm sập app.
            _log.error("Crypto Engine demo failed (is the socket server running?): %s", e)
