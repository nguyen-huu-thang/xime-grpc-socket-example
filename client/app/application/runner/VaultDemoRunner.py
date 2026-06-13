from __future__ import annotations

import logging

from app.application.usecase.VaultCallerUseCase import VaultCallerUseCase
from app.integration.trust.startup.TrustStartupOrchestrator import TrustStartupOrchestrator

_log = logging.getLogger(__name__)


class VaultDemoRunner:
    """PostConstruct hook that calls the Vault server once at startup, for demo.

    Depends on TrustStartupOrchestrator purely to force ordering: the framework
    starts a component's PostConstruct after its dependencies', so listing the
    orchestrator here guarantees the mTLS cert is bootstrapped into the resolver
    before we open the (dynamic-mTLS) channel to the server.
    Hook PostConstruct gọi server Vault một lần lúc khởi động, để demo. Phụ thuộc
    TrustStartupOrchestrator chỉ để ép thứ tự: framework chạy PostConstruct của
    một component sau các dependency của nó, nên khai orchestrator ở đây đảm bảo
    cert mTLS đã được bootstrap vào resolver trước khi ta mở channel (mTLS động)
    tới server.
    """

    def __init__(
        self,
        caller: VaultCallerUseCase,
        _trust: TrustStartupOrchestrator,
    ) -> None:
        self._caller = caller

    async def post_construct(self) -> None:
        _log.info("Vault demo: calling the server over dynamic mTLS...")
        try:
            await self._caller.run_demo()
            _log.info("Vault demo: done. (App now idles - press Ctrl+C to exit.)")
        except Exception as e:
            # Server chưa chạy hoặc mTLS chưa sẵn sàng - log rõ, không làm sập app.
            _log.error("Vault demo failed (is the server running?): %s", e)
