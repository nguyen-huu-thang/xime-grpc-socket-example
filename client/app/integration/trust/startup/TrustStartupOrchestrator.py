import logging

from app.integration.trust.certificate.TrustCertificateSynchronizer import TrustCertificateSynchronizer
from app.integration.trust.publicca.TrustRootCertificateInitializer import TrustRootCertificateInitializer

_log = logging.getLogger(__name__)


class TrustStartupOrchestrator:
    """
    Runs the trust bootstrap sequence at application startup.

    Ordering is strict:
      1. Load root CA certificate from disk   → enables verifying the peer
      2. Synchronize mTLS certificate          → populates the cert resolver

    This example covers the certificate / mTLS path only (bootstrap + rotate);
    it does not sync JWT verification keys (that concern is orthogonal to gRPC
    transport - see data-service for the full key cluster). Step 2 must run
    before the gRPC adapter serves its first request, because the dynamic-TLS
    provider reads the resolver that step 2 populates.
    Ví dụ này chỉ phủ phần cert/mTLS (bootstrap + rotate); KHÔNG đồng bộ key
    verify JWT (chuyện đó tách rời transport gRPC - xem data-service nếu cần cụm
    key đầy đủ). Bước 2 phải chạy trước khi adapter gRPC phục vụ request đầu, vì
    provider TLS động đọc resolver mà bước 2 nạp.
    """

    def __init__(
        self,
        root_ca_init: TrustRootCertificateInitializer,
        cert_sync: TrustCertificateSynchronizer,
    ) -> None:
        self._root_ca_init = root_ca_init
        self._cert_sync = cert_sync

    async def post_construct(self) -> None:
        _log.info("Trust startup: loading root CA certificate.")
        self._root_ca_init.initialize()

        _log.info("Trust startup: synchronizing mTLS certificate.")
        await self._cert_sync.synchronize_on_startup()

        _log.info("Trust startup complete.")
