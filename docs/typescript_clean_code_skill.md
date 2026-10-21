# SKILL: TypeScript Clean Code & Scalability Standards (`typescript_clean_code.md`)

**Phạm vi áp dụng:** Toàn bộ mã nguồn Frontend Dashboard (Next.js App Router, Components, State Management) viết bằng TypeScript.

## 1. Quy chuẩn Quản lý Kiểu dữ liệu (Strict Typing)
* **Zero `any` Policy:** Nghiêm cấm sử dụng kiểu dữ liệu `any`. Mọi props, state, API response payload đều phải được định nghĩa tường minh bằng `interface` hoặc `type` đặt tại thư mục `types/`.
* **Shared Contract Types:** Các kiểu dữ liệu đại diện cho Execution State, Rule, Plugin Manifest phải được đồng bộ hóa cấu trúc khớp tuyệt đối với Pydantic models ở phía Python Core.

## 2. Component Architecture & Modularization
* **Single Responsibility Components:** Tách biệt rõ ràng giữa *Container/Smart Components* (chứa logic fetch data, SSE event listeners) và *Presentational/Dumb Components* (chỉ nhận props và render UI, ví dụ: bảng Explain Plan, Status Badge).
* **shadcn/ui & Tailwind Consistency:** Sử dụng các thành phần từ `shadcn/ui` và tuân thủ nghiêm ngặt bộ token màu sắc đã định nghĩa trong `design.md` (`bg-slate-950`, `border-slate-800`, `indigo-600`). Không viết inline CSS thô.

## 3. Real-time & State Management Discipline
* **Clean SSE/WebSocket Lifecycle:** Khi sử dụng Server-Sent Events (SSE) để lắng nghe trạng thái thực thi lệnh của AI từ FastAPI, phải luôn đóng kết nối (`eventSource.close()`) trong hàm clean-up của `useEffect` để tránh rò rỉ bộ nhớ (memory leaks).
* **Immutability:** Cập nhật React State theo nguyên tắc bất biến (Immutability), không bao giờ mutate trực tiếp các mảng/object chứa danh sách execution logs hoặc active plugins.