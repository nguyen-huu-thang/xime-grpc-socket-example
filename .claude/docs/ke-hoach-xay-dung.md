# Kế hoạch xây dựng ví dụ gRPC (checklist)

> Làm theo thứ tự: **server trước, client sau** (client cần proto của server để
> sinh SDK). Mỗi bước có tiêu chí "xong" rõ ràng. Chi tiết thiết kế ở
> `kien-truc-vi-du.md`; phần Trust ở `trust-integration.md`.
>
> **Trạng thái cập nhật (2026-06-13):** toàn bộ phần CODE của Phần 1, 2, 3 đã
> hoàn thành (các mục `[x]` bên dưới). Những mục còn `[ ]` đều là tiêu chí
> "Xong khi... chạy live", phải có secrets runtime (`bootstrap.txt` + `ca.pem`)
> và Trust Service đang chạy mới verify được - đang chờ người dùng xử lý.
> Quy ước: `[x]` = đã làm xong; `[ ]` = chờ chạy thật để xác nhận.

## Chuẩn bị chung (làm 1 lần)

- [x] Cài framework: `pip install -e "D:\code\xime\xime framework"` và bản có
      extra gRPC: `pip install "xime[grpc]"` (grpcio, grpcio-tools, protobuf).
- [ ] Xác nhận **Trust Service đang chạy** và đã có `bootstrap.txt` + `ca.pem`
      cho từng app (người dùng cấp). *(chờ người dùng cấp secrets runtime)*
- [x] **data-service đã code/migrate xong** - là khuôn mẫu để copy cụm trust.
      Nếu chưa, làm data-service trước (xem `Base Platform\data`).

---

## Phần 1 - SERVER (code-first)

### 1.1. Scaffold app Xime
- [x] Tạo cây `server/app/{api/grpc,application/{usecase,dto},domain,config,resources}`
      và `server/runtime/security/`. Đối chiếu `Base Platform/data/app/`.
- [x] `server/pyproject.toml` (hoặc setup) khai dependency xime; `app/main.py`
      entry point gọi bootstrap framework (xem `xime framework/.claude/docs/app-entry-point.md`).

### 1.2. DTO + controller code-first
- [x] DTO Pydantic trong `application/dto/` (hoặc cạnh controller): `HashRequest/Response`,
      `StoreRequest/Response`, `FetchRequest`. Cho 1 trường kiểu "khó" (`Decimal`
      hoặc `uuid.UUID`) để minh hoạ sidecar fidelity. -> `application/dto/vault.py`.
- [x] `api/grpc/VaultController.py` với `server_id = "vault"`, 3 method
      `@command("hash")`, `@stream("store")` (UploadStream), `@stream("fetch")`
      (DownloadStream). Inject `VaultUseCase` qua constructor.
- [x] `application/usecase/VaultUseCase.py` chứa logic thật (hash, đếm byte, phát
      chunk). Controller chỉ điều phối, không nhồi logic.

### 1.3. Đăng ký + sinh mã
- [x] `config/dependency.py`: `dependency.scan("app.api.grpc", "app.application.usecase", ...)`
      + bind Protocol nếu có.
- [x] `config/grpc.py`: `configure_grpc_codefirst(packages=["app.api.grpc"])`.
      (Package controller PHẢI nằm trong cả scan lẫn đây.)
- [x] Chạy `xime grpc generate` → đã sinh `.proto`, `_pb2`/`_pb2_grpc`,
      `_descriptors.binpb`, `contract.json` vào `server/generated/default/`
      (LƯU Ý 1: output thực tế ở `server/generated/<server_id>/`; sau khi đổi
      `server_id="default"` thì là `server/generated/default/`, không phải
      `server/app/api/grpc/generated/vault/` như mô tả cũ.
      LƯU Ý 2: `xime` không trên PATH + config ở `app.config`, nên chạy:
      `python -c "from xime.cli._main import main; main()" grpc generate --config app.config`).
- [ ] **Xong khi:** `xime grpc check` sạch (không drift). *(chưa chạy để xác nhận)*

### 1.4. mTLS động (vào) + Trust
- [x] Copy cụm `integration/trust/` từ data-service (xem `trust-integration.md`).
      Persistence cert đã chốt **file-based** (`integration/trust/store/FileCertificateStore.py`).
- [x] `config/grpc.py`: thêm `configure_grpc_tls(provider=TrustGrpcCertificateProvider)`.
- [x] `resources/application.yml`: `grpc.port`, `grpc.tls.enabled: true`,
      `grpc.tls.mutual: true`, khối `trust.*` + `security.cert_encryption_key`.
- [ ] **Xong khi:** `python app/main.py` lên được, bootstrap cert chạy, server
      gRPC phục vụ mTLS (không insecure), `TrustStartupOrchestrator` chạy đúng
      thứ tự root CA → cert → key. *(chờ secrets runtime + Trust Service để chạy live)*

---

## Phần 2 - CLIENT (SDK + DI)

### 2.1. Scaffold app Xime
- [x] Tạo cây `client/app/{application/usecase,config,resources}`,
      `client/{contracts,clients}/`, `client/runtime/security/`.
- [x] `app/main.py` entry point.

### 2.2. Sinh SDK từ proto server
- [x] Copy `.proto` + `contract.json` từ `server/generated/vault/`
      sang `client/contracts/vault/`. *(nguồn copy là `server/generated/vault/`)*
- [x] `cd client && xime grpc client --proto contracts/vault --out clients/vault`
      → đã sinh package SDK (`_models.py`, `_clients.py`, `__init__.py`, `_descriptors.binpb`).
- [ ] **Xong khi:** `from clients.vault import VaultClient` import được; DTO trong
      `clients.vault` lật gương đúng kiểu (kiểm `Decimal`/`UUID` annotation).
      *(file đã sinh; chưa chạy import để xác nhận)*

### 2.3. Đưa client vào DI + use case
- [x] `config/grpc.py`: `configure_grpc_clients("vault", VaultClient)`.
- [x] `config/dependency.py`: scan `app.application.usecase`.
- [x] `application/usecase/VaultCallerUseCase.py`: inject `VaultClient` qua
      constructor; gọi `hash` (unary), `store` (truyền async generator chunk),
      `fetch` (async for). In kết quả ra để demo. (có thêm
      `application/runner/VaultDemoRunner.py` điều phối kịch bản demo.)

### 2.4. mTLS động (ra) + Trust
- [x] Copy cụm `integration/trust/` (như server) cho client.
- [x] `resources/application.yml`:
      ```yaml
      grpc:
        clients:
          vault:
            host: 127.0.0.1
            port: <port server>
            deadline_ms: 3000
            tls: { enabled: true, dynamic: true }
      ```
      + khối `trust.*` + `security.cert_encryption_key`.
- [ ] **Xong khi:** chạy Trust → server → `python client/app/main.py`, client mở
      kênh mTLS động tới server, gọi 3 RPC thành công, in kết quả đúng.

---

## Phần 3 - Hoàn thiện thành tài liệu tham khảo

- [x] README ngắn ở `server/` và `client/` (tiếng Việt): chạy thế nào, minh hoạ gì.
      (có cả `README.md`/`README-vn.md` gốc + README trong `runtime/security/`.)
- [x] Comment giải thích "vì sao" ở các điểm framework chạm (provider, configure_*,
      controller decorator) - vì đây là ví dụ để người khác học.
- [ ] (Tuỳ chọn) Kịch bản demo rotate: trong lúc client đang gọi, ép Trust cấp
      cert mới → quan sát kênh rebuild không đứt phiên. *(chờ chạy live)*
- [ ] Cập nhật lại file `CLAUDE.md` gốc: đổi trạng thái từ "scaffold" sang "đã có
      server + client chạy được", và trỏ tới README mỗi app.
      *(làm sau khi verify chạy live thành công)*

---

## Bẫy thường gặp (đọc trước khi debug lâu)

- **Controller không được serve:** quên đưa package vào `dependency.scan()` (chỉ
  có trong `configure_grpc_codefirst` là chưa đủ - DI phải tạo instance trước).
- **mTLS không lên:** thiếu `grpc.tls.enabled: true` trong yaml dù đã
  `configure_grpc_tls` (giống lỗi data-service từng chạy insecure).
- **Client `dynamic: true` nhưng không có cert:** provider/resolver chưa được DI
  hoặc bootstrap chưa chạy xong; kiểm thứ tự `TrustStartupOrchestrator`.
- **Drift proto:** sửa DTO mà quên `xime grpc generate`; CI nên chạy `xime grpc check`.
- **Trust là Java:** SDK sinh từ proto Trust là proto-only (chỉ unary, không
  sidecar) - đúng như thiết kế. `GrpcTrustCertificateClient` vẫn viết tay.
