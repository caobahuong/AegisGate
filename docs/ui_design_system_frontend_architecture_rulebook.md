# UI DESIGN SYSTEM & FRONTEND ARCHITECTURE RULEBOOK (`design.md`)

**Tên tài liệu:** Quy chuẩn Thiết kế Giao diện & Kiến trúc Frontend (Design System & UI Rules)
**Mục tiêu:** Tài liệu này đóng vai trò là "Luật bất thành văn" (Rulebook) bắt buộc mọi AI Coding Agent hoặc Developer phải tuân thủ khi xây dựng, mở rộng hoặc chỉnh sửa giao diện Frontend cho dự án **AegisGate**.

---

## 1. Triết lý Thiết kế & Cảm giác Trải nghiệm (UX Philosophy)

* **Bản chất sản phẩm:** Đây là một công cụ Quản trị Nền tảng, Giám sát Thời gian thực và Kiểm soát Cổng (Enterprise DevOps & Database Admin Tool). Do đó, giao diện phải toát lên sự **chính xác, an toàn, tốc độ và tối giản**.
* **Dark-First Theme:** Sử dụng giao diện tối (Dark Mode) làm mặc định tuyệt đối. Giao diện tối giúp giảm mỏi mắt khi làm việc lâu với code/log, đồng thời tạo điểm nhấn trực quan cực mạnh cho các trạng thái cảnh báo (Lỗi, Vi phạm Rule, Timeout).

---

## 2. Hệ thống Màu sắc Chủ đạo (Color Palette)

Mọi màu sắc sử dụng trong ứng dụng phải tuân thủ nghiêm ngặt bảng quy chuẩn sau (sử dụng cấu trúc màu của **Tailwind CSS**):

| Nhóm màu | Mã màu / Token | Mục đích sử dụng |
| :--- | :--- | :--- |
| **Nền chính (Background)** | `bg-slate-950` (`#020617`) | Màu nền toàn cục của trang ứng dụng. |
| **Nền thành phần (Surface)** | `bg-slate-900` (`#0f172a`) | Màu nền của các card, sidebar, header, modal. |
| **Đường viền (Borders)** | `border-slate-800` (`#1e293b`) | Phân tách các khối, card, bảng dữ liệu. |
| **Màu nhận diện (Brand / Primary)** | `indigo-600` (`#4f46e5`) / `indigo-500` | Nút bấm hành động chính (Primary Actions), tab đang chọn, icon chủ đạo. |
| **Trạng thái Thành công (Success)** | `emerald-500` / `emerald-400` | Trạng thái `COMPLETED`, `AUTO ON`, kết nối thông suốt, Dry-Run pass. |
| **Trạng thái Cảnh báo / Chờ (Warning)** | `amber-500` / `amber-400` | Trạng thái `PAUSED_FOR_REVIEW`, Auto Mode OFF, Dry-Run có lưu ý. |
| **Trạng thái Nguy hiểm / Lỗi (Danger)** | `red-500` / `red-400` | Trạng thái `REJECTED`, `TIMEOUT`, vi phạm rule cấm JOIN, nút Kill/Stop. |
| **Kiểu chữ (Text Colors)** | `text-slate-100` (Chính), `text-slate-400` (Phụ/Mô tả), `text-slate-500` (Mờ/Disabled) | Phân cấp độ rõ ràng cho văn bản. |

---

## 3. Kiểu chữ & Cỡ chữ (Typography)

* **Font Giao diện (Sans-Serif):** Sử dụng `Inter` cho toàn bộ tiêu đề, nhãn (labels), nút bấm và văn bản thông thường.
* **Font Mã nguồn & Query (Monospace):** Sử dụng `JetBrains Mono` bắt buộc cho mọi khung chứa câu lệnh SQL, mã JSON, Execution Plan, ID phiên chạy (`#exec_88192`) và chuỗi kết nối.
* **Quy chuẩn Phân cấp Cỡ chữ:**
  * **Page Title / Header:** `text-sm font-bold` (14px - 16px, gọn gàng, không cồng kềnh).
  * **Section Headers / Card Titles:** `text-xs font-bold uppercase tracking-wider` (12px, chữ hoa, có khoảng cách chữ).
  * **Body Text / Table Data:** `text-xs` (12px).
  * **Badges / Tags / Meta Info:** `text-[10px]` hoặc `text-xs font-semibold px-2.5 py-1 rounded`.

---

## 4. Quy chuẩn Bố cục & Layout (Layout Structure)

Ứng dụng bắt buộc phải tuân theo bố cục **Master-Sidebar & Multi-Column Dashboard**:

1. **Top Header (Thanh điều hướng trên cùng):** Chiều cao cố định (`h-16`). Chứa Logo nhận diện, Tên hệ thống (AegisGate), Đèn báo trạng thái MCP Server, và Công tắc chuyển đổi nhanh **Auto Approval Mode (ON/OFF)**.
2. **Left Sidebar (Thanh điều hướng bên trái):** Chiều rộng cố định (`w-64`). Chứa các mục điều hướng chính (`Live Execution Monitor`, `Pluggable Targets`, `Knowledge & Rules`, `Audit Logs`) và danh sách các Plugin đang kết nối ở chân sidebar.
3. **Main Content Area (Vùng hiển thị nội dung chính):** Chiếm toàn bộ không gian còn lại, được chia thành các Tab độc lập ẩn/hiện mượt mà qua state management.
4. **Grid System cho Monitor (3 Cột cân đối):**
   * *Cột 1:* AI Query & Reasoning (Hiển thị ý định của AI và câu lệnh thô).
   * *Cột 2:* Plugin Dry-Run & Explain Plan (Hiển thị kết quả kiểm tra Plan và đối chiếu Rules).
   * *Cột 3:* Gatekeeper & Interactive Controls (Bảng điều khiển trạng thái, nút Pause/Resume/Stop hoặc hiệu ứng đang chạy).

---

## 5. Quy chuẩn Tương tác & Trạng thái (Interactive & State Rules)

Mọi thành phần UI tương tác phải phản hồi trực quan theo State Machine của hệ thống:

* **Trạng thái Chờ (Idle / Waiting):** Hiển thị icon đồng hồ/thông báo nhẹ nhàng, màu sắc `slate-400`.
* **Trạng thái Đang xử lý (Executing / Loading):** Phải có hiệu ứng nhấp nháy (`animate-pulse`) hoặc xoay tròn (`animate-spin`), kết hợp màu `indigo-400`.
* **Trạng thái Chờ duyệt (Paused for Review):** Bắt buộc hiển thị cụm nút bấm hành động rõ ràng: Nút xanh (`Approve / Resume`) và Nút xám/đỏ (`Reject / Stop`).
* **Trạng thái Lỗi / Vi phạm (Rejected / Timeout):** Đổi màu nền card/badge sang tông đỏ dịu (`bg-red-500/10 border-red-500/20 text-red-400`) kèm icon cảnh báo.

---

## 6. Quy chuẩn Tích hợp Plugin có UI (Pluggable UI Contract)

Vì Plugin có thể được phát triển độc lập nhưng phải hiển thị trực quan trên giao diện chung của Core, mọi Plugin khi render trên UI phải tuân thủ cấu trúc **2 khối thông tin chuẩn (Two-Card Layout)**:

1. **Card Thông số Kỹ thuật (Configuration & Adapters):**
   * Hiển thị Driver / Engine đang sử dụng.
   * Hiển thị câu lệnh Dry-Run đặc thù (VD: `SET SHOWPLAN_XML ON` hoặc `.explain()`).
   * Hiển thị câu lệnh Abort khẩn cấp tương ứng.
   * Nút hành động trực tiếp (VD: *"Sync Schema & Indexes Now"*).
2. **Card Trạng thái Vận hành (Live Metrics & Pool):**
   * Hiển thị danh sách Session IDs / SPIDs đang hoạt động dưới DB.
   * Hiển thị độ trễ trung bình (Latency).
   * Đèn tín hiệu kết nối (`Connected / Active`).
3. **Modal Đăng ký Plugin mới (Add Plugin Modal):**
   * Core phải cung cấp sẵn Modal form chung với các trường chuẩn: *Key định danh, Tên hiển thị, Driver, Lệnh Dry-Run, Lệnh Abort*. Khi người dùng submit, giao diện phải tự động cập nhật danh sách tab và sidebar ngay lập tức mà không gây mất trạng thái ứng dụng.

---
