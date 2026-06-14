# CLAUDE.md - Ví dụ tham khảo gRPC + Socket trên Xime Framework

File này cung cấp ngữ cảnh cho Claude Code khi làm việc tại repo này.

## Mục tiêu repo

Đây là **ví dụ tham khảo CHÍNH THỨC về gRPC và Socket do Xime Framework hỗ trợ** -
để người khác đọc và học cách:

1. Viết một **gRPC server code-first** (controller Python + DTO Pydantic, framework
   tự sinh `.proto`, phục vụ qua nối dây động).
2. Viết một **gRPC client** gọi server đó bằng **SDK sinh tự động + Dependency
   Injection** (không dựng channel tay, không marshal protobuf).
3. Cả hai app tích hợp **Trust Service**: bootstrap cert lần đầu + rotate cert
   định kỳ, giao tiếp **mTLS động** (cert xoay không downtime) - giống data-service.
4. **Một app chạy nhiều adapter cùng lúc**: cùng tiến trình, server vừa phục vụ
   gRPC (Vault) vừa phục vụ **Socket/UDS** (Crypto Engine native); client gọi cả
   hai. Socket dùng **msgpack** (không codegen) + bảo mật **kernel** (file
   permission + SO_PEERCRED), KHÔNG TLS/Trust - chỉ chạy Linux/macOS.

Repo gồm hai ứng dụng Xime độc lập:

```text
gRPC socket/
├─ server/    # App Xime: gRPC code-first (Vault) + Socket/UDS (Crypto Engine)
└─ client/    # App Xime: gọi server qua SDK gRPC + SocketClient
```

Mỗi thư mục con là **một app Xime hoàn chỉnh, chạy riêng** (main.py, config/,
resources/application.yml, integration/trust/, ...). Cả hai cùng nói chuyện với
một Trust Service đang chạy.

> **Trạng thái (2026-06-13): cả hai app đã code xong, gRPC verify chạy LIVE OK.**
> server/ (code-first Vault + mTLS động) và client/ (SDK + DI + mTLS động) chạy
> live thành công (3 RPC + mTLS + rotate). Phần **Socket** (Crypto Engine) đã có
> đủ code + test; unit test xanh trên Windows, **e2e + chạy live trên Linux**
> (UDS không có trên Windows nên đã guard theo nền tảng).
> Persistence cert dùng **file** (không DB) - xem README mỗi app. Cụm trust copy
> từ data-service, **chỉ phần cert/mTLS** (bỏ cụm verification-key JWT cho gọn).
> Kế hoạch/thiết kế gốc trong `.claude/docs/`; vấn đề framework gặp phải ghi ở
> `van-de-framework/` (ghi chú NỘI BỘ, đã gitignore - không có khi clone bản công khai).

## Đọc trước khi bắt đầu (theo thứ tự)

1. `.claude/docs/kien-truc-vi-du.md` - kiến trúc ví dụ gRPC, kịch bản demo Vault.
2. `.claude/docs/ke-hoach-xay-dung.md` - checklist xây dựng gRPC (server, client).
3. `.claude/docs/trust-integration.md` - cách đưa cụm Trust (bootstrap + rotate
   cert + mTLS động) vào cả hai app, sao chép từ data-service.
4. `.claude/docs/kien-truc-socket.md` - kiến trúc phần Socket (Crypto Engine) thêm
   vào CHÍNH hai app này; khác biệt với gRPC.
5. `.claude/docs/ke-hoach-socket.md` - checklist phần Socket (server, client, test).

## Nguồn tham chiếu (quan trọng)

Ví dụ này KẾT HỢP ba mảng đã có sẵn ở nơi khác - khi bí, mở đúng nguồn:

| Mảng | Nguồn tham chiếu tốt nhất |
|---|---|
| Framework (tổng quan, DI, rules) | `D:\code\xime\xime framework\CLAUDE.md` + `.claude/rules/` |
| Code-first server (controller, DTO, generate, serve) | Tài liệu `xime framework/docs/vn/grpc-codefirst.md`; test e2e `xime framework/tests_temp/grpc_codefirst/test_codefirst_e2e.py` |
| Client SDK + DI + mTLS động | Tài liệu `xime framework/docs/vn/grpc-client.md`; test `xime framework/tests_temp/grpc_client/test_client_sdk_e2e.py` + `test_channel_e2e.py` |
| Trust integration (bootstrap, resolver, scheduler, provider) | **data-service** `D:\code\xime\Base Platform\data\app\integration\trust\` + hướng dẫn `data\.claude\docs\migrate-grpc-client-mtls.md` |
| Socket (UDS, msgpack, peercred) | Tài liệu `xime framework/docs/vn/socket-adapter.md`; mã nguồn `xime/adapters/socket/`; test mẫu `xime framework/tests_temp/socket/test_socket.py` |

> **data-service code trước ví dụ này.** Người dùng sẽ code/migrate data-service
> xong rồi mới làm ví dụ này. Cụm `integration/trust/` của data-service là khuôn
> mẫu để sao chép sang cả server/ lẫn client/.

## Ngôn ngữ & framework

**Python + Xime Framework** (cài từ local):

```bash
pip install -e "D:\code\xime\xime framework"
```

Quy tắc code Xime (đọc `xime framework/.claude/rules/coding.md`): constructor
injection, không annotation DI, interface là `Protocol`, bind tường minh trong
`config/dependency.py`, fail fast lúc startup.

## Chạy ứng dụng (sau khi đã code)

**Không cần Trust Service để chạy ví dụ.** mTLS có 2 giai đoạn: bootstrap (một lần,
đổi token lấy cert qua Trust) và runtime (các lần sau chỉ load cert từ
`runtime/security/cert.json`, không gọi Trust realtime). Sinh sẵn cert dev cho cả
hai app rồi chạy:

```bash
# 0. Sinh cert dev (CA + cert server/client) vào runtime/security/ - chạy từ root repo
python tools/generate_dev_certs.py

# Mỗi app chạy độc lập (ưu tiên hai terminal)
cd server && python -m app.main     # gRPC (mTLS, code-first) + Socket (Linux)
cd client && python -m app.main     # gọi server qua SDK gRPC + SocketClient

# Sinh mã gRPC (chạy trong từng app khi cần) - LƯU Ý: xime không trên PATH ở máy
# này + config ở app.config, nên gọi qua entry point:
cd server && python -c "from xime.cli._main import main; main()" grpc generate --config app.config
cd client && python -c "from xime.cli._main import main; main()" grpc client --proto contracts/vault --out clients/vault
```

Thứ tự khởi động khi demo: server → client (cert sinh sẵn ở bước 0). Muốn chạy
luồng bootstrap thật thì cần Trust Service (xem `runtime/security/README.md` và
<https://github.com/nguyen-huu-thang/trust-service>).

**Socket (UDS) chỉ chạy Linux/macOS.** Trên Windows phần socket tự bỏ qua (đã
guard), chỉ gRPC chạy. Trước khi chạy thật trên Linux: `pip install "xime[socket]"`
(kéo `msgpack`). Server bind `/tmp/xime/crypto.sock`; client đọc path đó từ
`crypto_engine.socket_path`.

Test: `cd server && pip install -e ".[test]" && python -m pytest tests/` (tương tự
cho client). Unit chạy mọi OS; e2e socket tự skip trên Windows, chạy trên Linux.

## Quy ước viết tài liệu/comment (toàn repo)

- Tài liệu, CLAUDE.md, comment: tiếng Việt (comment code: English trên, tiếng
  Việt dưới).
- KHÔNG dùng em dash (—) hay en dash (–); dùng dấu trừ thường "-".
- Đây là tài liệu tham khảo cho người khác đọc → ưu tiên rõ ràng, có comment
  giải thích "vì sao", không chỉ "làm gì".
