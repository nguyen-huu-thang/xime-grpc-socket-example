from __future__ import annotations

from xime.core.contract import DownloadStream, UploadStream, command, stream

from app.application.dto.crypto import (
    DownloadRequest,
    EncryptRequest,
    EncryptResponse,
    HashRequest,
    HashResponse,
)
from app.application.usecase.CryptoEngineUseCase import CryptoEngineUseCase

# Socket controller for a native "Crypto Engine", served over a Unix Domain
# Socket. Note it uses the SAME @command/@stream + Pydantic contract as the gRPC
# VaultController - only the transport differs. No protobuf, no codegen: requests
# and responses travel as msgpack dicts.
# Controller socket cho "Crypto Engine" native, phục vụ qua Unix Domain Socket.
# Dùng CÙNG contract @command/@stream + Pydantic như VaultController gRPC - chỉ
# khác transport. Không protobuf, không sinh mã: request/response đi dạng dict msgpack.


class CryptoEngineController:
    # server_id selects which SocketAdapter serves this controller AND the auto
    # socket path (<socket.dir>/crypto.sock). It MUST match SocketAdapter("crypto")
    # in main.py - if they differ, the adapter serves nothing (silent), exactly
    # like the gRPC server_id pitfall.
    # server_id chọn SocketAdapter phục vụ controller này VÀ path socket tự sinh.
    # PHẢI khớp SocketAdapter("crypto") trong main.py - lệch nhau thì adapter không
    # phục vụ gì (im lặng), y hệt bẫy server_id bên gRPC.
    server_id = "crypto"

    def __init__(self, usecase: CryptoEngineUseCase) -> None:
        # Constructor injection - framework builds CryptoEngineUseCase and passes it.
        # Constructor injection - framework dựng CryptoEngineUseCase và truyền vào.
        self._usecase = usecase

    @command("hash")
    async def hash(self, request: HashRequest) -> HashResponse:
        return await self._usecase.hash(request)

    @stream("encrypt")
    async def encrypt(self, request: EncryptRequest, upload: UploadStream) -> EncryptResponse:
        # Client-streaming: `upload` yields the uploaded byte chunks.
        # Client-streaming: `upload` phát ra các chunk byte client gửi lên.
        return await self._usecase.encrypt(request, upload)

    @stream("download")
    async def download(self, request: DownloadRequest, download: DownloadStream) -> None:
        # Server-streaming: the use case writes each chunk to `download`.
        # Server-streaming: use case ghi từng chunk vào `download`.
        await self._usecase.download(request, download)
