"""Unit test cho VaultUseCase (logic gRPC Vault), chạy mọi OS.

Use case không phụ thuộc transport (không gRPC, không mTLS, không Trust), nên test
được trực tiếp như logic thuần - đây cũng là bài học: tách nghiệp vụ khỏi đường đi
gRPC để test nhanh và độc lập. Phần dây gRPC code-first + mTLS được verify chạy
live (xem README), còn logic thì kiểm ở đây.

Đối xứng với tests/socket/test_crypto_engine.py phía Crypto Engine.
"""
from __future__ import annotations

import hashlib
import uuid

import pytest

from app.application.dto.vault import (
    FetchRequest,
    HashRequest,
    StoreRequest,
)
from app.application.usecase.VaultUseCase import VaultUseCase


async def _aiter(*chunks: bytes):
    # Dựng một async iterator chunk byte như client-stream của adapter cấp.
    # Build an async iterator of byte chunks like the adapter feeds in.
    for c in chunks:
        yield c


@pytest.mark.asyncio
async def test_hash_returns_sha256_and_real_uuid():
    uc = VaultUseCase()
    resp = await uc.hash(HashRequest(text="hello xime"))
    assert resp.digest == hashlib.sha256(b"hello xime").hexdigest()
    # trace_id là uuid.UUID thật (minh hoạ sidecar giữ kiểu 1:1), không phải str.
    # trace_id is a real uuid.UUID (the sidecar keeps the type 1:1), not a str.
    assert isinstance(resp.trace_id, uuid.UUID)


@pytest.mark.asyncio
async def test_hash_differs_per_call_trace_id():
    uc = VaultUseCase()
    a = await uc.hash(HashRequest(text="x"))
    b = await uc.hash(HashRequest(text="x"))
    assert a.digest == b.digest          # cùng input -> cùng digest
    assert a.trace_id != b.trace_id      # mỗi lần gọi -> trace_id mới


@pytest.mark.asyncio
async def test_store_counts_uploaded_bytes():
    uc = VaultUseCase()
    resp = await uc.store(StoreRequest(name="report.pdf"), _aiter(b"12345", b"678"))
    assert resp.name == "report.pdf"
    assert resp.total_bytes == 8


@pytest.mark.asyncio
async def test_store_empty_stream_is_zero_bytes():
    uc = VaultUseCase()
    resp = await uc.store(StoreRequest(name="empty"), _aiter())
    assert resp.total_bytes == 0


@pytest.mark.asyncio
async def test_fetch_emits_parts_chunks():
    uc = VaultUseCase()
    chunks = [chunk async for chunk in uc.fetch(FetchRequest(name="report.pdf", parts=3))]
    assert chunks == [
        b"report.pdf-part0",
        b"report.pdf-part1",
        b"report.pdf-part2",
    ]


@pytest.mark.asyncio
async def test_fetch_zero_parts_emits_nothing():
    uc = VaultUseCase()
    chunks = [chunk async for chunk in uc.fetch(FetchRequest(name="x", parts=0))]
    assert chunks == []
