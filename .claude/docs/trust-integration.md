# Tích hợp Trust (bootstrap + rotate cert + mTLS động)

> Cụm này GIỐNG NHAU ở cả server/ và client/. Toàn bộ là **sao chép từ
> data-service** rồi đổi tên/cổng cho hợp. Nguồn gốc:
> `D:\code\xime\Base Platform\data\app\integration\trust\` và hướng dẫn
> `data\.claude\docs\migrate-grpc-client-mtls.md`.
>
> **data-service code trước ví dụ này** - khi làm, mở đúng file tương ứng bên
> data-service ra đối chiếu 1:1.

## 1. Cụm `integration/trust/` gồm gì

Sao chép nguyên các thư mục con sau (đã verify tồn tại trong data-service):

```text
integration/trust/
  bootstrap/      Bootstrap, BootstrapLoader, BootstrapPayload, BootstrapValidator
  certificate/    GrpcTrustCertificateClient (viết tay), TrustCertificateResolver,
                  TrustCertificateSynchronizer
  publicca/       RootCertificateFileStore, TrustRootCertificateInitializer,
                  TrustRootCertificateResolver
  key/            TrustKeyClient, VerificationKeyCache, VerificationKeySynchronizer,
                  TrustKeyCleanup
  ssl/            TrustGrpcCertificateProvider, TrustSslContextProvider,
                  PemNormalizer
  scheduler/      CertRotationJob, KeyRefreshJob, KeyCleanupJob
  startup/        TrustStartupOrchestrator
  proto/ + generated/   proto Trust + stub sinh ra
```

> Lưu ý: data-service đang ở giữa quá trình migrate. Bản sạch nhất là sau khi
> data-service hoàn tất guide `migrate-grpc-client-mtls.md`: đã **xóa**
> `ssl/GrpcServerSslContextProvider.py`, và `TrustKeyClient` đã thành adapter
> mỏng quanh SDK. **Copy bản ĐÃ migrate**, đừng copy phần thừa.

## 2. Vai trò các thành phần (để hiểu khi copy)

- **Bootstrap** - đọc file bootstrap (`runtime/security/bootstrap.txt`) chứa
  thông tin đổi cert lần đầu. Người dùng cấp file này lúc chạy.
- **GrpcTrustCertificateClient** (VIẾT TAY, giữ nguyên) - gọi Trust
  `RotateCertificate` để nhận cert mới. KHÔNG dùng SDK động vì chicken-egg: cần
  cert hợp lệ để mở kênh, nhưng kênh này chính là để đi lấy cert. Nó dựng channel
  tay với `TrustSslContextProvider`, có `set_credentials()`.
- **TrustCertificateResolver** - cache cert hiện tại trong RAM (có lock). Mọi
  nơi cần cert (provider) đọc từ đây.
- **TrustCertificateSynchronizer** - vòng đời cert: startup (bootstrap hoặc nạp
  từ store), và rotate khi gần hết hạn. Có state model NEW/ACTIVE/RECOVERABLE/BROKEN.
- **TrustRootCertificateResolver / Initializer / FileStore** - root CA của Trust
  (tin tưởng phía bên kia). Nạp từ `runtime/security/ca.pem`.
- **TrustGrpcCertificateProvider** - implement Protocol `GrpcCertificateProvider`
  của framework: `version()` + `current()` đọc 2 resolver (cert + root CA), map
  qua `PemNormalizer` thành `ServerCertificates`. Đây là cầu nối app ↔ framework
  cho mTLS động (cả vào server lẫn kênh client).
- **TrustKeyClient / VerificationKeyCache** - lấy public key Trust để verify JWT.
  Sau migrate, `TrustKeyClient` là adapter mỏng quanh SDK động.
- **CertRotationJob / KeyRefreshJob** (scheduler) - định kỳ gọi synchronizer
  rotate cert / refresh key. Khi cert đổi, resolver cập nhật → `version()` đổi →
  framework tự dùng cert mới (server + client).
- **TrustStartupOrchestrator** - chạy lúc startup, đúng thứ tự:
  **root CA → đồng bộ cert (bootstrap) → đồng bộ key**.

## 3. Quyết định cần chốt: lưu cert ở đâu (persistence)

data-service lưu cert vào **PostgreSQL** qua `LoadCertificatePort`/`SaveCertificatePort`
+ `TransactionManager` (cần DB + Alembic + SQLAlchemy starter). Với một **ví dụ
chạy nhanh cho người khác tham khảo**, đây là gánh nặng (phải dựng Postgres mới
chạy được demo).

**Đề xuất (khuyến nghị) cho ví dụ này: lưu cert ra FILE** trong
`runtime/security/` (ví dụ cert PEM mã hoá bằng Fernet, giống cách root CA đã lưu
file). Giữ NGUYÊN cấu trúc resolver/synchronizer/scheduler/provider - chỉ thay
hai port DB bằng hai port file (`FileLoadCertificatePort`/`FileSaveCertificatePort`).
Lý do: ví dụ chạy được chỉ với Trust + file, không cần Postgres; mọi pattern mTLS
động vẫn nguyên vẹn.

> Đây là điểm khác biệt có chủ đích so với data-service. Nếu người dùng muốn ví
> dụ **bám sát data-service tuyệt đối** (kể cả DB), thì giữ Postgres + Alembic +
> SQLAlchemy starter. **Hỏi/chốt với người dùng trước khi code phần persistence**
> - đây là quyết định kiến trúc, không tự ý chọn. Phần còn lại (resolver,
> synchronizer skeleton, scheduler, provider, bootstrap) làm được ngay không phụ
> thuộc lựa chọn này.

## 4. Bootstrap & runtime do người dùng cấp

Người dùng chạy demo sẽ cung cấp (đặt trong `runtime/security/` của MỖI app):

- `bootstrap.txt` - payload bootstrap đổi cert lần đầu (định dạng theo
  `BootstrapPayload`/`BootstrapValidator` của data-service).
- `ca.pem` - root CA của Trust.

Và cấu hình trong `resources/application.yml` (theo data-service):

```yaml
trust:
  service_id: <id service này>
  grpc:
    host: <trust host>
    port: <trust grpc port>
security:
  cert_encryption_key: <Fernet key để mã hoá cert lưu file/DB>
```

> Khi code, đối chiếu key YAML chính xác với data-service `resources/application.yml`
> (tên trường có thể khác chút). Đừng đoán - đọc file thật.

## 5. Đăng ký vào DI (config layer)

Phần lớn cụm trust nằm trong package được `dependency.scan(...)` hoặc đăng ký thủ
công trong `config/dependency.py` (đối chiếu `data/app/config/dependency.py`).
Riêng hai điểm chạm framework:

```python
# config/grpc.py  (server VÀ client đều cần dòng provider nếu mở kênh/serve mTLS động)
from xime.adapters.grpc import configure_grpc_tls
from app.integration.trust.ssl.TrustGrpcCertificateProvider import TrustGrpcCertificateProvider

configure_grpc_tls(provider=TrustGrpcCertificateProvider)   # server: mTLS vào
```

Phía client, để kênh SDK dùng mTLS động, đặt `tls.dynamic: true` trong
`grpc.clients.<id>.tls` (xem `kien-truc-vi-du.md` mục 4). Framework tự lấy cert
từ cùng provider/resolver.

## 6. Thứ tự làm (đừng nhảy bước)

1. Copy cụm `integration/trust/` (bản đã migrate) từ data-service sang app.
2. Thay đổi tên service/cổng/`service_id`.
3. Chốt persistence (mục 3) - nếu file-based, viết 2 port file thay 2 port DB.
4. Đăng ký DI + `configure_grpc_tls`.
5. Đặt `bootstrap.txt` + `ca.pem` vào `runtime/security/`.
6. Chạy Trust → chạy app → kiểm bootstrap cert chạy, mTLS lên, không insecure.

> Toàn bộ chi tiết "làm gì với từng file" đã có trong
> `data\.claude\docs\migrate-grpc-client-mtls.md` (Phần 0/A/B). Tài liệu này chỉ
> tóm tắt để định hướng; nguồn chân lý là code data-service.
