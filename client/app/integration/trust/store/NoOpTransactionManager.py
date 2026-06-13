from __future__ import annotations


class _NoOpTransaction:
    """Async context manager that does nothing - file storage needs no transaction.

    Mirrors the TransactionContext shape (begin/commit/rollback) but is a no-op,
    so the trust synchronizers can keep their `async with self._tx():` blocks
    unchanged whether persistence is a database or a flat file.
    Async context manager rỗng - lưu file không cần transaction. Giữ đúng hình
    dạng TransactionContext để synchronizer dùng `async with self._tx():` như cũ,
    bất kể persistence là DB hay file.
    """

    async def __aenter__(self) -> "_NoOpTransaction":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


class NoOpTransactionManager:
    """TransactionManager implementation for file-backed persistence (no DB).

    The example stores certs in a flat file, so there is no transaction to open.
    Bound to TransactionManager in config/dependency.py.
    Bản TransactionManager cho persistence dạng file (không DB). Ví dụ lưu cert ra
    file nên không có transaction để mở. Bind vào TransactionManager trong
    config/dependency.py.
    """

    def __call__(self) -> _NoOpTransaction:
        return _NoOpTransaction()
