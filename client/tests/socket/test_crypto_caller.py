"""Test cho phần client gọi socket "Crypto Engine".

1. Unit (mọi OS): CryptoEngineCallerUseCase đọc đúng socket_path từ config.
2. E2E (chỉ Linux + msgpack): dựng một socket server engine tối giản trong tiến
   trình, chạy run_demo() của use case end-to-end (smoke: hoàn tất không lỗi).
"""
from __future__ import annotations

import asyncio
import hashlib
import importlib.util

import pytest

from xime.core.config.runtime import RuntimeConfig

from app.application.usecase.CryptoEngineCallerUseCase import CryptoEngineCallerUseCase

HAS_UNIX = hasattr(asyncio, "start_unix_server")
HAS_MSGPACK = importlib.util.find_spec("msgpack") is not None
e2e = pytest.mark.skipif(
    not (HAS_UNIX and HAS_MSGPACK),
    reason="socket e2e cần Unix socket (Linux) + msgpack",
)

# ---------------------------------------------------------------------------
# Stub models + engine cho e2e test - phải ở module level để
# typing.get_type_hints() resolve được (from __future__ import annotations
# biến annotation thành string, cần tìm được trong globals).
# ---------------------------------------------------------------------------
if HAS_UNIX and HAS_MSGPACK:
    from pydantic import BaseModel

    from xime.core.contract import DownloadStream, UploadStream, command, stream

    class HReq(BaseModel):
        blob_id: str

    class HResp(BaseModel):
        digest: str

    class EReq(BaseModel):
        name: str

    class EResp(BaseModel):
        name: str
        total_bytes: int

    class DReq(BaseModel):
        name: str
        parts: int

    class Engine:
        server_id = "crypto"

        @command("hash")
        async def hash(self, request: HReq) -> HResp:
            return HResp(digest=hashlib.sha256(request.blob_id.encode()).hexdigest())

        @stream("encrypt")
        async def encrypt(self, request: EReq, upload: UploadStream) -> EResp:
            total = 0
            async for chunk in upload:
                total += len(chunk)
            return EResp(name=request.name, total_bytes=total)

        @stream("download")
        async def download(self, request: DReq, download: DownloadStream) -> None:
            for i in range(request.parts):
                await download.write(f"{request.name}-chunk{i}".encode())

    class FakeApp:
        def __init__(self, instances):
            self._instances = instances

        def get(self, cls):
            return self._instances[cls]


# ===========================================================================
# 1. Unit - đọc cấu hình (chạy mọi OS)
# ===========================================================================

def test_socket_path_from_config():
    cfg = RuntimeConfig.from_dict({"crypto_engine": {"socket_path": "/custom/x.sock"}})
    uc = CryptoEngineCallerUseCase(cfg)
    assert uc._socket_path == "/custom/x.sock"


def test_socket_path_default_when_absent():
    cfg = RuntimeConfig.from_dict({})
    uc = CryptoEngineCallerUseCase(cfg)
    assert uc._socket_path == "/tmp/xime/crypto.sock"


# ===========================================================================
# 2. E2E - chỉ Linux + msgpack
# ===========================================================================

@e2e
@pytest.mark.asyncio
async def test_e2e_caller_runs_against_engine(tmp_path):
    from xime.adapters.socket._adapter import SocketAdapter
    from xime.adapters.socket._config import SocketServerConfig
    from xime.adapters.socket.routing._builder import SocketEndpointBuilder

    sock_path = str(tmp_path / "crypto.sock")
    adapter = SocketAdapter("crypto", path=sock_path)
    adapter._config = SocketServerConfig(path=sock_path)
    adapter._table = SocketEndpointBuilder(
        FakeApp({Engine: Engine()}), "crypto"
    ).build([Engine])

    server = await asyncio.start_unix_server(adapter._handle_connection, path=sock_path)
    async with server:
        cfg = RuntimeConfig.from_dict({"crypto_engine": {"socket_path": sock_path}})
        uc = CryptoEngineCallerUseCase(cfg)
        # Smoke: gọi đủ command + upload + download qua SocketClient, không ném lỗi.
        await uc.run_demo()
