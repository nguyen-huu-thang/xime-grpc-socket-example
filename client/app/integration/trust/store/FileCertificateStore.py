from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from cryptography.fernet import Fernet
from xime.core.config.runtime import RuntimeConfig

from app.domain.trust.Certificate import Certificate


class FileCertificateStore:
    """File-backed store for the runtime mTLS certificate (no database).

    Implements LoadCertificatePort + SaveCertificatePort. The single latest
    certificate is persisted as one JSON file; private_key and refresh_token are
    Fernet-encrypted before being written, exactly like the data-service DB
    repository - only the storage medium differs (flat file vs Postgres).
    Store cert mTLS runtime dạng file (không DB). Implement LoadCertificatePort +
    SaveCertificatePort. Cert mới nhất lưu thành một file JSON; private_key và
    refresh_token được mã hoá Fernet trước khi ghi, y như repository DB của
    data-service - chỉ khác phương tiện lưu (file phẳng thay vì Postgres).

    Encryption key resolution (first match wins):
      1. TRUST_CERT_ENCRYPTION_KEY environment variable
      2. trust.cert_encryption_key in application.yml
    The key must stay stable across restarts, otherwise the stored cert cannot
    be decrypted. It is a url-safe base64-encoded 32-byte Fernet key.
    """

    def __init__(self, config: RuntimeConfig) -> None:
        path = config.get("trust.cert_store.path", "./runtime/security/cert.json")
        self._path = Path(path)
        key = os.environ.get("TRUST_CERT_ENCRYPTION_KEY") or config.get("trust.cert_encryption_key")
        if not key:
            raise RuntimeError(
                "Trust certificate encryption key is not configured. "
                "Set TRUST_CERT_ENCRYPTION_KEY or trust.cert_encryption_key in application.yml. "
                "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            )
        self._fernet = Fernet(key.encode() if isinstance(key, str) else key)

    # -- LoadCertificatePort ------------------------------------------------

    async def find_latest(self) -> Certificate | None:
        if not self._path.exists():
            return None
        data = json.loads(self._path.read_text(encoding="utf-8"))
        return Certificate(
            certificate_id=data["certificate_id"],
            service_id=data["service_id"],
            public_cert=data["public_cert"],
            private_key=self._decrypt(data["private_key"]),
            refresh_token_id=data["refresh_token_id"],
            refresh_token=self._decrypt(data["refresh_token"]),
            issued_at=datetime.fromisoformat(data["issued_at"]),
            expires_at=datetime.fromisoformat(data["expires_at"]),
        )

    # -- SaveCertificatePort ------------------------------------------------

    async def save(self, cert: Certificate) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "certificate_id": cert.certificate_id,
            "service_id": cert.service_id,
            "public_cert": cert.public_cert,
            "private_key": self._encrypt(cert.private_key),
            "refresh_token_id": cert.refresh_token_id,
            "refresh_token": self._encrypt(cert.refresh_token),
            "issued_at": cert.issued_at.isoformat(),
            "expires_at": cert.expires_at.isoformat(),
        }
        # Write atomically: write to a temp file then replace, so a crash mid-write
        # never leaves a half-written cert file.
        # Ghi nguyên tử: ghi file tạm rồi thay thế, để sự cố giữa chừng không để
        # lại file cert ghi dở.
        tmp = self._path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        os.replace(tmp, self._path)

    async def delete_all(self) -> None:
        self._path.unlink(missing_ok=True)

    async def delete_expired(self, now: datetime, keep_id: str) -> None:
        # Single-file store keeps only the latest cert, so there is nothing to
        # prune. Kept to satisfy SaveCertificatePort.
        # Store một-file chỉ giữ cert mới nhất nên không có gì để dọn. Giữ method
        # cho khớp SaveCertificatePort.
        return None

    # -- internal -----------------------------------------------------------

    def _encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode()).decode()

    def _decrypt(self, ciphertext: str) -> str:
        return self._fernet.decrypt(ciphertext.encode()).decode()
