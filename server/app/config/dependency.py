from xime.core.config.binding import BindingConfig
from xime.core.transaction.manager import TransactionManager

from app.application.port.outbound.trust.LoadCertificatePort import LoadCertificatePort
from app.application.port.outbound.trust.SaveCertificatePort import SaveCertificatePort
from app.integration.trust.bootstrap.Bootstrap import Bootstrap
from app.integration.trust.store.FileCertificateStore import FileCertificateStore
from app.integration.trust.store.NoOpTransactionManager import NoOpTransactionManager

# DI configuration for the Vault gRPC server example.
# Framework reads the `dependency` variable at startup. All scanned classes must
# have fully type-hinted constructors.
# Cấu hình DI cho ví dụ server gRPC Vault. Framework đọc biến `dependency` lúc
# khởi động. Mọi class được scan phải có constructor đủ type hint.

dependency = BindingConfig()

# Bootstrap builds its loader/validator internally, so it is registered
# explicitly rather than scanned.
# Bootstrap tự dựng loader/validator bên trong nên đăng ký thủ công thay vì scan.
dependency.register(Bootstrap)

dependency.scan(
    # Code-first gRPC controller (also passed to configure_grpc_codefirst).
    "app.api.grpc",
    # Socket controller (also passed to configure_socket_controllers).
    # Controller socket (cũng truyền vào configure_socket_controllers).
    "app.api.socket",
    # Business logic (gRPC Vault + socket Crypto Engine use cases).
    "app.application.usecase",
    # Trust integration (cert / mTLS only - file-backed).
    "app.integration.trust.publicca",
    "app.integration.trust.certificate",
    "app.integration.trust.ssl",
    "app.integration.trust.startup",
    "app.integration.trust.scheduler",
    "app.integration.trust.store",
)

dependency.bind({
    # File-backed persistence replaces the DB: no transaction, flat-file cert store.
    # Persistence dạng file thay DB: không transaction, store cert file phẳng.
    TransactionManager: NoOpTransactionManager,
    LoadCertificatePort: FileCertificateStore,
    SaveCertificatePort: FileCertificateStore,
})
