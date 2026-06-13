"""Test cho service socket "Crypto Engine".

Hai nhóm:
1. Unit (chạy mọi OS, gồm Windows): logic use case + builder phân giải shape + DTO.
   Không đụng tới Unix socket nên chạy được ngay trên Windows.
2. E2E (chỉ Linux + msgpack): khởi động SocketAdapter thật trên file .sock tạm rồi
   gọi qua SocketClient. Tự skip khi thiếu start_unix_server (Windows) hoặc msgpack.

Bám mẫu: xime framework/tests_temp/socket/test_socket.py
"""
from __future__ import annotations

import asyncio
import hashlib
import importlib.util

import pytest
from pydantic import ValidationError

from app.api.socket.CryptoEngineController import CryptoEngineController
from app.application.dto.crypto import (
    DownloadRequest,
    EncryptRequest,
    HashRequest,
)
from app.application.usecase.CryptoEngineUseCase import CryptoEngineUseCase

HAS_UNIX = hasattr(asyncio, "start_unix_server")
HAS_MSGPACK = importlib.util.find_spec("msgpack") is not None
e2e = pytest.mark.skipif(
    not (HAS_UNIX and HAS_MSGPACK),
    reason="socket e2e cần Unix socket (Linux) + msgpack",
)


class FakeApp:
    """Application giả cho builder: get(cls) trả instance đã dựng sẵn."""

    def __init__(self, instances: dict) -> None:
        self._instances = instances

    def get(self, cls):
        return self._instances[cls]


class _CollectingDownload:
    """Duck-type DownloadStream: gom các write để assert (dùng cho unit test)."""

    def __init__(self) -> None:
        self.chunks: list[bytes] = []

    async def write(self, chunk: bytes) -> None:
        self.chunks.append(chunk)


# ===========================================================================
# 1. Unit - use case (chạy mọi OS)
# ===========================================================================

@pytest.mark.asyncio
async def test_hash_returns_sha256():
    uc = CryptoEngineUseCase()
    resp = await uc.hash(HashRequest(blob_id="report.pdf"))
    assert resp.digest == hashlib.sha256(b"report.pdf").hexdigest()


@pytest.mark.asyncio
async def test_encrypt_counts_uploaded_bytes():
    # Dùng UploadStream cụ thể (queue-backed) như adapter thật, không cần socket.
    from xime.adapters.socket._session import UploadStream as QueueUploadStream
    from xime.adapters.socket._session import _END

    queue: asyncio.Queue = asyncio.Queue()
    await queue.put(b"12345")
    await queue.put(b"678")
    await queue.put(_END)

    uc = CryptoEngineUseCase()
    resp = await uc.encrypt(EncryptRequest(name="report.pdf"), QueueUploadStream(queue))
    assert resp.name == "report.pdf"
    assert resp.total_bytes == 8


@pytest.mark.asyncio
async def test_download_emits_parts_chunks():
    uc = CryptoEngineUseCase()
    sink = _CollectingDownload()
    await uc.download(DownloadRequest(name="report.pdf", parts=3), sink)
    assert sink.chunks == [
        b"report.pdf-chunk0",
        b"report.pdf-chunk1",
        b"report.pdf-chunk2",
    ]


# ===========================================================================
# 2. Unit - builder (chạy mọi OS)
# ===========================================================================

def _build_table(server_id: str = "crypto"):
    from xime.adapters.socket.routing._builder import SocketEndpointBuilder

    controller = CryptoEngineController(CryptoEngineUseCase())
    app = FakeApp({CryptoEngineController: controller})
    return SocketEndpointBuilder(app, server_id).build([CryptoEngineController])


def test_builder_resolves_all_shapes():
    table = _build_table()
    assert table["hash"].shape == "command"
    assert table["encrypt"].shape == "upload"
    assert table["encrypt"].stream_param == "upload"
    assert table["download"].shape == "download"
    assert table["download"].response_type is None


def test_builder_filters_by_server_id():
    # server_id khác "crypto" -> controller không được nhận, bảng rỗng.
    assert _build_table(server_id="other") == {}


# ===========================================================================
# 3. Unit - DTO (chạy mọi OS)
# ===========================================================================

def test_dto_requires_fields():
    HashRequest(blob_id="x")  # hợp lệ
    with pytest.raises(ValidationError):
        HashRequest()  # thiếu blob_id


# ===========================================================================
# 4. E2E - chỉ Linux + msgpack
# ===========================================================================

@e2e
@pytest.mark.asyncio
async def test_e2e_command_upload_download(tmp_path):
    from xime.adapters.socket import SocketClient
    from xime.adapters.socket._adapter import SocketAdapter
    from xime.adapters.socket._config import SocketServerConfig
    from xime.adapters.socket.routing._builder import SocketEndpointBuilder

    sock_path = str(tmp_path / "crypto.sock")
    controller = CryptoEngineController(CryptoEngineUseCase())

    adapter = SocketAdapter("crypto", path=sock_path)
    adapter._config = SocketServerConfig(path=sock_path)
    adapter._table = SocketEndpointBuilder(
        FakeApp({CryptoEngineController: controller}), "crypto"
    ).build([CryptoEngineController])

    server = await asyncio.start_unix_server(adapter._handle_connection, path=sock_path)
    async with server:
        client = SocketClient(sock_path)
        await client.connect()
        try:
            # command
            resp = await client.command("hash", HashRequest(blob_id="report.pdf"))
            assert resp["digest"] == hashlib.sha256(b"report.pdf").hexdigest()

            # upload
            async with client.upload("encrypt", EncryptRequest(name="report.pdf")) as up:
                await up.write(b"12345")
                await up.write(b"678")
                result = await up.finish()
            assert result["name"] == "report.pdf"
            assert result["total_bytes"] == 8

            # download
            chunks = [
                c async for c in client.download(
                    "download", DownloadRequest(name="report.pdf", parts=3)
                )
            ]
            assert chunks == [
                b"report.pdf-chunk0",
                b"report.pdf-chunk1",
                b"report.pdf-chunk2",
            ]
        finally:
            await client.close()


@e2e
@pytest.mark.asyncio
async def test_e2e_concurrent_uploads(tmp_path):
    """Hai upload đồng thời trên cùng connection không lẫn dữ liệu (multiplex)."""
    from xime.adapters.socket import SocketClient
    from xime.adapters.socket._adapter import SocketAdapter
    from xime.adapters.socket._config import SocketServerConfig
    from xime.adapters.socket.routing._builder import SocketEndpointBuilder

    sock_path = str(tmp_path / "crypto.sock")
    controller = CryptoEngineController(CryptoEngineUseCase())
    adapter = SocketAdapter("crypto", path=sock_path)
    adapter._config = SocketServerConfig(path=sock_path)
    adapter._table = SocketEndpointBuilder(
        FakeApp({CryptoEngineController: controller}), "crypto"
    ).build([CryptoEngineController])

    server = await asyncio.start_unix_server(adapter._handle_connection, path=sock_path)
    async with server:
        client = SocketClient(sock_path)
        await client.connect()
        try:
            async def run_upload(payloads):
                async with client.upload("encrypt", EncryptRequest(name="x")) as up:
                    for p in payloads:
                        await up.write(p)
                    return await up.finish()

            r1, r2 = await asyncio.gather(
                run_upload([b"aaaa", b"bb"]),      # 6
                run_upload([b"c", b"dddddddd"]),   # 9
            )
            assert {r1["total_bytes"], r2["total_bytes"]} == {6, 9}
        finally:
            await client.close()
