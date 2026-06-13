from __future__ import annotations

import hashlib
import uuid
from typing import AsyncIterator

from app.application.dto.vault import (
    FetchRequest,
    HashRequest,
    HashResponse,
    StoreRequest,
    StoreResponse,
)

# Business logic for the Vault service. Kept deliberately trivial - the point of
# this example is the gRPC wiring (code-first + DI + mTLS), not the domain.
# Logic nghiệp vụ Vault. Cố tình để tối giản - trọng tâm ví dụ là đường đi gRPC
# (code-first + DI + mTLS), không phải nghiệp vụ.


class VaultUseCase:
    async def hash(self, request: HashRequest) -> HashResponse:
        digest = hashlib.sha256(request.text.encode("utf-8")).hexdigest()
        return HashResponse(digest=digest, trace_id=uuid.uuid4())

    async def store(self, request: StoreRequest, chunks: AsyncIterator[bytes]) -> StoreResponse:
        total = 0
        async for chunk in chunks:
            total += len(chunk)
        return StoreResponse(name=request.name, total_bytes=total)

    async def fetch(self, request: FetchRequest) -> AsyncIterator[bytes]:
        # Emit `parts` chunks; a real service would stream file bytes here.
        # Phát `parts` chunk; service thật sẽ stream byte file ở đây.
        for i in range(request.parts):
            yield f"{request.name}-part{i}".encode("utf-8")
