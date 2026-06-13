# Xime Framework - gRPC + Socket reference example

**English** | [Tiếng Việt](README-vn.md)

Official reference example showing how a single **Xime Framework** app runs
**multiple transport adapters at once**:

- **gRPC** (code-first + dynamic mTLS) - a "Vault" service.
- **Socket / Unix Domain Socket** (msgpack, kernel security) - a native
  "Crypto Engine".

Both transports share the **same `@command`/`@stream` + Pydantic contract** - only
the transport and wiring differ. This is the main lesson: write the controller
once, serve it over different transports.

```text
                ┌──────────────── server/ (one process) ─────────────────┐
  client/       │  GrpcAdapter()           -> Vault         (gRPC, mTLS)   │
 (one process)  │  SocketAdapter("crypto") -> Crypto Engine (UDS, msgpack)│
   ├─ gRPC ────▶│  :50051  (TCP, dynamic mTLS via Trust)                  │
   └─ UDS ─────▶│  /tmp/xime/crypto.sock  (peercred + file permission)    │
                └─────────────────────────────────────────────────────────┘
```

## Layout

| Folder | What it is |
| --- | --- |
| [`server/`](server/) | Xime app: gRPC code-first (Vault) **and** Socket (Crypto Engine) |
| [`client/`](client/) | Xime app: calls Vault via generated SDK + DI, and the Crypto Engine via `SocketClient` |
| [`.claude/docs/`](.claude/docs/) | Architecture + step-by-step build plans (gRPC and socket) |
| [`van-de-framework/`](van-de-framework/) | Framework issues found while building this example |

Each folder under `server/`/`client/` is a complete, independently-runnable Xime
app (`main.py`, `config/`, `resources/application.yml`, `integration/trust/`).

## What each transport demonstrates

**gRPC (Vault)** - code-first: write a Python controller + Pydantic DTOs, the
framework generates `.proto` + a `contract.json` sidecar and serves it by dynamic
wiring. The client uses an auto-generated SDK injected through DI. Both sides do
**dynamic mTLS** (certs bootstrapped + rotated via a Trust Service, no downtime).

**Socket (Crypto Engine)** - local IPC over a Unix Domain Socket for talking to
native engines (C++/Rust/Go). No protobuf, no codegen: requests/responses travel
as **msgpack** dicts. Security is **kernel-based** (file permission + SO_PEERCRED),
so **no TLS / no Trust**.

## Platform note (important)

Unix Domain Sockets exist only on **Linux/macOS**. On Windows the socket adapter
and socket demo are **guarded** (skipped), so the gRPC half still runs for
development. Run the socket parts for real on Linux.

## Quick start

```bash
# Install the framework + extras (run on Linux for the socket parts)
pip install -e "D:\code\xime\xime framework"
pip install "xime[grpc]" "xime[socket]"

# Start order for a demo: Trust Service -> server -> client
cd server && python -m app.main     # serves gRPC (:50051) + socket (/tmp/xime/crypto.sock)
cd client && python -m app.main     # runs the gRPC Vault demo + the socket Crypto Engine demo
```

You need a running **Trust Service** plus the runtime secrets
(`runtime/security/bootstrap.txt` + `ca.pem`) for the gRPC/mTLS half - see each
app's README and `runtime/security/README.md`.

## Tests

```bash
cd server && pip install -e ".[test]" && python -m pytest tests/
cd client && pip install -e ".[test]" && python -m pytest tests/
```

Unit tests run on any OS; socket end-to-end tests auto-skip on Windows and run on
Linux. The `tests/grpc/` folders are intentionally empty (gRPC is verified live).

## Read next

- Per-app details: [`server/README.md`](server/README.md), [`client/README.md`](client/README.md)
- Architecture + plans: [`.claude/docs/`](.claude/docs/) (`kien-truc-vi-du.md`,
  `kien-truc-socket.md`, `ke-hoach-xay-dung.md`, `ke-hoach-socket.md`,
  `trust-integration.md`)
- Project context for Claude Code: [`CLAUDE.md`](CLAUDE.md)
