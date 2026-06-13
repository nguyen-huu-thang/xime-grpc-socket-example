import asyncio

from xime import Application
from xime.adapters.grpc import GrpcAdapter

# Vault gRPC server (code-first + dynamic mTLS) AND a native "Crypto Engine" over
# a Unix Domain Socket - one Xime app running two adapters at once.
# Logging is auto-configured by the framework at bootstrap (tune via the
# `logging:` block in resources/application.yml) - no basicConfig needed here.
# Config is auto-discovered from app.config.* (dependency/grpc/socket/scheduler).
# Server Vault gRPC (code-first + mTLS động) VÀ "Crypto Engine" native qua Unix
# Domain Socket - một app Xime chạy hai adapter cùng lúc. Logging do framework tự
# cấu hình lúc bootstrap. Config tự khám phá từ app.config.*.
app = Application()

if __name__ == "__main__":
    # gRPC works on any OS. The socket adapter needs Unix Domain Sockets, which
    # only exist on Linux/macOS - guard it so the gRPC server still runs on
    # Windows during development (real socket runs happen on Linux).
    # gRPC chạy mọi OS. Socket adapter cần Unix Domain Socket (chỉ Linux/macOS) -
    # guard lại để server gRPC vẫn chạy được trên Windows khi dev (chạy socket
    # thật trên Linux).
    app.use(GrpcAdapter())
    if hasattr(asyncio, "start_unix_server"):
        from xime.adapters.socket import SocketAdapter

        app.use(SocketAdapter("crypto"))   # phục vụ controller server_id="crypto"
    app.run()
