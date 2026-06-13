from __future__ import annotations

from pydantic import BaseModel

# Request DTOs the socket client sends to the Crypto Engine. There is NO generated
# SDK for the socket transport (unlike gRPC), so the client declares its own
# request models; they are turned into msgpack dicts via model_dump(). Responses
# come back as plain dicts, so no response models are needed here.
# Keep every field msgpack-friendly (str/int/float/bool/bytes/list/dict).
# DTO request mà client socket gửi cho Crypto Engine. KHÔNG có SDK sinh tự động
# cho transport socket (khác gRPC), nên client tự khai model request; chúng được
# chuyển thành dict msgpack qua model_dump(). Response trả về là dict thuần nên
# không cần model response. Mọi field phải msgpack-friendly.


class HashRequest(BaseModel):
    blob_id: str


class EncryptRequest(BaseModel):
    name: str


class DownloadRequest(BaseModel):
    name: str
    parts: int
