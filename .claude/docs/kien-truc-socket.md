# Kiến trúc bổ sung: Socket (UDS) trong cùng app server/client

> Đọc file này TRƯỚC khi làm phần socket. Nó mô tả socket được thêm vào ĐÂU và
> minh hoạ điều gì. Các bước chi tiết ở `ke-hoach-socket.md`. Phần gRPC vẫn theo
> `kien-truc-vi-du.md`.

## 1. Ý tưởng cốt lõi: một app, nhiều adapter

Không thêm app mới. Ta tận dụng đúng điểm mạnh của Xime: **một `Application` dùng
nhiều adapter cùng lúc**. Sau khi xong:

- `server/` (đang phục vụ gRPC Vault qua mTLS) **đồng thời** phục vụ một service
  socket "engine native" qua Unix Domain Socket (UDS).
- `client/` (đang gọi gRPC Vault) **đồng thời** gọi service socket đó qua
  `SocketClient`.

```text
                 ┌───────────────────────────── server/ (1 process) ─────────────────────────────┐
   client/       │                                                                                 │
 (1 process)     │   GrpcAdapter()            -> Vault (code-first, mTLS động)  [server_id=default] │
   │             │   SocketAdapter("crypto")  -> CryptoEngine (UDS, msgpack)    [server_id=crypto]  │
   │  gRPC mTLS  │                                                                                 │
   ├────────────▶│   :50051  (TCP, mTLS)                                                            │
   │  UDS msgpack│                                                                                 │
   └────────────▶│   /tmp/xime/crypto.sock  (UDS, peercred + file permission)                      │
                 └─────────────────────────────────────────────────────────────────────────────────┘
```

Thông điệp dạy học: **cùng bộ contract `@command`/`@stream` + DTO Pydantic**, đổi
transport thì chỉ đổi adapter + cấu hình, không đổi cách viết controller.

## 2. Socket khác gRPC ở đâu (nhớ kỹ trước khi code)

| Khía cạnh | gRPC (đã có) | Socket (sắp thêm) |
|---|---|---|
| Transport | TCP, host:port | Unix Domain Socket (file `.sock`), cùng máy |
| Serialize | protobuf (có `.proto`) | **msgpack** (KHÔNG codegen, KHÔNG `.proto`) |
| Sinh mã | `xime grpc generate` + SDK client | **Không có bước sinh mã nào** |
| Bảo mật | mTLS động + Trust | **kernel: file permission (chmod/chown) + SO_PEERCRED** - KHÔNG TLS, KHÔNG Trust |
| Client | SDK sinh tự động, inject qua DI, trả DTO typed | `SocketClient(path)` dựng tay, trả **dict** (msgpack), không typed |
| Nền tảng | mọi OS | **chỉ Linux/macOS** (cần `asyncio.start_unix_server`) |
| Use case | service-to-service qua mạng | IPC cùng máy gọi native engine (C++/Rust/Go) |

Hệ quả quan trọng:

- **Không cần cụm Trust cho socket.** Socket dùng bảo mật kernel, nên phần socket
  đơn giản hơn hẳn gRPC: chỉ controller + use case + adapter + cấu hình.
- **msgpack chỉ gói được kiểu cơ bản** (str/int/float/bool/bytes/list/dict).
  `UUID`/`Decimal` để nguyên trong DTO socket sẽ **lỗi lúc `msgpack.packb`** (khác
  với sidecar fidelity của gRPC). Trong DTO socket hãy phơi ra `str` thay vì
  `UUID`/`Decimal`. Đây là điểm tương phản đáng dạy với gRPC.
- **Windows không chạy được UDS.** Trên Windows chỉ **viết code + viết unit
  test** (logic thuần: use case, builder, config). **E2E/chạy thật trên Linux**
  (test e2e tự `skipif` khi thiếu `start_unix_server`/`msgpack`).

## 3. Kịch bản demo: "Crypto Engine" native (qua UDS)

Bám sát ví dụ trong tài liệu chính thức `xime framework/docs/vn/socket-adapter.md`
để người đọc dễ đối chiếu. Server giả lập một engine native phủ đủ 3 kiểu endpoint:

| Endpoint | Kiểu | DTO vào -> ra | Ý nghĩa demo |
|---|---|---|---|
| `hash` | `@command` | `HashRequest{blob_id}` -> `HashResponse{digest}` | request/response đơn qua UDS |
| `encrypt` | `@stream` + `UploadStream` | `EncryptRequest{name}` + chunk bytes -> `EncryptResponse{total_bytes}` | client stream file lên engine |
| `download` | `@stream` + `DownloadStream` | `DownloadRequest{parts}` -> stream chunk bytes | engine stream kết quả về |

Logic giữ tối thiểu (hash bytes, đếm byte, phát vài chunk) - trọng tâm là
**đường đi socket + DI + msgpack + multiplex session**, không phải nghiệp vụ.

## 4. Server thêm gì (giữ nguyên cấu trúc, chỉ thêm file)

```text
server/app/
  api/
    grpc/          # (đã có) Vault code-first, server_id="default"
    socket/        # MỚI: CryptoEngineController.py, server_id="crypto"
  application/
    usecase/       # (đã có) + CryptoEngineUseCase.py
    dto/           # (đã có) + dto socket (hoặc đặt cạnh controller)
  config/
    grpc.py        # (đã có)
    socket.py      # MỚI: configure_socket_controllers + configure_socket_error_mappings
    dependency.py  # (sửa) thêm "app.api.socket" vào scan
  main.py          # (sửa) thêm app.use(SocketAdapter("crypto"))
  resources/application.yml   # (sửa) thêm khối socket:
```

Điểm cốt lõi (API thật theo `xime/adapters/socket`):

```python
# config/socket.py
from xime.adapters.socket import configure_socket_controllers
# Controller socket ở package riêng "app.api.socket" - KHÔNG trộn với gRPC.
# Cùng decorator @command/@stream nhưng adapter lọc theo package + server_id.
configure_socket_controllers("app.api.socket")

# main.py
app.use(GrpcAdapter())            # (đã có) phục vụ controller server_id="default"
app.use(SocketAdapter("crypto"))  # MỚI: phục vụ controller server_id="crypto"
```

> Bẫy y hệt gRPC: `CryptoEngineController.server_id` PHẢI khớp tham số của
> `SocketAdapter(...)`. `server_id="crypto"` thì phải `SocketAdapter("crypto")`;
> lệch nhau -> adapter không phục vụ controller nào (im lặng). Và package
> `app.api.socket` phải có trong CẢ `configure_socket_controllers` LẪN
> `dependency.scan(...)` (DI tạo instance trước khi adapter dựng bảng endpoint).

## 5. Client thêm gì

```text
client/app/
  application/
    usecase/   # (đã có) + CryptoEngineCallerUseCase.py: dùng SocketClient gọi 3 endpoint
    runner/    # (đã có) + CryptoDemoRunner (hoặc gộp vào demo hiện có)
  config/      # có thể không cần đổi (SocketClient không có configure_*_clients)
  resources/application.yml   # (sửa) thêm đường dẫn socket của server để client kết nối
```

Khác gRPC: **không có `configure_socket_clients`/DI tự nối kênh**. Client tự dựng
`SocketClient(path)` trong use case, path đọc từ `application.yml`:

```python
# application/usecase/CryptoEngineCallerUseCase.py (mẫu, theo _client.py)
from xime.adapters.socket import SocketClient

client = SocketClient(self._socket_path)   # path = đúng file .sock của server
await client.connect()
resp = await client.command("hash", HashRequest(blob_id="abc"))   # resp là dict
async with client.upload("encrypt", EncryptRequest(name="doc")) as up:
    await up.write(b"...")
    result = await up.finish()             # dict
chunks = [c async for c in client.download("download", DownloadRequest(parts=3))]
await client.close()
```

> Lưu ý API: tài liệu framework viết `client.stream(...)` cho upload, nhưng MÃ
> NGUỒN thật là `client.upload(...)` và `client.download(...)`. Theo mã nguồn.
> Response trả về là **dict** (msgpack), không phải DTO typed -> log theo key dict.

## 6. Ranh giới framework vs app (phần socket)

| Phần | Ai giữ |
|---|---|
| Wire protocol (frame 16B + msgpack), multiplex session, backpressure, reaper, peercred, chmod/chown, dịch lỗi -> code | **Framework** (`xime/adapters/socket`) |
| Controller + DTO + use case engine | **App** (phần "dạy") |
| Dựng `SocketClient`, gọi command/upload/download, đọc dict trả về | **App** (client) |

## 7. Kiểm thử (vì làm trên Windows, chạy thật trên Linux)

Bám cấu trúc test của framework `xime framework/tests_temp/socket/test_socket.py`:

- **Unit test (chạy mọi OS, gồm Windows):** test thẳng `CryptoEngineUseCase`
  (logic hash/đếm byte/phát chunk); test `SocketEndpointBuilder(...).build([...])`
  phân giải đúng shape (command/upload/download) và lọc `server_id`; test DTO
  hợp lệ. Không đụng socket thật.
- **E2E test (chỉ Linux + msgpack):** khởi động `SocketAdapter` trong tiến trình
  trên file `.sock` tạm rồi gọi qua `SocketClient` (command + upload + download +
  2 session đồng thời). Đánh dấu `skipif` khi thiếu `start_unix_server`/`msgpack`
  -> trên Windows tự bỏ qua, không báo đỏ.

Nguồn tham chiếu khi bí: `xime framework/docs/vn/socket-adapter.md` (hướng dẫn),
`xime/adapters/socket/` (mã nguồn: `_adapter.py`, `_client.py`, `_config.py`,
`routing/_builder.py`, `_protocol.py`), `tests_temp/socket/test_socket.py` (mẫu test).
