# Xime Framework - ví dụ tham khảo gRPC + Socket

[English](README.md) | **Tiếng Việt**

Ví dụ tham khảo CHÍNH THỨC cho thấy **một app Xime Framework chạy nhiều adapter
transport cùng lúc**:

- **gRPC** (code-first + mTLS động) - service "Vault".
- **Socket / Unix Domain Socket** (msgpack, bảo mật kernel) - "Crypto Engine" native.

Cả hai transport dùng **chung contract `@command`/`@stream` + Pydantic** - chỉ
khác transport và cách nối dây. Đây là bài học chính: viết controller một lần,
phục vụ qua nhiều transport.

```text
                ┌──────────────── server/ (một tiến trình) ──────────────┐
  client/       │  GrpcAdapter()           -> Vault         (gRPC, mTLS)   │
 (một tiến trình)│  SocketAdapter("crypto") -> Crypto Engine (UDS, msgpack)│
   ├─ gRPC ────▶│  :50051  (TCP, mTLS động qua Trust)                     │
   └─ UDS ─────▶│  /tmp/xime/crypto.sock  (peercred + file permission)    │
                └─────────────────────────────────────────────────────────┘
```

## Bố cục

| Thư mục | Là gì |
| --- | --- |
| [`server/`](server/) | App Xime: gRPC code-first (Vault) **và** Socket (Crypto Engine) |
| [`client/`](client/) | App Xime: gọi Vault qua SDK sinh tự động + DI, và Crypto Engine qua `SocketClient` |
| [`.claude/docs/`](.claude/docs/) | Kiến trúc + kế hoạch xây dựng từng bước (gRPC và socket) |
| [`van-de-framework/`](van-de-framework/) | Các vấn đề của framework phát hiện khi làm ví dụ này |

Mỗi thư mục `server/`/`client/` là một app Xime hoàn chỉnh, chạy riêng (`main.py`,
`config/`, `resources/application.yml`, `integration/trust/`).

## Mỗi transport minh hoạ gì

**gRPC (Vault)** - code-first: viết controller Python + DTO Pydantic, framework tự
sinh `.proto` + sidecar `contract.json` và phục vụ qua nối dây động. Client dùng
SDK sinh tự động, inject qua DI. Cả hai phía dùng **mTLS động** (cert bootstrap +
rotate qua Trust Service, không downtime).

**Socket (Crypto Engine)** - IPC cùng máy qua Unix Domain Socket để gọi native
engine (C++/Rust/Go). Không protobuf, không sinh mã: request/response đi dạng
**msgpack** dict. Bảo mật bằng **kernel** (file permission + SO_PEERCRED), nên
**KHÔNG TLS / KHÔNG Trust**.

## Lưu ý nền tảng (quan trọng)

Unix Domain Socket chỉ có trên **Linux/macOS**. Trên Windows, socket adapter và
demo socket được **guard** (bỏ qua) để nửa gRPC vẫn chạy khi dev. Chạy phần socket
thật trên Linux.

## Bắt đầu nhanh

```bash
# Cài framework + extra (chạy trên Linux cho phần socket)
pip install -e "D:\code\xime\xime framework"
pip install "xime[grpc]" "xime[socket]"

# Thứ tự demo: Trust Service -> server -> client
cd server && python -m app.main     # phục vụ gRPC (:50051) + socket (/tmp/xime/crypto.sock)
cd client && python -m app.main     # chạy demo Vault gRPC + demo Crypto Engine socket
```

Nửa gRPC/mTLS cần **Trust Service đang chạy** cùng secrets runtime
(`runtime/security/bootstrap.txt` + `ca.pem`) - xem README mỗi app và
`runtime/security/README.md`.

## Test

```bash
cd server && pip install -e ".[test]" && python -m pytest tests/
cd client && pip install -e ".[test]" && python -m pytest tests/
```

Unit test chạy mọi OS; e2e socket tự skip trên Windows, chạy trên Linux. Thư mục
`tests/grpc/` cố ý để trống (gRPC đã verify chạy live).

## Đọc tiếp

- Chi tiết từng app: [`server/README.md`](server/README.md), [`client/README.md`](client/README.md)
- Kiến trúc + kế hoạch: [`.claude/docs/`](.claude/docs/) (`kien-truc-vi-du.md`,
  `kien-truc-socket.md`, `ke-hoach-xay-dung.md`, `ke-hoach-socket.md`,
  `trust-integration.md`)
- Ngữ cảnh cho Claude Code: [`CLAUDE.md`](CLAUDE.md)
