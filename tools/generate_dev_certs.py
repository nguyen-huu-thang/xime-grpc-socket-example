#!/usr/bin/env python3
"""Generate self-signed dev certificates so the example runs WITHOUT a Trust Service.

Sinh cert dev self-signed để chạy ví dụ mà KHÔNG cần Trust Service.

Why this exists / Vì sao có script này
--------------------------------------
The mTLS lifecycle in this example has two phases:

1. Bootstrap (one-time): the app talks to a Trust Service to exchange a bootstrap
   token for a real runtime certificate, then saves it to the local file store.
2. Runtime (every later start): the app loads the certificate from the file store
   (``runtime/security/cert.json``) and serves mTLS. It does NOT contact the Trust
   Service in real time - it only calls Trust again if the cert nears expiry and
   needs rotation (see TrustCertificateSynchronizer).

So to just *run and study the example*, you do not need a Trust Service at all:
you only need a valid ``cert.json`` + ``ca-cert.pem`` already on disk (the
"ACTIVE" startup state). This script creates exactly that:

- one self-signed CA (the root of trust both apps verify against),
- one leaf cert for the server  (service_id "vault-server"),
- one leaf cert for the client  (service_id "vault-client"),

both leaves signed by the same CA, written in the exact on-disk format the
FileCertificateStore expects (private_key Fernet-encrypted with the key from each
app's application.yml).

Vòng đời mTLS ví dụ này có 2 giai đoạn: (1) bootstrap một lần với Trust Service để
đổi lấy cert runtime, lưu xuống file; (2) các lần chạy sau chỉ LOAD cert từ file,
KHÔNG gọi Trust realtime (chỉ gọi lại khi cert sắp hết hạn cần rotate). Vì vậy để
chạy/nghiên cứu ví dụ thì không cần Trust Service - chỉ cần sẵn cert.json +
ca-cert.pem hợp lệ. Script này tạo đúng các file đó: 1 CA self-signed + 2 leaf cert
(server, client) cùng ký bởi CA, đúng format mà FileCertificateStore đọc.

To see the REAL bootstrap + rotation flow against a Trust Service, study or run the
public Trust Service: https://github.com/nguyen-huu-thang/trust-service

Usage / Cách dùng
-----------------
From the repo root (chạy ở thư mục gốc repo):

    pip install cryptography
    python tools/generate_dev_certs.py

Then start the apps (no Trust Service needed):

    cd server && python -m app.main
    cd client && python -m app.main
"""
from __future__ import annotations

import base64
import datetime as dt
import ipaddress
import json
import re
import secrets
import sys
from pathlib import Path

try:
    from cryptography import x509
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID
except ImportError:
    sys.exit(
        "Thiếu thư viện 'cryptography'. Cài bằng: pip install cryptography\n"
        "Missing 'cryptography'. Install with: pip install cryptography"
    )

# Repo root = parent of this tools/ directory, so the script works from any CWD.
# Gốc repo = thư mục cha của tools/, để script chạy đúng dù CWD ở đâu.
REPO_ROOT = Path(__file__).resolve().parent.parent

# Each app's identity. service_id MUST match trust.service_id in its application.yml.
# Định danh mỗi app. service_id PHẢI khớp trust.service_id trong application.yml.
APPS = {
    "server": "vault-server",
    "client": "vault-client",
}

# Validity window. issued_at = now keeps needs_rotation() False (threshold 150 days),
# so the apps never try to call the Trust Service for rotation while you experiment.
# Cửa sổ hiệu lực. issued_at = now giữ needs_rotation() = False (ngưỡng 150 ngày),
# nên app không gọi Trust để rotate trong lúc bạn thử nghiệm.
VALIDITY_DAYS = 365


def _read_encryption_key(app_dir: Path) -> str:
    """Read trust.cert_encryption_key from an app's application.yml (no PyYAML needed).

    The FileCertificateStore decrypts private_key/refresh_token with this Fernet key,
    so we MUST encrypt with the same one. A tiny regex avoids a PyYAML dependency.
    Đọc trust.cert_encryption_key từ application.yml (không cần PyYAML). FileCertificateStore
    giải mã private_key/refresh_token bằng key Fernet này nên ta PHẢI mã hoá cùng key.
    """
    yml = app_dir / "resources" / "application.yml"
    text = yml.read_text(encoding="utf-8")
    match = re.search(r'^\s*cert_encryption_key:\s*"?([^"\n]+)"?\s*$', text, re.MULTILINE)
    if not match:
        sys.exit(f"Không tìm thấy trust.cert_encryption_key trong {yml}")
    return match.group(1).strip()


def _new_key() -> ec.EllipticCurvePrivateKey:
    # EC P-256 to match the real Trust Service certificates (compact, fast).
    # EC P-256 cho khớp cert thật của Trust Service (gọn, nhanh).
    return ec.generate_private_key(ec.SECP256R1())


def _b64_der_cert(cert: x509.Certificate) -> str:
    # Store the cert as raw base64 DER (no PEM header), exactly like the Trust
    # Service output; PemNormalizer re-wraps it to PEM at use time.
    # Lưu cert dạng base64 DER thô (không header PEM), y như output Trust Service;
    # PemNormalizer sẽ bọc lại thành PEM lúc dùng.
    return base64.b64encode(cert.public_bytes(serialization.Encoding.DER)).decode()


def _b64_der_key(key: ec.EllipticCurvePrivateKey) -> str:
    der = key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    return base64.b64encode(der).decode()


def _make_ca() -> tuple[ec.EllipticCurvePrivateKey, x509.Certificate]:
    key = _new_key()
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, "Xime Dev Root CA"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Xime Example"),
    ])
    now = dt.datetime.now(dt.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - dt.timedelta(minutes=5))
        .not_valid_after(now + dt.timedelta(days=3650))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=False, content_commitment=False,
                key_encipherment=False, data_encipherment=False,
                key_agreement=False, key_cert_sign=True, crl_sign=True,
                encipher_only=False, decipher_only=False,
            ),
            critical=True,
        )
        .sign(key, hashes.SHA256())
    )
    return key, cert


def _make_leaf(
    service_id: str,
    ca_key: ec.EllipticCurvePrivateKey,
    ca_cert: x509.Certificate,
) -> tuple[ec.EllipticCurvePrivateKey, x509.Certificate]:
    key = _new_key()
    subject = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, service_id),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Xime Example"),
    ])
    now = dt.datetime.now(dt.timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(ca_cert.subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - dt.timedelta(minutes=5))
        .not_valid_after(now + dt.timedelta(days=VALIDITY_DAYS))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        # SAN: gRPC/BoringSSL verifies the hostname against the SAN (CN is ignored),
        # so the server cert MUST list "localhost"/127.0.0.1; harmless on the client.
        # SAN: gRPC/BoringSSL verify hostname theo SAN (bỏ qua CN), nên cert server
        # PHẢI có "localhost"/127.0.0.1; phía client để cũng không sao.
        .add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName("localhost"),
                x509.IPAddress(ipaddress.ip_address("127.0.0.1")),
                x509.IPAddress(ipaddress.ip_address("::1")),
            ]),
            critical=False,
        )
        # Both EKUs so the same leaf works as a server identity and a client
        # identity under mutual TLS.
        # Cả hai EKU để cùng leaf vừa làm danh tính server vừa làm client trong mTLS.
        .add_extension(
            x509.ExtendedKeyUsage([
                ExtendedKeyUsageOID.SERVER_AUTH,
                ExtendedKeyUsageOID.CLIENT_AUTH,
            ]),
            critical=False,
        )
        .sign(ca_key, hashes.SHA256())
    )
    return key, cert


def _short_id() -> str:
    # Opaque id, just needs to be unique-ish for logs / file fields.
    # Id mờ, chỉ cần đủ duy nhất cho log / field file.
    return secrets.token_urlsafe(16)


def main() -> None:
    print("Generating dev CA + server/client certs (no Trust Service needed)...")
    print("Sinh CA + cert server/client cho dev (không cần Trust Service)...\n")

    ca_key, ca_cert = _make_ca()
    ca_pem = ca_cert.public_bytes(serialization.Encoding.PEM).decode()

    now = dt.datetime.now(dt.timezone.utc)
    expires = now + dt.timedelta(days=VALIDITY_DAYS)

    for app, service_id in APPS.items():
        app_dir = REPO_ROOT / app
        sec_dir = app_dir / "runtime" / "security"
        sec_dir.mkdir(parents=True, exist_ok=True)

        key, cert = _make_leaf(service_id, ca_key, ca_cert)
        fernet = Fernet(_read_encryption_key(app_dir).encode())

        # refresh_token is only consumed during rotation (a Trust call). With a fresh
        # issued_at the apps never rotate here, so a placeholder is fine.
        # refresh_token chỉ dùng khi rotate (gọi Trust). issued_at mới nên app không
        # rotate, để placeholder là đủ.
        record = {
            "certificate_id": _short_id(),
            "service_id": service_id,
            "public_cert": _b64_der_cert(cert),
            "private_key": fernet.encrypt(_b64_der_key(key).encode()).decode(),
            "refresh_token_id": _short_id(),
            "refresh_token": fernet.encrypt(b"dev-no-rotation-placeholder").decode(),
            "issued_at": now.isoformat(),
            "expires_at": expires.isoformat(),
        }

        (sec_dir / "cert.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
        (sec_dir / "ca-cert.pem").write_text(ca_pem, encoding="utf-8")

        print(f"  [{app}] service_id={service_id}")
        print(f"         {sec_dir / 'cert.json'}")
        print(f"         {sec_dir / 'ca-cert.pem'}")

    print("\nDone. Both apps now start in the ACTIVE state and serve mTLS without Trust.")
    print("Xong. Cả hai app khởi động ở trạng thái ACTIVE, phục vụ mTLS mà không cần Trust.")
    print("\nNote: these are DEV-ONLY self-signed certs. Do not use in production.")
    print("Lưu ý: đây là cert self-signed CHỈ cho dev, đừng dùng cho production.")


if __name__ == "__main__":
    main()
