from xime.adapters.socket import (
    configure_socket_controllers,
    configure_socket_error_mappings,
)

# Register the package that holds socket controllers. Kept separate from the gRPC
# package (app.api.grpc): both transports share the same @command/@stream
# decorators, so each adapter must scan ONLY its own package. This package MUST
# also appear in dependency.scan() (config/dependency.py) so the DI container
# builds the controller instance before SocketAdapter builds its endpoint table.
# Đăng ký package chứa controller socket. Tách khỏi package gRPC: hai transport
# dùng chung decorator @command/@stream, nên mỗi adapter chỉ quét package của
# mình. Package này PHẢI cũng nằm trong dependency.scan() để DI tạo instance
# controller trước khi SocketAdapter dựng bảng endpoint.
configure_socket_controllers("app.api.socket")

# Map business exceptions to the error codes the client receives. Unmapped
# exceptions default to "INTERNAL"; the failing session ends without crashing the
# server. Left empty here (the demo has no custom exceptions) but shown for
# reference - mirrors configure_grpc_error_mappings on the gRPC side.
# Ánh xạ exception nghiệp vụ sang mã lỗi client nhận. Exception không map mặc định
# "INTERNAL"; session lỗi kết thúc mà không làm sập server. Để trống ở đây (demo
# chưa có exception riêng) nhưng nêu ra để tham khảo.
configure_socket_error_mappings({})
