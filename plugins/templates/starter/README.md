# AegisGate External Database Plugin Starter Template

Mẫu chuẩn để xây dựng Plugin cơ sở dữ liệu bên ngoài kết nối vào hệ thống **AegisGate Zero-Trust Gateway**.

---

## 📁 Cấu trúc Thư mục

```text
my_custom_plugin/
├── manifest.json              # Khai báo metadata, UI Schema, commands
├── adapter.py                 # Kế thừa BasePlugin, implement 4 hàm nghiệp vụ
├── requirements.txt           # Thư viện phụ thuộc (ví dụ psycopg2, redis, ...)
├── README.md                  # Hướng dẫn cấu hình & tham số kết nối
└── tests/
    └── test_adapter.py        # Unit test độc lập cho plugin
```

---

## 🚀 4 Bước Xây dựng Plugin Mới

### Bước 1: Khai báo `manifest.json`
Chỉnh sửa `manifest.json` với ID duy nhất, tên hiển thị, lệnh `dry_run_command`, `abort_command` và các trường UI form trong `ui_schema`.

### Bước 2: Kế thừa `BasePlugin` trong `adapter.py`
Chỉ cần thực hiện 4 phương thức:
1. `sync_knowledge(config)`: Trả về danh sách schema, bảng, cột, kiểu dữ liệu, index.
2. `dry_run(query, config)`: Trả về execution explain plan (SHOWPLAN/EXPLAIN) và điểm đánh giá rủi ro (`risk_score`).
3. `execute(query, config)`: Thực thi query và trả về kết quả `{"rows_affected": ..., "data": [...]}`.
4. `abort(spid, config)`: Tiêu diệt/hủy phiên làm việc trên cơ sở dữ liệu (`KILL {spid}`).

### Bước 3: Chạy thử nghiệm độc lập
```bash
python tests/test_adapter.py
```

### Bước 4: Đóng gói và Cài đặt vào AegisGate
1. Nén toàn bộ thư mục thành file `.zip`.
2. Truy cập AegisGate Dashboard -> tab **Pluggable Targets** -> bấm **Add Pluggable Target**.
3. Chuyển sang tab **Upload ZIP Package** và tải file `.zip` lên.
4. Hệ thống sẽ tự động tạo Virtualenv cô lập, cài đặt `requirements.txt`, chạy **Certification Linter (4 bước)** và kích hoạt ngay lập tức!

