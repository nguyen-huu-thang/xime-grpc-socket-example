from xime import Application

# Vault gRPC client (SDK + DI + dynamic mTLS).
# Logging is auto-configured by the framework at bootstrap (tune via the
# `logging:` block in resources/application.yml) - no basicConfig needed here.
# No adapter: the demo call runs in VaultDemoRunner.post_construct at startup,
# then the app idles (Ctrl+C to exit). Config auto-discovered from app.config.*.
# Client gRPC Vault (SDK + DI + mTLS động). Logging do framework tự cấu hình lúc
# bootstrap (chỉnh qua khối `logging:` trong resources/application.yml). Không
# adapter: lời gọi demo chạy trong VaultDemoRunner.post_construct lúc khởi động,
# sau đó app đứng chờ (Ctrl+C để thoát). Config tự khám phá từ app.config.*.
app = Application()

if __name__ == "__main__":
    app.run()
