from __future__ import annotations

import uuid

from pydantic import BaseModel

# DTOs for the Vault gRPC contract. These Pydantic models ARE the source of
# truth: `xime grpc generate` derives the .proto + contract.json from them.
# DTO cho contract gRPC Vault. Các model Pydantic này LÀ nguồn chân lý:
# `xime grpc generate` suy ra .proto + contract.json từ chúng.


class HashRequest(BaseModel):
    text: str


class HashResponse(BaseModel):
    digest: str
    # uuid.UUID survives 1:1 to the client SDK thanks to the contract.json
    # sidecar (in raw .proto it would only be a string).
    # uuid.UUID giữ nguyên 1:1 sang client SDK nhờ sidecar contract.json (trong
    # .proto trần nó chỉ là string).
    trace_id: uuid.UUID


class StoreRequest(BaseModel):
    name: str


class StoreResponse(BaseModel):
    name: str
    total_bytes: int


class FetchRequest(BaseModel):
    name: str
    parts: int
