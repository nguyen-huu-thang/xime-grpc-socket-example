from xime.adapters.grpc import configure_grpc_tls
from xime.adapters.grpc.codefirst import configure_grpc_codefirst

from app.integration.trust.ssl.TrustGrpcCertificateProvider import TrustGrpcCertificateProvider

# Code-first: scan controllers here for `xime grpc generate` and for dynamic
# serving. This package must ALSO be in dependency.scan() so DI builds the
# controller instance before the adapter serves it.
# Code-first: scan controller ở đây cho `xime grpc generate` và để phục vụ động.
# Package này PHẢI nằm trong dependency.scan() để DI dựng instance controller
# trước khi adapter phục vụ.
configure_grpc_codefirst(packages=["app.api.grpc"])

# Inbound dynamic mTLS: the server re-reads the cert from the provider on every
# new TLS handshake (rotation without restart). On/off lives in application.yml
# (grpc.tls.enabled / mutual).
# mTLS vào động: server đọc lại cert từ provider ở mỗi handshake TLS mới (rotate
# không cần restart). Bật/tắt nằm ở application.yml (grpc.tls.enabled / mutual).
configure_grpc_tls(provider=TrustGrpcCertificateProvider)
