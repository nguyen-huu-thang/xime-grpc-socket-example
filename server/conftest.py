import os
import sys

# Make the `app` package importable when running pytest from the server directory.
# Cho phép import package `app` khi chạy pytest từ thư mục server.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
