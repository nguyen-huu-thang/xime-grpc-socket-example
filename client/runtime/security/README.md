# runtime/security (bí mật runtime - máy bạn tự cấp)

Thư mục này chứa cert mTLS của **client** (`service_id = "vault-client"`). Mọi file
bí mật ở đây đều bị `.gitignore` bỏ qua; chỉ riêng README này được commit để hướng dẫn.

## Cách nhanh nhất: chạy không cần Trust Service

mTLS ở ví dụ này có 2 giai đoạn: **bootstrap** (một lần, đổi token lấy cert qua
Trust Service) và **runtime** (các lần chạy sau chỉ LOAD cert từ file, KHÔNG gọi
Trust realtime). Vì vậy để chạy/nghiên cứu ví dụ, bạn chỉ cần sẵn cert + root CA.

Từ thư mục gốc repo, chạy một lần:

```bash
pip install cryptography
python tools/generate_dev_certs.py
```

Script sinh sẵn vào đây (và cả bên `server/`):

- `cert.json` - cert runtime; `private_key` và `refresh_token` mã hoá Fernet bằng
  `trust.cert_encryption_key` trong `resources/application.yml`.
- `ca-cert.pem` - root CA self-signed dùng chung cho cả server lẫn client (để mTLS
  hai phía tin nhau). Client dùng nó để verify cert phía server.

Sau đó (sau khi server đã lên) `python -m app.main` mở channel mTLS động tới
`localhost:50051` mà không cần Trust Service.

> Cert do script sinh là **self-signed CHỈ cho dev**, đừng dùng cho production.

## Muốn chạy luồng bootstrap thật (có Trust Service)

Đặt thêm vào đây:

- `bootstrap.txt` - file bootstrap cert lần đầu, do Trust Service cấp cho đúng
  `service_id = "vault-client"`. App dùng nó một lần rồi tự xoá sau khi rotate xong.

Nếu chưa có Trust Service, tham khảo/repo công khai để tự dựng:
<https://github.com/nguyen-huu-thang/trust-service> (hoặc liên hệ tác giả).

> Lưu ý trạng thái: có `bootstrap.txt` + chưa có `cert.json` -> chạy bootstrap; có
> `cert.json` + không có `bootstrap.txt` -> load từ file (ACTIVE); có cả hai ->
> app xoá cert cũ và bootstrap lại. Xem `TrustCertificateSynchronizer`.

Tất cả file bí mật ở đây ĐỪNG commit (đã có trong `.gitignore`).
