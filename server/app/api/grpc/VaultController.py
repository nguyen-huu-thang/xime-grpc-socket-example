from __future__ import annotations

from xime.core.contract import DownloadStream, UploadStream, command, stream

from app.application.dto.vault import (
    FetchRequest,
    HashRequest,
    HashResponse,
    StoreRequest,
    StoreResponse,
)
from app.application.usecase.VaultUseCase import VaultUseCase

# Code-First gRPC controller. No protobuf imports, no Servicer base class: the
# decorators + Pydantic type hints below are all the framework needs to generate
# the .proto and to wire the RPC handlers dynamically at startup.
# Controller gRPC Code-First. Không import protobuf, không kế thừa Servicer: các
# decorator + type hint Pydantic dưới đây là tất cả những gì framework cần để
# sinh .proto và nối dây handler RPC động lúc khởi động.


class VaultController:
    # server_id drives the proto package (xime.<server_id>) AND selects which
    # GrpcAdapter serves this controller. "default" => served by GrpcAdapter().
    # server_id quyết định package proto (xime.<server_id>) VÀ chọn GrpcAdapter
    # nào phục vụ controller. "default" => phục vụ bởi GrpcAdapter() mặc định.
    server_id = "default"

    def __init__(self, usecase: VaultUseCase) -> None:
        # Constructor injection - framework builds VaultUseCase and passes it in.
        # Constructor injection - framework dựng VaultUseCase và truyền vào.
        self._usecase = usecase

    @command("hash")
    async def hash(self, request: HashRequest) -> HashResponse:
        return await self._usecase.hash(request)

    @stream("store")
    async def store(self, request: StoreRequest, upload: UploadStream) -> StoreResponse:
        # Client-streaming: `upload` yields the uploaded byte chunks.
        # Client-streaming: `upload` phát ra các chunk byte client gửi lên.
        return await self._usecase.store(request, upload)

    @stream("fetch")
    async def fetch(self, request: FetchRequest, download: DownloadStream) -> None:
        # Server-streaming: write each chunk to `download`.
        # Server-streaming: ghi từng chunk vào `download`.
        async for chunk in self._usecase.fetch(request):
            await download.write(chunk)
