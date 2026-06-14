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
# 1. Tạo môi trường ảo (khuyến nghị dùng chung cho cả server + client)
python3 -m venv .venv
source .venv/bin/activate          # Linux/macOS
# .venv\Scripts\activate           # Windows

# 2. Cài framework + extras
pip install "xime[grpc,socket,scheduler]"
pip install cryptography           # mã hoá cert khi lưu file

# 3. Cài server và client ở chế độ editable
pip install -e "./server[test]"
pip install -e "./client[test]"

# 4. Sinh cert dev để mTLS chạy được mà KHÔNG cần Trust Service
python tools/generate_dev_certs.py

# 5. Chạy (hai terminal)
cd server && python -m app.main    # phục vụ gRPC (:50051) + socket (/tmp/xime/crypto.sock)
cd client && python -m app.main    # chạy demo Vault gRPC + demo Crypto Engine socket
```

**Không cần Trust Service để chạy ví dụ.** mTLS có 2 giai đoạn: **bootstrap** một
lần (đổi token lấy cert thật qua Trust Service) và giai đoạn **runtime** (các lần
chạy sau chỉ LOAD cert từ `runtime/security/cert.json`, không gọi Trust realtime,
chỉ liên hệ lại khi cert sắp hết hạn và cần rotate). `tools/generate_dev_certs.py`
ghi sẵn CA + cert dev vào giai đoạn runtime nên cả hai app tự khởi động và mTLS với
nhau. Muốn xem luồng bootstrap/rotate thật với Trust Service, nghiên cứu
<https://github.com/nguyen-huu-thang/trust-service> (hoặc `runtime/security/README.md`
của mỗi app).

> **Lưu ý PyPI**: `pip install "xime[all]"` có thể lỗi nếu bản PyPI đang dùng
> `apscheduler>=4.0` (chưa có bản stable). Dùng `xime[grpc,socket,scheduler]`
> để bỏ qua extra `all`, hoặc cài từ source local:
> `pip install -e "<path-tới-xime-framework>[all]"`.

## Test

```bash
cd server && pip install -e ".[test]" && python -m pytest tests/
cd client && pip install -e ".[test]" && python -m pytest tests/
```

Unit test chạy mọi OS; e2e socket tự skip trên Windows, chạy trên Linux.
`server/tests/grpc/` có unit test cho VaultUseCase; phần dây gRPC đầy đủ (code-first
+ mTLS động) đã verify chạy live.

## Đọc tiếp

- Chi tiết từng app: [`server/README.md`](server/README.md), [`client/README.md`](client/README.md)
- Kiến trúc + kế hoạch: [`.claude/docs/`](.claude/docs/) (`kien-truc-vi-du.md`,
  `kien-truc-socket.md`, `ke-hoach-xay-dung.md`, `ke-hoach-socket.md`,
  `trust-integration.md`)
- Ngữ cảnh cho Claude Code: [`CLAUDE.md`](CLAUDE.md)
