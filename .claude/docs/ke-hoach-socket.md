# Kế hoạch thêm Socket (UDS) vào server/ và client/ (checklist)

> Đọc `kien-truc-socket.md` trước. Socket được THÊM vào chính hai app đang có
> (không tạo app mới). Giữ nguyên cấu trúc thư mục, chỉ thêm file + sửa vài chỗ
> cấu hình. Làm theo thứ tự: server trước, client sau, test cuối.
>
> Bối cảnh máy: đang code trên **Windows** -> chỉ viết code + viết test. UDS chỉ
> chạy trên **Linux**, nên mọi mục "Xong khi... chạy live/e2e" để chạy/verify
> trên Linux. Unit test logic thuần chạy được ngay trên Windows.
>
> **Trạng thái (2026-06-13):** toàn bộ CODE + TEST đã viết xong và verify mức
> Windows (unit pass, e2e tự skip). Các mục `[ ]` còn lại đều là "Xong khi...
> chạy live/e2e trên Linux". Quy ước: `[x]` = đã làm; `[ ]` = chờ chạy thật Linux.

## Chuẩn bị chung

- [x] `server/pyproject.toml` và `client/pyproject.toml` đã khai `msgpack` (deps để
      LỎNG, không ghim version). Bước `pip install "xime[socket]"` chạy trên Linux
      trước khi chạy thật.
- [x] Dev dep test khai trong `[project.optional-dependencies] test` của mỗi
      pyproject: `pytest`, `pytest-asyncio` (đã có trong môi trường, test chạy được).

---

## Phần 1 - SERVER: thêm service socket "Crypto Engine"

### 1.1. DTO + controller socket
- [x] Tạo package `server/app/api/socket/` (có `__init__.py`).
- [x] DTO Pydantic `application/dto/crypto.py`, **chỉ kiểu msgpack-friendly**:
      `HashRequest{blob_id}` / `HashResponse{digest}`, `EncryptRequest{name}` /
      `EncryptResponse{name,total_bytes}`, `DownloadRequest{name,parts}`.
- [x] `api/socket/CryptoEngineController.py`: `server_id = "crypto"`, 3 method
      `@command("hash")`, `@stream("encrypt")` (UploadStream), `@stream("download")`
      (DownloadStream). Inject `CryptoEngineUseCase` qua constructor.
- [x] `application/usecase/CryptoEngineUseCase.py`: hash bytes, đếm byte upload,
      phát `parts` chunk download.

### 1.2. Đăng ký + adapter
- [x] `config/socket.py`: `configure_socket_controllers("app.api.socket")` +
      `configure_socket_error_mappings({})` (để trống, nêu để tham khảo).
- [x] `config/dependency.py`: đã thêm `"app.api.socket"` vào `dependency.scan(...)`.
- [x] `main.py`: thêm `app.use(SocketAdapter("crypto"))` cạnh `GrpcAdapter()`,
      **guard `hasattr(asyncio, "start_unix_server")`** để Windows vẫn chạy gRPC.
- [x] `resources/application.yml`: đã thêm khối `socket:` (dir `/tmp/xime`):
      ```yaml
      socket:
        dir: /tmp/xime          # tránh /run/xime cần quyền root khi dev
        permission: "0600"
        session_timeout: 30
        # allowed_uids: [1000]  # tuỳ chọn, whitelist SO_PEERCRED
      ```
      -> server bind tại `/tmp/xime/crypto.sock` (suy từ server_id "crypto").
- [ ] **Xong khi (Linux):** `python -m app.main` lên, log cho thấy CẢ GrpcAdapter
      lẫn SocketAdapter phục vụ; file `/tmp/xime/crypto.sock` được tạo.

---

## Phần 2 - CLIENT: gọi service socket qua SocketClient

### 2.1. Use case gọi engine
- [x] `application/usecase/CryptoEngineCallerUseCase.py`: nhận `RuntimeConfig`, đọc
      `socket_path`, dựng `SocketClient(path)`, gọi `command("hash")`,
      `upload("encrypt")` (ghi chunk rồi `finish()`), `download("download")`
      (async for), `close()`. Response đọc theo key dict.
- [x] Đưa `socket_path` vào `application.yml` khối app-level
      `crypto_engine.socket_path: "/tmp/xime/crypto.sock"`, đọc qua `RuntimeConfig`.

### 2.2. Chạy demo lúc khởi động
- [x] `application/runner/CryptoDemoRunner.py` (PostConstruct): gọi
      `CryptoEngineCallerUseCase`, log có đánh số `[1/3]/[2/3]/[3/3]`, bắt exception,
      **guard `hasattr(asyncio, "open_unix_connection")`** (Windows bỏ qua, không lỗi).
- [x] `config/dependency.py`: package `app.application.usecase` + `app.application.runner`
      đã có sẵn trong scan -> use case/runner mới tự được nhặt.
- [ ] **Xong khi (Linux):** chạy server rồi client; client kết nối UDS, gọi 3
      endpoint thành công, in kết quả đúng (hash digest, total_bytes, danh sách chunk).

---

## Phần 3 - TEST (ưu tiên: phần làm được ngay trên Windows)

> Bám mẫu `xime framework/tests_temp/socket/test_socket.py`.

### 3.1. Unit test (chạy mọi OS - làm trên Windows)
- [x] Test `CryptoEngineUseCase`: hash sha256, đếm byte upload, phát đủ `parts` chunk.
- [x] Test `SocketEndpointBuilder(...).build([CryptoEngineController])`: shape
      command/upload/download + lọc `server_id` (khác -> bảng rỗng).
- [x] Test DTO: thiếu field -> `ValidationError`.
- [x] Test client `CryptoEngineCallerUseCase` đọc đúng `socket_path` (config + mặc định).
- [x] **Đã chạy trên Windows:** server 6 passed / 2 skipped; client 2 passed / 1 skipped.

### 3.2. E2E test (chỉ Linux + msgpack)
- [x] Server: `SocketAdapter` trong tiến trình trên `.sock` tạm, gọi qua
      `SocketClient`: command + upload + download + 2 session đồng thời.
- [x] Client: dựng engine server tối giản, chạy `run_demo()` end-to-end (smoke).
- [x] Đánh dấu `skipif(not (HAS_UNIX and HAS_MSGPACK))` -> tự skip trên Windows.
- [ ] **Xong khi (Linux):** `pytest` xanh và các e2e CHẠY (không còn skip).

### 3.3. Vị trí test (đã chốt)
- [x] `server/tests/` và `client/tests/`, mỗi cái chia `grpc/` và `socket/`.
      Socket: `tests/socket/test_*.py` (unit + e2e). gRPC: `tests/grpc/` để TRỐNG
      (`.gitkeep`) vì gRPC đã verify live. `conftest.py` mỗi app để `import app` chạy.

---

## Phần 4 - Hoàn thiện tài liệu

- [x] Cập nhật `server/README.md` và `client/README.md`: đã thêm mục Socket +
      Test, cập nhật cây cấu trúc.
- [x] Cập nhật `CLAUDE.md` gốc: repo minh hoạ **gRPC + socket trong cùng app**,
      trỏ tới `kien-truc-socket.md` + `ke-hoach-socket.md`.
- [x] Cập nhật README gốc `README.md` (EN) + `README-vn.md` (VI): thêm phần Socket.

---

## Bẫy thường gặp (đọc trước khi debug lâu)

- **Controller socket không được phục vụ:** `server_id` lệch với `SocketAdapter(...)`,
  HOẶC quên thêm `app.api.socket` vào `dependency.scan()` (chỉ
  `configure_socket_controllers` là chưa đủ). Triệu chứng: client gọi báo
  `NOT_FOUND`/không có endpoint - giống hệt bẫy server_id bên gRPC.
- **`SocketAdapter requires msgpack`:** chưa cài `xime[socket]`/`msgpack`.
- **`msgpack.packb` lỗi kiểu:** DTO socket có `UUID`/`Decimal`/datetime. Đổi sang
  `str`/`int`/`float`. (Socket KHÔNG có sidecar fidelity như gRPC.)
- **Trộn nhầm controller:** đừng đưa package gRPC vào `configure_socket_controllers`
  hay ngược lại; tuy cùng decorator `@command/@stream`, mỗi adapter chỉ quét
  package + `server_id` của nó.
- **Path client != path server:** `socket_path` của client phải trùng file server
  bind (suy từ `socket.dir` + server_id, hoặc `path` truyền vào adapter).
- **Windows báo không chạy được/đỏ test:** bình thường - UDS chỉ Linux. E2E phải
  `skipif`; chạy thật trên Linux.
- **Quyền thư mục socket:** `/run/xime` thường cần root; khi dev dùng `/tmp/xime`.
