from xime.core.config.binding import BindingConfig
from xime.core.transaction.manager import TransactionManager

from app.application.port.outbound.trust.LoadCertificatePort import LoadCertificatePort
from app.application.port.outbound.trust.SaveCertificatePort import SaveCertificatePort
from app.integration.trust.bootstrap.Bootstrap import Bootstrap
from app.integration.trust.store.FileCertificateStore import FileCertificateStore
from app.integration.trust.store.NoOpTransactionManager import NoOpTransactionManager

# DI configuration for the Vault gRPC client example.
# Cấu hình DI cho ví dụ client gRPC Vault.

dependency = BindingConfig()

dependency.register(Bootstrap)

dependency.scan(
    # Caller use case + the startup demo runner.
    "app.application.usecase",
    "app.application.runner",
    # Trust integration (cert / mTLS only - file-backed), same as the server.
    "app.integration.trust.publicca",
    "app.integration.trust.certificate",
    "app.integration.trust.ssl",
    "app.integration.trust.startup",
    "app.integration.trust.scheduler",
    "app.integration.trust.store",
)

dependency.bind({
    TransactionManager: NoOpTransactionManager,
    LoadCertificatePort: FileCertificateStore,
    SaveCertificatePort: FileCertificateStore,
})
