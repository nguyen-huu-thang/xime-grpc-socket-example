from __future__ import annotations

import hashlib

from xime.core.contract import DownloadStream, UploadStream

from app.application.dto.crypto import (
    DownloadRequest,
    EncryptRequest,
    EncryptResponse,
    HashRequest,
    HashResponse,
)

# Business logic for the "Crypto Engine" socket service. Stands in for a native
# engine (C++/Rust/Go) doing heavy crypto over local IPC. Kept deliberately
# trivial - the point of this example is the socket transport (UDS + msgpack +
# streaming + session multiplexing), not the cryptography.
# Logic cho service socket "Crypto Engine". Đóng vai một native engine (C++/Rust/Go)
# làm crypto nặng qua IPC cùng máy. Cố tình tối giản - trọng tâm ví dụ là đường đi
# socket (UDS + msgpack + streaming + multiplex session), không phải nghiệp vụ crypto.


class CryptoEngineUseCase:
    async def hash(self, request: HashRequest) -> HashResponse:
        digest = hashlib.sha256(request.blob_id.encode("utf-8")).hexdigest()
        return HashResponse(digest=digest)

    async def encrypt(self, request: EncryptRequest, upload: UploadStream) -> EncryptResponse:
        # Count the uploaded bytes; a real engine would encrypt each chunk.
        # Đếm byte upload; engine thật sẽ mã hoá từng chunk.
        total = 0
        async for chunk in upload:
            total += len(chunk)
        return EncryptResponse(name=request.name, total_bytes=total)

    async def download(self, request: DownloadRequest, download: DownloadStream) -> None:
        # Emit `parts` chunks; a real engine would stream processed bytes back.
        # Phát `parts` chunk; engine thật sẽ stream byte đã xử lý về.
        for i in range(request.parts):
            await download.write(f"{request.name}-chunk{i}".encode("utf-8"))
