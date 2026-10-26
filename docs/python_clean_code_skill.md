# SKILL: Python Clean Code & Scalability Standards (`python_clean_code.md`)

**Phạm vi áp dụng:** Toàn bộ mã nguồn Backend Core (FastAPI, State Machine, Plugin Adapters) viết bằng Python.

## 1. Triết lý Kiến trúc & Modular (Zero-Mess Architecture)
* **Strict Separation of Concerns:** Không bao giờ viết business logic hoặc gọi trực tiếp database driver bên trong file route của FastAPI (`api_routes.py`). Phải đi qua tầng Service / Engine (ví dụ: `engine/state_machine.py`).
* **Dependency Injection:** Sử dụng cơ chế Dependency Injection của FastAPI cho Database Session và các Service để dễ Unit Test và không bị tightly-coupled.
* **No Hardcoding:** Mọi cấu hình kết nối, timeout (15s/30s), hoặc threshold phải nằm trong file `config.py` dùng `pydantic-settings`, tuyệt đối không rải rác magic numbers trong code.

## 2. Quy chuẩn Viết Code Python (Pythonic & Typing)
* **Type Hinting Bắt buộc:** 100% các hàm, phương thức phải có đầy đủ type hints cho tham số và giá trị trả về (Return type). Sử dụng `pydantic` models cho mọi Request/Response payload.
* **Async/Await Discipline:** Tận dụng triệt để `async/await` cho các tác vụ I/O bound (gọi subprocess plugin, query SQLite, HTTP request). Sử dụng `asyncio.wait_for` cho các cơ chế timeout guard.
* **Custom Exception Handling:** Không dùng `except Exception:` chung chung. Phải định nghĩa các Custom Exceptions rõ ràng (VD: `PluginExecutionError`, `RuleViolationError`, `ExecutionTimeoutError`) để tầng Gateway bắt và trả về mã lỗi HTTP chuẩn xác cho AI/UI.

## 3. Quy chuẩn Quản lý Tiến trình Plugin (Subprocess & Stdio)
* Khi gọi Plugin qua Subprocess (JSON-RPC), luôn luôn bọc trong `try...finally` để đảm bảo process con bị terminate/kill đúng cách khi gặp ngoại lệ hoặc timeout, tránh để lại process mồ cô (orphan processes) gây rò rỉ tài nguyên hệ thống.
