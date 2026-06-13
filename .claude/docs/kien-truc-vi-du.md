# Kiến trúc ví dụ gRPC (server + client)

> Đọc file này TRƯỚC. Nó mô tả ví dụ sẽ xây gì, mỗi app minh hoạ điều gì, và
> kịch bản demo cụ thể. Chi tiết từng bước nằm ở `ke-hoach-xay-dung.md`; phần
> Trust ở `trust-integration.md`.

## 1. Ví dụ này minh hoạ điều gì

Một cặp service Xime nói chuyện gRPC với nhau qua **mTLS động** (cert xoay không
downtime), trong đó:

- **server/** - định nghĩa contract bằng **code-first** (controller Python + DTO
  Pydantic), framework tự sinh `.proto` + sidecar `contract.json`, phục vụ qua
  nối dây động (không viết Servicer tay).
- **client/** - gọi server bằng **SDK sinh tự động** từ proto của server, SDK
  được đưa vào **DI** và inject vào use case (không dựng channel tay, không
  marshal protobuf tay).

Cả hai app đều tự bootstrap cert lần đầu với Trust và rotate cert định kỳ - sao
chép nguyên cụm `integration/trust/` từ data-service.

```text
        ┌────────────┐   mTLS động (cert rotate)   ┌────────────┐
        │  client/   │ ───────────────────────────▶│  server/   │
        │ (gọi SDK)  │      gRPC code-first         │ (phục vụ)  │
        └─────┬──────┘                              └─────┬──────┘
              │ bootstrap + rotate cert / key             │
              ▼                                            ▼
                        ┌──────────────────┐
                        │  Trust Service   │  (người dùng chạy sẵn)
                        └──────────────────┘
```

## 2. Kịch bản demo: dịch vụ "Vault"

Server cung cấp một service **Vault** đơn giản nhưng phủ đủ 3 kiểu RPC mà
code-first hỗ trợ (bám sát test đã chứng minh chạy được:
`xime framework/tests_temp/grpc_codefirst/test_codefirst_e2e.py` và
`tests_temp/grpc_client/test_client_sdk_e2e.py`):

| RPC | Kiểu | DTO vào → ra | Ý nghĩa demo |
|---|---|---|---|
| `hash` | `@command` (unary) | `HashRequest{text}` → `HashResponse{digest}` | RPC đơn cơ bản |
| `store` | `@stream` + `UploadStream` (client-stream) | `StoreRequest{name}` + chunk bytes → `StoreResponse{total_bytes}` | upload theo chunk |
| `fetch` | `@stream` + `DownloadStream` (server-stream) | `FetchRequest{parts}` → stream chunk bytes | download theo chunk |

Logic nghiệp vụ giữ tối thiểu (hash chuỗi, đếm byte, phát vài chunk) - trọng tâm
ví dụ là **đường đi gRPC + DI + mTLS**, không phải nghiệp vụ. Nên đặt một DTO có
kiểu "khó" (ví dụ `Decimal` hoặc `uuid.UUID`) ở một RPC để minh hoạ sidecar giữ
fidelity 1:1 khi sinh SDK (xem test client SDK dùng `Decimal`/`UUID`).

## 3. Server minh hoạ gì (code-first)

Cấu trúc app Xime chuẩn (giống data-service, tham chiếu `Base Platform/data/app/`):

```text
server/
  app/
    main.py
    api/grpc/
      VaultController.py        # @command/@stream, server_id = "vault"
      generated/                # xime grpc generate sinh vào đây (.proto, _pb2, contract.json, lock)
    application/
      usecase/                  # logic nghiệp vụ thật (VaultUseCase...)
      dto/                      # DTO Pydantic dùng cho controller
    domain/                     # (tuỳ chọn) logic thuần
    config/
      dependency.py             # scan + bind
      grpc.py                   # configure_grpc_codefirst + configure_grpc_tls
    integration/trust/          # SAO CHÉP từ data-service (bootstrap + rotate)
    resources/
      application.yml           # grpc.port + grpc.tls.enabled/mutual + trust.*
  runtime/security/             # bootstrap.txt, ca.pem (người dùng cấp lúc chạy)
```

Điểm cốt lõi phía server (API thật, đã verify):

```python
# config/grpc.py
from xime.adapters.grpc.codefirst import configure_grpc_codefirst
from xime.adapters.grpc import configure_grpc_tls
from app.integration.trust.ssl.TrustGrpcCertificateProvider import TrustGrpcCertificateProvider

configure_grpc_codefirst(packages=["app.api.grpc"])   # controller ở đây
configure_grpc_tls(provider=TrustGrpcCertificateProvider)   # mTLS động vào (inbound)
```

> Lưu ý: package controller PHẢI có trong cả `configure_grpc_codefirst(packages=...)`
> LẪN `dependency.scan(...)` (DI tạo instance trước khi adapter phục vụ).

Controller (mẫu theo test e2e):

```python
# api/grpc/VaultController.py
from xime.core.contract import command, stream, UploadStream, DownloadStream

class VaultController:
    server_id = "vault"

    def __init__(self, usecase: VaultUseCase):   # constructor injection
        self._usecase = usecase

    @command("hash")
    async def hash(self, request: HashRequest) -> HashResponse: ...

    @stream("store")
    async def store(self, request: StoreRequest, upload: UploadStream) -> StoreResponse: ...

    @stream("fetch")
    async def fetch(self, request: FetchRequest, download: DownloadStream) -> None: ...
```

Sinh mã: `cd server && xime grpc generate` (đọc registry, sinh `.proto` +
`_pb2`/`_pb2_grpc` + `_descriptors.binpb` + `contract.json` + `proto.lock.json`
vào `output_dir`). `xime grpc check` để CI kiểm drift.

## 4. Client minh hoạ gì (SDK + DI)

```text
client/
  app/
    main.py
    application/usecase/        # VaultCallerUseCase: inject client SDK, gọi server
    config/
      dependency.py
      grpc.py                   # configure_grpc_clients(...) + (tuỳ chọn) configure_grpc_tls cho server riêng của client
    integration/trust/          # SAO CHÉP từ data-service
    resources/application.yml   # grpc.clients.vault.{host,port,deadline_ms,tls}
  contracts/vault/              # copy .proto (+ contract.json) từ server sang
  clients/vault/                # xime grpc client sinh SDK vào đây
  runtime/security/
```

Sinh SDK từ proto của server:

```bash
cd client
# copy proto + sidecar từ server/app/api/grpc/generated/vault sang contracts/vault
xime grpc client --proto contracts/vault --out clients/vault
```

Khai báo client vào DI + cấu hình kênh:

```python
# config/grpc.py
from xime.adapters.grpc import configure_grpc_clients
from clients.vault import VaultClient        # tên class sinh theo controller
configure_grpc_clients("vault", VaultClient)  # "vault" khớp key trong application.yml
```

```yaml
# resources/application.yml
grpc:
  clients:
    vault:
      host: 127.0.0.1
      port: 9090
      deadline_ms: 3000
      tls:
        enabled: true
        dynamic: true     # mTLS động: kênh rebuild khi cert đổi version
```

Use case nhận client qua constructor (framework tự inject instance đã dựng kênh):

```python
# application/usecase/VaultCallerUseCase.py
class VaultCallerUseCase:
    def __init__(self, vault: VaultClient):    # SDK client là dependency bình thường
        self._vault = vault

    async def run(self) -> None:
        reply = await self._vault.hash(HashRequest(text="hello"))
        # upload: truyền async generator các chunk bytes
        # download: async for chunk in self._vault.fetch(FetchRequest(parts=3))
```

## 5. Ranh giới framework vs app (nhớ kỹ)

| Phần | Ai giữ | Ghi chú |
|---|---|---|
| Sinh proto/SDK, nối dây serve, dựng channel, marshal, deadline, dịch lỗi typed, rebuild kênh khi cert đổi | **Framework** | App không động vào |
| Controller + DTO + use case nghiệp vụ | **App** | Đây là phần ví dụ "dạy" |
| Bootstrap cert lần đầu, resolver giữ cert, scheduler rotate, provider đọc resolver | **App** (cụm `integration/trust/`) | Sao chép từ data-service; framework chỉ định nghĩa Protocol `GrpcCertificateProvider` |
| `GrpcTrustCertificateClient` (đổi cert với Trust) | **App, viết tay** | KHÔNG migrate sang SDK động (chicken-egg: cần cert để lấy cert) |
| `TrustKeyClient` (lấy public key) | **App** | CÓ thể dùng SDK động (proto-only vì Trust là Java) |

## 6. mTLS động hoạt động ra sao (tóm tắt)

- Provider implement Protocol `GrpcCertificateProvider` của framework với 2 method:
  `version()` (đổi khi cert mới) và `current()` (trả PEM hiện tại). Provider chỉ
  đọc resolver trong bộ nhớ - KHÔNG gọi Trust realtime.
- **Server:** `configure_grpc_tls(provider=...)` → framework dựng dynamic SSL
  server credentials, fetch cert mới ở mỗi handshake. Bật/tắt ở
  `grpc.tls.enabled/mutual`.
- **Client:** `tls.dynamic: true` → `XimeGrpcChannel` theo dõi `version()`, khi
  đổi thì dựng kênh mới và cho kênh cũ "về hưu" có ân hạn (phiên đang chạy không
  đứt).
- Sự kiện cấp cert mới đến từ `CertRotationJob` (scheduler) gọi
  `GrpcTrustCertificateClient` → cập nhật resolver → `version()` đổi → cả server
  lẫn client tự dùng cert mới.
