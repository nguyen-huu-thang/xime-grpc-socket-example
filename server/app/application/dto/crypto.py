from __future__ import annotations

from pydantic import BaseModel

# DTOs for the Crypto Engine socket contract. Unlike the gRPC DTOs, these travel
# as msgpack dicts (request.model_dump() -> msgpack.packb), so every field MUST be
# a msgpack-friendly primitive: str / int / float / bool / bytes / list / dict.
# No uuid.UUID or Decimal here - they would raise at msgpack.packb. That is the
# key contrast with the gRPC sidecar (which keeps UUID/Decimal fidelity 1:1).
# DTO cho contract socket Crypto Engine. Khác DTO gRPC, chúng đi dưới dạng dict
# msgpack nên mọi field PHẢI là kiểu cơ bản msgpack gói được: str/int/float/bool/
# bytes/list/dict. KHÔNG uuid.UUID hay Decimal vì sẽ lỗi lúc msgpack.packb - đây
# là điểm tương phản với sidecar gRPC (giữ fidelity UUID/Decimal 1:1).


class HashRequest(BaseModel):
    blob_id: str


class HashResponse(BaseModel):
    digest: str


class EncryptRequest(BaseModel):
    name: str


class EncryptResponse(BaseModel):
    name: str
    total_bytes: int


class DownloadRequest(BaseModel):
    name: str
    parts: int
