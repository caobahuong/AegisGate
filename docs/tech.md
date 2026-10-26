# TECHNICAL SPECIFICATION & TECH STACK (`tech.md`)
**Tên dự án:** AegisGate
**Mục tiêu tài liệu:** Cung cấp chi tiết các lựa chọn về Công nghệ (Tech Stack), Kiến trúc Kỹ thuật thực thi, Giao thức truyền thông giữa Core và Plugin, cũng như cấu trúc mã nguồn để đội ngũ phát triển hoặc AI Coding Agent bắt tay vào hiện thực hóa hệ thống AegisGate.

---

## 1. Tổng quan Lựa chọn Công nghệ (Tech Stack Overview)

| Phân hệ (Layer) | Công nghệ lựa chọn | Lý do và Đặc tả |
| :--- | :--- | :--- |
| **Backend Core** | **Python 3.11+ / FastAPI** | • Hệ sinh thái AI/LLM mạnh mẽ nhất.<br>• Hỗ trợ native `async/await` tối ưu cho các bộ đếm thời gian (timeout 15s/30s).<br>• Tích hợp sẵn chuẩn **Model Context Protocol (MCP)** Python SDK. |
| **Plugin Protocol** | **JSON-RPC over Stdio / Subprocess** | • Cho phép viết Plugin bằng bất kỳ ngôn ngữ nào (C#, Python, Go, Node.js).<br>• Cách ly hoàn toàn tiến trình (Process Isolation): Nếu Plugin bị treo hoặc crash, Core không bị ảnh hưởng. |
| **Frontend UI** | **Next.js (React) + TypeScript + Tailwind CSS + shadcn/ui** | • Xây dựng Dashboard quản trị nội bộ cực kỳ mượt mà, hiện đại.<br>• Hỗ trợ Server-Sent Events (SSE) hoặc WebSocket để hiển thị real-time trạng thái chạy lệnh của AI. |
| **Core Storage** | **SQLite (via SQLModel / SQLAlchemy) + Markdown (`.md`)** | • Gọn nhẹ, toàn bộ dữ liệu cấu hình, rules và logs nằm trong 1 file `aegisgate.db` duy nhất.<br>• Các tài liệu `doc.md` và `skills` lưu dạng file text thuần để dễ dàng chỉnh sửa. |

---

## 2. Kiến trúc Mã nguồn (Project Directory Structure)

Dự án được thiết kế theo mô hình Modular Monolith, tách biệt hoàn toàn giữa Core và các Plugins độc lập:

```text
AegisGate/
│
├── core/                        # Nền tảng lõi (Backend - FastAPI)
│   ├── main.py                  # Khởi chạy FastAPI & MCP Server
│   ├── database.py              # Kết nối SQLite & Models (SQLModel)
│   ├── engine/                  # State Machine & Execution Gatekeeper
│   │   ├── state_machine.py     # Quản lý luồng: DryRun -> Pause -> Execute -> Log
│   │   ├── timeout_guard.py     # Bộ đếm thời gian thực thi (15 or 30 seconds)
│   │   └── governance.py        # Đối chiếu Rules (Cấm Join, Cấm Table Scan...)
│   ├── gateway/                 # Cổng giao tiếp AI
│   │   ├── mcp_server.py        # Cung cấp 4 MCP Tools cho AI Agent
│   │   └── api_routes.py        # REST API cho Frontend Dashboard
│   └── storage/                 # Kho lưu trữ Knowledge, Rules, Logs
│
├── plugins/                     # Thư mục chứa các Plugin độc lập (Cắm rời)
│   ├── plugin_contract.py       # Định nghĩa Interface chuẩn mà mọi plugin phải tuân theo
│   ├── sqlserver_plugin/        # Plugin mẫu cho SQL Server (Python/C#)
│   │   ├── plugin_manifest.json # Khai báo thông tin plugin
│   │   ├── adapter.py           # Thực thi Sync, DryRun (Showplan), Execute, Abort
│   │   └── requirements.txt     # Thư viện riêng của plugin (ví dụ: pyodbc)
│   └── mongodb_plugin/          # Plugin mẫu cho MongoDB (Ví dụ mở rộng)
│
├── frontend/                    # Giao diện Web Dashboard (Next.js)
│   ├── src/app/                 # Các trang: Live Monitor, Rules, Knowledge, Logs
│   └── components/              # UI components (shadcn/ui)
│
├── data/                        # Thư mục dữ liệu nội bộ
│   ├── aegisgate.db             # File SQLite lưu trữ chính của Core
│   └── knowledge_docs/          # Thư mục chứa các file doc.md, skills.md
│
└── project_architecture_business_plan.md # Tài liệu đặc tả bài toán & nghiệp vụ (plan.md)
```

---

## 3. Cơ chế Giao tiếp giữa Core và Plugin (Plugin Communication Protocol)

Để đảm bảo tính trung lập ("không thiết kế riêng cho bên thứ 3 nào"), Core và Plugin giao tiếp thông qua **Tiến trình con (Subprocess)** sử dụng chuẩn **JSON-RPC qua dòng lệnh Stdio** hoặc **giao thức IPC cục bộ**.

### 3.1. Vòng đời khởi tạo Plugin của Core
1. Khi khởi động, Core đọc thư mục `plugins/` và nạp các `plugin_manifest.json`.
2. Core bật tiến trình Plugin dưới dạng một Child Process (ví dụ: `python plugins/sqlserver_plugin/adapter.py`).
3. Core gửi các lệnh qua `stdin` của tiến trình con dưới dạng chuỗi JSON và nhận kết quả phản hồi qua `stdout`.

### 3.2. Cấu trúc JSON-RPC Request/Response chuẩn

* **Lệnh đồng bộ cấu trúc (`sync_knowledge`):**
  * **Request (Core -> Plugin):**
    ```json
    {"jsonrpc": "2.0", "method": "sync_knowledge", "params": {"config": {"host": "localhost", "db": "Prod"}}, "id": 1}
    ```
  * **Response (Plugin -> Core):** Trả về gói JSON chứa danh sách bảng, cột, kiểu dữ liệu và index chuẩn hóa.

* **Lệnh kiểm tra trước (`dry_run`):**
  * **Request (Core -> Plugin):** Truyền câu query của AI và bộ rules.
  * **Response (Plugin -> Core):** Trả về `is_valid`, `violations`, và dữ liệu `explain_plan`.

* **Lệnh thực thi thật (`execute`):**
  * **Request (Core -> Plugin):** Truyền `execution_id`, câu query, và `timeout_seconds`.
  * **Response (Plugin -> Core):** Trả về kết quả dữ liệu (`data`) hoặc lỗi timeout.

* **Lệnh hủy khẩn cấp (`abort`):**
  * **Request (Core -> Plugin):** Truyền `execution_id` đang chạy dở.
  * **Response (Plugin -> Core):** Plugin chủ động gọi hàm hủy kết nối / `KILL` tiến trình dưới Database và trả về trạng thái thành công.

---

## 4. Chi tiết Công nghệ từng Phân hệ

### 4.1. Backend Core (FastAPI + MCP)
* **Thư viện chính:** `fastapi`, `uvicorn`, `mcp` (Model Context Protocol official SDK), `sqlmodel`, `pydantic`.
* **Xử lý Bất đồng bộ & Timeout:** Sử dụng `asyncio.wait_for` để bọc các thao tác gọi Plugin. Nếu thời gian vượt quá ngưỡng quy định, FastAPI tự động gửi lệnh `abort` xuống Plugin để giải phóng tài nguyên.

### 4.2. Hệ thống Lưu trữ Core (SQLite + Markdown)
* **SQLite Database (`aegisgate.db`):** Quản lý thông tin kết nối, ánh xạ trạng thái execution logs, rule cấu hình, và metadata của Knowledge Chunks.
* **Knowledge Store (Hybrid):**
  * Metadata dạng cấu trúc bảng/cột lưu trong SQLite.
  * Nội dung giải thích chi tiết (`doc.md`, `skills.md`) lưu trực tiếp thành file text trong thư mục `data/knowledge_docs/` để lập trình viên hoặc AI dễ dàng đọc/ghi bằng các công cụ code thông thường.

### 4.3. Giao diện Frontend (Next.js Dashboard)
* **Thư viện chính:** `Next.js App Router`, `Tailwind CSS`, `shadcn/ui`, `lucide-react` (icons).
* **Real-time Engine:** Sử dụng **Server-Sent Events (SSE)** từ FastAPI đẩy sự kiện về Next.js ngay khi AI tạo ra một request mới.
