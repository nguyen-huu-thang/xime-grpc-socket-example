from __future__ import annotations

import logging

from clients.vault import FetchRequest, HashRequest, StoreRequest, VaultClient

_log = logging.getLogger(__name__)


class VaultCallerUseCase:
    """Calls the Vault gRPC server through the generated SDK client.

    VaultClient is a generated SDK class. The framework builds it with a managed
    dynamic-mTLS channel (configure_grpc_clients + grpc.clients.vault in yaml) and
    injects it here - no channel construction, no protobuf marshalling by hand.
    VaultClient là class SDK sinh tự động. Framework dựng nó với channel mTLS động
    có quản lý (configure_grpc_clients + grpc.clients.vault trong yaml) và inject
    vào đây - không dựng channel, không marshal protobuf bằng tay.
    """

    def __init__(self, vault: VaultClient) -> None:
        self._vault = vault

    async def run_demo(self) -> None:
        # 1. unary - DTO trả về là Pydantic typed, trace_id là uuid.UUID thật.
        hashed = await self._vault.hash(HashRequest(text="hello xime"))
        _log.info("[1/3] unary       hash  -> digest=%s trace_id=%s (type=%s)",
                  hashed.digest[:16] + "...", hashed.trace_id, type(hashed.trace_id).__name__)

        # 2. client-streaming - truyền async generator các chunk bytes.
        async def chunks():
            yield b"12345"
            yield b"678"
        stored = await self._vault.store(StoreRequest(name="report.pdf"), chunks())
        _log.info("[2/3] client-stream store -> name=%s total_bytes=%d", stored.name, stored.total_bytes)

        # 3. server-streaming - async iterate các chunk trả về.
        parts = [chunk async for chunk in self._vault.fetch(FetchRequest(name="report.pdf", parts=3))]
        _log.info("[3/3] server-stream fetch -> %d chunks: %s", len(parts), [p.decode() for p in parts])
