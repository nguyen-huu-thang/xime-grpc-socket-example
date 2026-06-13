from xime.adapters.grpc import configure_grpc_clients, configure_grpc_tls

from clients.vault import VaultClient
from app.integration.trust.ssl.TrustGrpcCertificateProvider import TrustGrpcCertificateProvider

# Register the generated SDK client. "vault" matches grpc.clients.vault in
# application.yml; the framework builds a managed XimeGrpcChannel from that block
# and registers a VaultClient instance in DI.
# Đăng ký client SDK sinh ra. "vault" khớp grpc.clients.vault trong
# application.yml; framework dựng XimeGrpcChannel có quản lý từ block đó và đăng
# ký một instance VaultClient vào DI.
configure_grpc_clients("vault", VaultClient)

# Required for the client's outbound dynamic mTLS: the dynamic channel attaches
# this provider to read the current cert (shared "default" provider, same as the
# server side). Without it, tls.dynamic: true fails fast at startup.
# Cần cho mTLS động chiều ra của client: channel động gắn provider này để đọc
# cert hiện tại (provider "default" dùng chung, giống phía server). Thiếu nó,
# tls.dynamic: true sẽ fail ngay lúc khởi động.
configure_grpc_tls(provider=TrustGrpcCertificateProvider)
