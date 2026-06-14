# Vault gRPC Client - ví dụ SDK + DI + mTLS động

App Xime minh hoạ **gRPC client**: gọi server Vault qua **SDK sinh tự động** +
**Dependency Injection**, không dựng channel tay, không marshal protobuf, cộng
**mTLS động** chiều ra (cert bootstrap + rotate với Trust).

Cùng app còn gọi service **Socket (Unix Domain Socket)** "Crypto Engine" của
server - minh hoạ một client nói chuyện hai transport. Xem mục **Socket: gọi
Crypto Engine** bên dưới.

> Nửa kia là [`../server`](../server) - định nghĩa Vault bằng code-first. Tổng
> quan: [`../CLAUDE.md`](../CLAUDE.md) và
> [`../.claude/docs/kien-truc-vi-du.md`](../.claude/docs/kien-truc-vi-du.md).

## Minh hoạ những gì

- **Sinh SDK từ proto của server**: copy `vault.proto` + `contract.json` từ
  server sang [contracts/vault/](contracts/vault/), rồi
  `xime grpc client --proto contracts/vault --out clients/vault` -> [clients/vault/](clients/vault/)
  (`VaultClient` + DTO Pydantic, `trace_id` lật gương lại đúng `uuid.UUID`).
- **Đưa client vào DI**: [app/config/grpc.py](app/config/grpc.py) gọi
  `configure_grpc_clients("vault", VaultClient)`; YAML `grpc.clients.vault` khai
  host/port/deadline + `tls.dynamic: true`.
- **Gọi qua DI**: [app/application/usecase/VaultCallerUseCase.py](app/application/usecase/VaultCallerUseCase.py)
  nhận `VaultClient` qua constructor, gọi `hash` (unary), `store` (client-stream),
  `fetch` (server-stream).
- **Chạy demo lúc khởi động**: [app/application/runner/VaultDemoRunner.py](app/application/runner/VaultDemoRunner.py)
  là hook `post_construct`, phụ thuộc `TrustStartupOrchestrator` để chắc cert mTLS
  đã sẵn sàng trước khi mở channel.
- **mTLS động chiều ra**: `tls.dynamic: true` -> `XimeGrpcChannel` tự rebuild khi
  cert rotate; cần `configure_grpc_tls(provider=...)` để channel lấy được cert.
- **Trust integration**: giống hệt server (copy file-based, chỉ cert/mTLS).

## Chạy

```bash
# 1. Tạo venv + cài thư viện (từ root repo hoặc riêng trong client/)
python3 -m venv .venv
source .venv/bin/activate

pip install "xime[grpc,socket,scheduler]"
pip install cryptography
pip install -e ".[test]"

# 2. Sinh lại SDK client nếu server đổi contract (xem mục "Khi sửa contract")

# 3. Sinh cert dev vào runtime/security/ - KHÔNG cần Trust Service
#    Tạo cert.json + ca-cert.pem cho cả server lẫn client (service_id = "vault-client").
#    Xem runtime/security/README.md.
python ../tools/generate_dev_certs.py

# 4. Chạy SAU khi server đã lên:
python -m app.main
```

Client load cert từ file -> mở channel mTLS động tới server (`localhost:50051`) ->
gọi 3 RPC -> in kết quả -> đứng chờ (Ctrl+C để thoát).

Thứ tự demo: server -> client (app này). Trust Service chỉ cần nếu chạy luồng
bootstrap thật (xem `runtime/security/README.md`).

## Socket: gọi Crypto Engine (UDS, chỉ Linux)

Client cũng gọi service socket "Crypto Engine" của server qua Unix Domain Socket.
Khác gRPC: **không có SDK sinh tự động / DI nối kênh** - use case tự dựng
`SocketClient(path)`; response trả về là **dict** (msgpack), không phải DTO typed.

- Use case [app/application/usecase/CryptoEngineCallerUseCase.py](app/application/usecase/CryptoEngineCallerUseCase.py): đọc `crypto_engine.socket_path` từ config, gọi `command("hash")`, `upload("encrypt")`, `download("download")`.
- Runner [app/application/runner/CryptoDemoRunner.py](app/application/runner/CryptoDemoRunner.py): `post_construct` chạy demo, log `[1/3]/[2/3]/[3/3]`, **guard nền tảng** (Windows bỏ qua, không lỗi).
- DTO request [app/application/dto/crypto.py](app/application/dto/crypto.py) (chỉ request; response là dict).
- Cấu hình: `crypto_engine.socket_path` trong `resources/application.yml`, phải trùng path server bind (`/tmp/xime/crypto.sock`).

> **Chỉ Linux/macOS.** Trên Windows demo socket tự bỏ qua; chạy thật trên Linux.
> Cài thêm: `pip install "xime[socket]"` (kéo `msgpack`).

## Test

```bash
pip install -e ".[test]"   # pytest + pytest-asyncio
python -m pytest tests/
```

- `tests/socket/` - unit (đọc config, chạy mọi OS) + e2e smoke (chỉ Linux).
- `tests/grpc/` - để trống.

## Khi sửa contract

Nếu server đổi controller/DTO:

```bash
# Ở server/: sinh lại proto
python -c "from xime.cli._main import main; main()" grpc generate --config app.config

# Copy contract sang client/
cp server/generated/default/vault.proto client/contracts/vault/
cp server/generated/default/contract.json client/contracts/vault/

# Ở client/: sinh lại SDK
python -c "from xime.cli._main import main; main()" grpc client \
    --proto contracts/vault --out clients/vault
```

SDK (`clients/vault/`) luôn là mã sinh, không sửa tay.

## Cấu trúc

```text
app/
  application/
    usecase/VaultCallerUseCase.py         # inject VaultClient, gọi 3 RPC gRPC
    usecase/CryptoEngineCallerUseCase.py  # tự dựng SocketClient, gọi 3 endpoint socket
    runner/VaultDemoRunner.py             # post_construct demo gRPC
    runner/CryptoDemoRunner.py            # post_construct demo socket (guard nền tảng)
    dto/crypto.py                         # DTO request cho socket (msgpack-friendly)
  integration/trust/                # bootstrap + rotate cert + mTLS (file-based)
  config/
    dependency.py                   # DI scan + bind
    grpc.py                         # configure_grpc_clients + configure_grpc_tls
    scheduler.py                    # CertRotationJob
  main.py                           # Application().run() (không adapter)
contracts/vault/                    # proto + contract.json copy từ server
clients/vault/                      # SDK gRPC sinh tự động (VaultClient + DTO)
tests/
  grpc/                             # để trống
  socket/test_crypto_caller.py      # unit (mọi OS) + e2e smoke (Linux)
conftest.py                         # cho phép import app khi chạy pytest
resources/application.yml           # grpc.clients.vault, crypto_engine.socket_path, trust.*
runtime/security/                   # cert.json + ca-cert.pem (sinh bởi tools/generate_dev_certs.py)
```
