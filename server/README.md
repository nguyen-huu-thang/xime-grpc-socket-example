# Vault gRPC Server - ví dụ code-first + mTLS động

App Xime minh hoạ **gRPC code-first**: bạn viết controller Python + DTO Pydantic,
framework tự sinh `.proto` và phục vụ qua nối dây động, cộng **mTLS động** (cert
bootstrap + rotate với Trust, xoay không cần restart).

Cùng tiến trình này còn phục vụ một service **Socket (Unix Domain Socket)** -
"Crypto Engine" native - minh hoạ điểm mạnh **một app Xime chạy nhiều adapter
cùng lúc**. Xem mục **Socket: Crypto Engine** bên dưới.

> Đây là một nửa của ví dụ. Nửa kia là [`../client`](../client) - gọi server này
> qua SDK sinh tự động + DI. Đọc tổng quan ở [`../CLAUDE.md`](../CLAUDE.md) và
> [`../.claude/docs/kien-truc-vi-du.md`](../.claude/docs/kien-truc-vi-du.md).

## Minh hoạ những gì

- **Code-first 3 kiểu RPC** trong [app/api/grpc/VaultController.py](app/api/grpc/VaultController.py):
  - `hash` - `@command` (unary): `HashRequest{text}` -> `HashResponse{digest, trace_id: UUID}`
  - `store` - `@stream` + `UploadStream` (client-stream): nhận chunk -> `StoreResponse{total_bytes}`
  - `fetch` - `@stream` + `DownloadStream` (server-stream): phát các chunk
  - DTO ở [app/application/dto/vault.py](app/application/dto/vault.py) là nguồn chân lý; `trace_id: uuid.UUID` minh hoạ sidecar giữ kiểu 1:1.
- **Sinh mã**: `xime grpc generate` -> [generated/vault/](generated/vault/) (`.proto`, `contract.json`, `_descriptors.binpb`, `*_pb2*`).
- **mTLS động vào**: [app/config/grpc.py](app/config/grpc.py) gọi `configure_grpc_tls(provider=TrustGrpcCertificateProvider)`.
- **Trust integration** (`app/integration/trust/`): bootstrap cert lần đầu + rotate định kỳ. Sao chép từ data-service, **chỉ phần cert/mTLS** (không có cụm verification-key JWT - xem data-service nếu cần).

## Khác data-service ở đâu

Persistence cert dùng **file** thay vì PostgreSQL, cho nhẹ và chạy nhanh:

- [app/integration/trust/store/FileCertificateStore.py](app/integration/trust/store/FileCertificateStore.py) - implement `LoadCertificatePort` + `SaveCertificatePort`, lưu `runtime/security/cert.json`, mã hoá Fernet (y cách data-service mã hoá, chỉ khác phương tiện lưu).
- [app/integration/trust/store/NoOpTransactionManager.py](app/integration/trust/store/NoOpTransactionManager.py) - `TransactionManager` rỗng (file không cần transaction), nên các synchronizer copy nguyên từ data-service chạy không sửa.

Mọi thứ còn lại của cụm trust (resolver, synchronizer, scheduler, ssl provider,
bootstrap, cert client viết tay) là **copy nguyên từ data-service**.

## Chạy

```bash
# 1. Cài framework + extra gRPC
pip install -e "D:\code\xime\xime framework"
pip install "xime[grpc]"
pip install -e .        # deps của app

# 2. Đặt secrets do Trust cấp vào runtime/security/
#    - bootstrap.txt  (cert bootstrap lần đầu)
#    - ca.pem         (root CA của Trust)
#    Xem runtime/security/README.md

# 3. (tuỳ chọn) sinh lại proto sau khi sửa controller/DTO
xime grpc generate --config app.config

# 4. Chạy (cần Trust Service đang chạy ở trust.grpc.host:port)
python -m app.main
```

Server lắng nghe gRPC ở cổng `50051` (xem `resources/application.yml`), mTLS bật.
Thứ tự demo: Trust Service -> server (app này) -> client.

## Socket: Crypto Engine (UDS, chỉ Linux)

Cùng tiến trình, server còn phục vụ một "Crypto Engine" native qua Unix Domain
Socket - **cùng contract `@command`/`@stream` + DTO Pydantic** như gRPC, chỉ khác
transport. Không protobuf, không sinh mã: request/response đi dạng **msgpack
dict**. Bảo mật bằng kernel (file permission + SO_PEERCRED), KHÔNG TLS/Trust.

- Controller [app/api/socket/CryptoEngineController.py](app/api/socket/CryptoEngineController.py) (`server_id = "crypto"`):
  - `hash` - `@command`: `HashRequest{blob_id}` -> `HashResponse{digest}`
  - `encrypt` - `@stream` + `UploadStream`: nhận chunk -> `EncryptResponse{total_bytes}`
  - `download` - `@stream` + `DownloadStream`: phát `parts` chunk
- DTO msgpack-friendly [app/application/dto/crypto.py](app/application/dto/crypto.py): chỉ str/int (KHÔNG UUID/Decimal - msgpack không gói được; đây là điểm khác sidecar gRPC).
- Đăng ký [app/config/socket.py](app/config/socket.py): `configure_socket_controllers("app.api.socket")`; package này cũng nằm trong `dependency.scan`.
- Adapter [app/main.py](app/main.py): `app.use(SocketAdapter("crypto"))`, **guard theo nền tảng** (`hasattr(asyncio, "start_unix_server")`) - Windows chỉ chạy gRPC, Linux chạy cả hai.
- Cấu hình: khối `socket:` trong `resources/application.yml` -> bind `/tmp/xime/crypto.sock`.

> **Chỉ Linux/macOS.** UDS không có trên Windows; chạy thật + e2e test trên Linux.
> Cài thêm: `pip install "xime[socket]"` (kéo `msgpack`).

## Test

```bash
pip install -e ".[test]"   # pytest + pytest-asyncio
python -m pytest tests/
```

- `tests/socket/` - unit (use case + builder + DTO, chạy mọi OS) + e2e (chỉ Linux).
- `tests/grpc/` - để trống (gRPC đã verify chạy live).
- Trên Windows: unit pass, e2e tự skip. Trên Linux: e2e chạy đầy đủ.

## Cấu trúc

```text
app/
  api/
    grpc/VaultController.py            # controller gRPC code-first (@command/@stream)
    socket/CryptoEngineController.py   # controller socket (cùng contract, server_id="crypto")
  application/
    dto/vault.py                  # DTO gRPC = nguồn chân lý (có UUID)
    dto/crypto.py                 # DTO socket (msgpack-friendly, không UUID/Decimal)
    usecase/VaultUseCase.py            # logic Vault (gRPC)
    usecase/CryptoEngineUseCase.py     # logic Crypto Engine (socket)
  integration/trust/              # bootstrap + rotate cert + mTLS (copy từ data-service)
    store/                        # file store thay DB (viết tay)
  config/
    dependency.py                 # DI scan + bind (gồm app.api.socket)
    grpc.py                       # configure_grpc_codefirst + configure_grpc_tls
    socket.py                     # configure_socket_controllers + error mappings
    scheduler.py                  # CertRotationJob mỗi giờ
  main.py                         # GrpcAdapter() + SocketAdapter("crypto") (guard nền tảng)
generated/vault/                  # mã sinh gRPC (commit để client copy proto)
tests/
  grpc/                           # để trống (gRPC đã verify chạy live)
  socket/test_crypto_engine.py    # unit (mọi OS) + e2e (Linux)
conftest.py                       # cho phép import app khi chạy pytest
resources/application.yml         # cổng gRPC, khối socket:, trust.*, cert_encryption_key
runtime/security/                 # bootstrap.txt + ca.pem (bạn cấp), cert.json (sinh ra)
```
