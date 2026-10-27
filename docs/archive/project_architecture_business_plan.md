> [!NOTE]
> **Historical planning document** - see [docs/architecture.md](../architecture.md) for the active system architecture.

---

# KẾ HOẠCH TỔNG THỂ & ĐẶC TẢ NGHIỆP VỤ DỰ ÁN AEGISGATE (`plan.md`)

**Tên định danh dự án:** AegisGate
**Bản chất hệ thống:** Nền tảng Proxy và bộ khung điều phối (AI Execution Proxy & Pluggable Harness Platform) đứng giữa **AI Agent** và **Bất kỳ Hệ thống Bên thứ 3 nào**.
**Phạm vi tài liệu:** Tài liệu này định nghĩa bài toán, triết lý thiết kế lõi, phân ranh giới trách nhiệm giữa Nền tảng (AegisGate Core) và các Mô-đun mở rộng (Plugins), cùng các luồng nghiệp vụ vận hành. *(Các quyết định về công nghệ, ngôn ngữ lập trình và thiết kế cơ sở dữ liệu chi tiết sẽ được quy định ở một tài liệu Kỹ thuật riêng).*

---

## 1. Bối cảnh & Bài toán (Problem Statement)

Trong thực tế, nhu cầu cho phép AI kết nối trực tiếp vào các hệ thống bên thứ 3 (như hệ quản trị cơ sở dữ liệu SQL, NoSQL, các hệ thống lưu trữ hoặc dịch vụ nội bộ) đang rất lớn. Tuy nhiên, nếu để AI kết nối trực tiếp hoặc qua các công cụ kết nối đơn giản hiện tại sẽ gặp 4 rào cản lớn:

1. **Nguy cơ từ việc giao quyền trực tiếp:** Việc đưa thẳng thông tin đăng nhập (Username, Password, Connection String) cho AI hoặc cấu hình trực tiếp vào môi trường của AI là quá rủi ro.
2. **Mất kiểm soát hành vi và giới hạn thực thi:** Không có cơ chế kiểm soát việc AI được phép truy vấn như thế nào, cấm kết hợp (JOIN) những nguồn dữ liệu nào với nhau vì quá nặng, hay giới hạn thời gian chạy tối đa (ví dụ: lệnh đọc chỉ được chạy tối đa 15 giây, lệnh cập nhật tối đa 30 giây, quá giờ phải tự động ngắt/kill ngay lập tức).
3. **Lãng phí và thiếu chính xác khi AI tự mò mẫm cấu trúc:** Mỗi lần làm việc, AI lại phải tự truy vấn vào hệ thống bên thứ 3 để tìm hiểu xem có những bảng nào, trường nào, đánh chỉ mục (index) ra sao. Việc này vừa gây tải thừa cho hệ thống đích, vừa khiến AI dễ "đoán mò" sai nghiệp vụ nếu thiếu tài liệu hướng dẫn đi kèm.
4. **Mù thông tin và thiếu quyền can thiệp tức thời (Lack of Observability & Control):** Người dùng không biết AI sắp thực thi kế hoạch (Plan) gì để duyệt trước, không thể tạm dừng (Pause), cho chạy tiếp (Resume) hay dừng khẩn cấp (Stop) khi phát hiện bất thường, và không có nơi lưu trữ lịch sử tập trung xem mỗi lần gọi AI đã làm gì, mất bao lâu, kết quả trả ra sao.

---

## 2. Triết lý Thiết kế Cốt lõi (Core Design Philosophy)

Điểm đặc biệt nhất và là giá trị cốt lõi của sản phẩm này nằm ở kiến trúc **Tách biệt Hoàn toàn (Total Decoupling)**:

### 2.1. Tool Proxy đứng giữa: "Không thiết kế để xử lý bất kỳ bên thứ 3 cụ thể nào"
* **Bản chất của Tool Proxy (Core Platform):** Bản thân Tool Proxy hoàn toàn "mù" (agnostic) về bên thứ 3. Trong lõi của Tool **không hề tồn tại** khái niệm SQL Server, MongoDB, bảng (table), cột (column) hay câu lệnh SQL.
* **Vai trò của Tool Proxy:** Nó chỉ đóng vai trò là **Nền tảng Giao tiếp, Lưu trữ và Điều phối (Platform & Harness)**:
  * Mở cổng giao tiếp chuẩn cho mọi loại AI (qua API, MCP...).
  * Cung cấp nơi lưu trữ tập trung cho các tri thức của hệ thống: `Rule` (Luật lệ), `Skill` (Kỹ năng), `doc.md` (Tài liệu hướng dẫn cho AI), và `Kho dữ liệu cấu trúc` (đóng vai trò như bộ nhớ đệm bền vững về cấu trúc của bên thứ 3 để AI tra cứu mà không cần chạm vào hệ thống thật).
  * Cung cấp cơ chế điều khiển luồng chạy (Auto Mode, Pause, Resume, Stop) và giao diện hiển thị kế hoạch thực thi (Explain Plan / Dry-Run) cho con người giám sát.
  * Cung cấp hệ thống quản lý và tra cứu lịch sử (Log Management).
  * **Cung cấp các "Đầu nhận chuẩn" (Standard Ingest/Output Sinks):** Định nghĩa sẵn quy chuẩn đầu vào để bất kỳ Plugin nào cũng có thể đẩy dữ liệu cấu trúc và đẩy Log/Plan về cho Tool lưu trữ và hiển thị.

### 2.2. Hệ thống Plugin độc lập: "Đóng gói riêng biệt để nhúng (Embed/Plug) vào Tool"
* **Bản chất của Plugin:** Mỗi bên thứ 3 (như SQL Server, PostgreSQL, MongoDB, Elasticsearch...) sẽ là một Plugin hoàn toàn riêng biệt được viết và nhúng (add) vào nền tảng Tool Proxy.
* **Vai trò của Plugin:** Mọi nghiệp vụ đặc thù, nặng nề và sát với bên thứ 3 nhất đều nằm gọn bên trong Plugin đó:
  * Tự quản lý kết nối (Connection), quản lý vùng nhớ kết nối (Pool), quản lý phiên giao dịch (Transaction).
  * Tự thực thi các luật đặc thù của nền tảng đích: Kiểm tra câu lệnh trước khi chạy (Dry-Run / Explain Plan), kiểm tra việc kết hợp dữ liệu bị cấm (như cấm JOIN bảng A với bảng B), ép thời gian chạy tối đa (ví dụ: quá 15 giây tự động gửi lệnh Kill xuống hệ thống đích).
  * Trích xuất cấu trúc của bên thứ 3, tự chia nhỏ (nếu dữ liệu lớn) và đẩy ra **Đầu nhận Kho dữ liệu** của Tool Proxy.
  * Thu thập kết quả, thời gian thực thi, kế hoạch chạy (Plan) và đẩy ra **Đầu nhận Log** của Tool Proxy theo đúng chuẩn mà Tool quy định.

---

## 3. Sơ đồ Tư duy Kiến trúc (Conceptual Architecture)

```text
+-----------------------------------------------------------------------------------+
|                                  TẦNG AI AGENTS                                   |
|                    (Kết nối vào Tool qua API, MCP, SDK...)                        |
+-----------------------------------------+-----------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                AEGISGATE - TOOL PROXY PLATFORM (NỀN TẢNG ĐỨNG GIỮA)               |
|           *Tuyệt đối không chứa logic của bất kỳ bên thứ 3 cụ thể nào*            |
|                                                                                   |
|  +---------------------------+   +---------------------------------------------+  |
|  |  Kho Lưu Trữ Tri Thức AI  |   |     Bộ Điều Phối Thực Thi (Harness UI)      |  |
|  | - Lưu trữ doc.md, Skills  |   | - Chế độ chạy: Auto Mode / Manual Mode      |  |
|  | - Lưu trữ Rules chung     |   | - Điều khiển: Pause / Resume / Stop         |  |
|  | - Lưu Kho cấu trúc (Cache |   | - Màn hình xem trước Kế hoạch (Plan Viewer) |  |
|  |   bền vững của bên thứ 3) |   | - Quản lý, tra cứu và giám sát Log tập trung|  |
|  +-------------+-------------+   +----------------------+----------------------+  |
|                ^                                        ^                         |
|                | (Đẩy cấu trúc đã chia nhỏ)             | (Đẩy Plan, Output, Log) |
|  ==============+========================================+=======================  |
|  |        CÁC ĐẦU NHẬN & GIAO ƯỚC CHUẨN CỦA TOOL (STANDARD PORTS/SINKS)        |  |
+--+-----------------------------------------------------------------------------+--+
   ^                                      ^                                      ^
   | (Nhúng Plugin 1)                     | (Nhúng Plugin 2)                     | (Nhúng Plugin N)
   v                                      v                                      v
+-----------------------+              +-----------------------+              +-----------------------+
|   PLUGIN: SQL SERVER  |              |    PLUGIN: MONGODB    |              |    PLUGIN: BÊN THỨ 3  |
|  (Độc lập hoàn toàn)  |              |  (Độc lập hoàn toàn)  |              |  (Độc lập hoàn toàn)  |
| - Giữ User/Pass, Pool |              | - Giữ User/Pass, Pool |              | - Giữ cơ chế kết nối  |
| - Quét Bảng, Index    |              | - Quét Collection     |              | - Tự quét cấu trúc    |
| - Chạy Explain Plan   |              | - Chạy Explain        |              | - Tự kiểm tra Dry-Run |
| - Chặn JOIN cấm       |              | - Áp dụng Rule riêng  |              | - Tự xử lý Timeout &  |
| - Timeout 15s -> Kill |              | - Timeout -> KillOp   |              |   ngắt lệnh khẩn cấp  |
+-----------+-----------+              +-----------+-----------+              +-----------+-----------+
            |                                      |                                      |
            v                                      v                                      v
   (Hệ thống SQL Server)                  (Hệ thống MongoDB)                    (Hệ thống Đích khác)
```

---

## 4. Phân định Trách nhiệm Chi tiết: AegisGate Core vs. Plugin

Để đảm bảo nguyên tắc **"AegisGate không xử lý bên thứ 3, mọi việc đặc thù do Plugin tự lo nhưng phải tuân thủ đầu nhận của AegisGate"**, trách nhiệm của hai bên được tách bạch như sau:

| Khía cạnh | Trách nhiệm của AEGISGATE CORE (Nền tảng lõi) | Trách nhiệm của PLUGIN (Mô-đun nhúng vào) |
| :--- | :--- | :--- |
| **1. Kết nối & Bảo mật** | • Chỉ lưu danh sách các định danh kết nối (Connection Profiles) và biết kết nối đó thuộc về Plugin nào.<br>• Không trực tiếp mở kết nối tới bên thứ 3. | • Trực tiếp nắm giữ thông tin xác thực (User, Pass), khởi tạo và duy trì Connection Pool, quản lý Transaction với bên thứ 3. |
| **2. Kho cấu trúc & Tri thức (Knowledge Store)** | • Cung cấp **Đầu nhận Cấu trúc** để nhận dữ liệu từ Plugin đẩy lên và lưu trữ bền vững.<br>• Cho phép người dùng (hoặc Scheduler) bấm nút kích hoạt đồng bộ lại.<br>• Cung cấp nơi viết và gắn thêm `doc.md`, `skills`, `rules` vào từng phần dữ liệu.<br>• Phục vụ AI tra cứu thông tin này mà không cần gọi xuống Plugin hay bên thứ 3. | • Khi được yêu cầu đồng bộ, tự kết nối vào bên thứ 3 để quét thông tin (bảng, trường, kiểu dữ liệu, index...).<br>• Nếu dữ liệu quá lớn, tự chịu trách nhiệm **chia nhỏ (chunking/grouping)** theo chuẩn quy ước rồi đẩy vào Đầu nhận của Tool. |
| **3. Kiểm duyệt trước khi chạy (Dry-Run / Plan)** | • Truyền yêu cầu của AI cùng danh sách Rule xuống cho Plugin.<br>• Cung cấp **Đầu nhận Kế hoạch (Plan Sink)** để nhận kết quả phân tích từ Plugin, lưu lại và hiển thị trực quan lên màn hình cho người dùng xem. | • Tự dịch các Rule thành cơ chế kiểm tra tương ứng (ví dụ: chạy `EXPLAIN` / `SHOWPLAN` trên DB).<br>• Tự phát hiện vi phạm (như câu lệnh có kết hợp 2 bảng bị cấm JOIN với nhau, hoặc quét toàn bộ bảng nặng) dựa trên Plan và trả kết quả Đạt/Không Đạt kèm chi tiết Plan về cho Tool. |
| **4. Điều khiển Thực thi (Pause / Resume / Stop / Auto)** | • Quản lý trạng thái phiên chạy:<br>  - Nếu bật **Auto Mode**: Cho phép Plugin chạy tiếp ngay sau khi vượt qua bước kiểm tra Plan.<br>  - Nếu tắt Auto Mode: Tự động **Pause (Tạm dừng)** sau bước kiểm tra Plan để chờ người dùng bấm **Resume (Duyệt chạy)** hoặc **Stop (Từ chối)**.<br>• Khi đang chạy mà người dùng bấm **Stop**, phát tín hiệu hủy xuống Plugin. | • Thực thi câu lệnh thật khi được phép.<br>• Tự áp dụng giới hạn thời gian chạy theo từng loại lệnh (VD: lệnh đọc 15s, lệnh ghi 30s).<br>• Nếu quá số giây quy định hoặc nhận tín hiệu **Stop** từ Tool: Tự thực hiện thao tác **Kill/Cancel** tiến trình ngay dưới hệ thống bên thứ 3. |
| **5. Hệ thống Log & Giám sát** | • Cung cấp **Đầu nhận Log chuẩn (Log Sink)**.<br>• Lưu trữ toàn bộ lịch sử: AI gọi lúc nào, yêu cầu gì, Plan ra sao, chạy bao lâu, ai duyệt, kết quả thế nào để phục vụ tra cứu và kiểm toán. | • Đo đạc chính xác thời gian thực thi, trạng thái trả về, dữ liệu đầu ra (hoặc mã lỗi từ bên thứ 3) và đóng gói đẩy về Đầu nhận Log của Tool. |

---

## 5. Các Luồng Nghiệp vụ Vận hành (Operational Workflows)

### Luồng 1: Nhúng Plugin và Xây dựng Kho Tri thức (Onboarding & Cataloging Flow)
1. **Nhúng Plugin:** Người dùng thêm một Plugin (ví dụ: Plugin SQL Server hoặc Plugin MongoDB) vào Tool Proxy và cấu hình thông tin kết nối bên trong Plugin đó.
2. **Thu thập & Chia nhỏ Cấu trúc:**
   * Người dùng bấm nút cập nhật hoặc hệ thống lập lịch (Scheduler) tự động gọi lệnh đồng bộ của Plugin.
   * Plugin kết nối tới bên thứ 3, lấy toàn bộ thông tin cấu trúc (bảng, trường, chỉ mục/index, quan hệ...), tự phân loại và chia thành các phần nhỏ hợp lý, sau đó đẩy qua **Đầu nhận Cấu trúc** của Tool Proxy.
   * Tool Proxy lưu trữ bền vững toàn bộ thông tin này.
3. **Bổ sung Tri thức Nghiệp vụ (`doc.md`, `skill`, `rule`):**
   * Trên giao diện của Tool Proxy, người dùng bổ sung các tài liệu giải thích nghiệp vụ (`doc.md`), các kỹ năng/mẫu truy vấn chuẩn (`skill`), và thiết lập các quy tắc (`rule` như: cấm JOIN bảng A với bảng B, giới hạn Select 15s, Update 30s).

---

### Luồng 2: AI Tìm hiểu Hệ thống qua Kho lưu trữ của Tool (Zero-Touch Discovery Flow)
1. Khi AI nhận bài toán từ người dùng, thay vì kết nối vào bên thứ 3 để mò mẫm, AI hỏi trực tiếp **Tool Proxy** (qua MCP hoặc API).
2. Tool Proxy trích xuất thông tin từ Kho lưu trữ nội bộ:
   * Cung cấp cho AI danh sách các phân vùng dữ liệu đã được Plugin chia nhỏ.
   * Khi AI chọn đúng phần dữ liệu cần quan tâm, Tool trả về chi tiết trường nào, index nào đang có, kèm theo `doc.md`, `skill` và các `rule` giới hạn của phần đó.
3. Nhờ có đầy đủ thông tin cấu trúc và Index từ trước, AI tự viết ra câu truy vấn chính xác ngay từ lần đầu mà không làm phiền đến hệ thống bên thứ 3.

---

### Luồng 3: Kiểm duyệt Plan, Điều khiển (Pause/Resume/Stop) và Thực thi (Execution & Control Flow)

```text
[1. AI gửi yêu cầu thực thi tới Tool Proxy]
                    │
                    ▼
[2. Tool Proxy chuyển yêu cầu + Rules cho Plugin kiểm tra trước (Dry-Run)]
    • Plugin chạy cơ chế kiểm tra (VD: lấy Execution Plan) trên bên thứ 3.
    • Plugin kiểm tra các điều kiện cấm (VD: phát hiện có JOIN 2 bảng bị cấm).
    • Plugin xác định mức thời gian tối đa được phép chạy (VD: 15s hoặc 30s).
    • Plugin đẩy toàn bộ [Kết quả Kiểm tra + Plan] về Đầu nhận của Tool Proxy.
                    │
                    ├──► Nếu VI PHẠM RULE:
                    │    Tool Proxy chặn ngay lập tức, ghi Log và trả lý do lỗi
                    │    về cho AI để AI tự viết lại câu truy vấn khác.
                    │
                    └──► Nếu HỢP LỆ (Đạt mọi Rule):
                         Tool Proxy lưu và hiển thị Plan lên màn hình điều khiển.
                                    │
         ┌──────────────────────────┴──────────────────────────┐
         ▼ (Nếu đang bật AUTO MODE)                            ▼ (Nếu tắt AUTO MODE / Chế độ duyệt)
[Chuyển thẳng sang Bước 3]                          [Trạng thái: PAUSED (Tạm dừng chờ duyệt)]
                                                     Người dùng xem câu lệnh & Plan trên Tool:
                                                     • Bấm [RESUME]: Cho phép chạy tiếp sang Bước 3.
                                                     • Bấm [STOP]: Hủy bỏ, trả lời nhắn về cho AI.
                                                               │
         ┌─────────────────────────────────────────────────────┘
         ▼
[3. Plugin Thực thi thật (Executing) với Bộ đếm thời gian (VD: 15s / 30s)]
    • Trong lúc đang chạy:
      - Nếu vượt quá số giây quy định (Timeout 15s/30s) ──┐
      - Hoặc người dùng thấy bất thường và bấm nút [STOP] ─┼─► Plugin lập tức KILL / NGẮT
                                                           │   tiến trình dưới bên thứ 3.
    • Nếu chạy thành công trong thời gian cho phép:        │
      Plugin thu nhận kết quả trả về.                      │
                    │                                      │
                    ◄──────────────────────────────────────┘
                    ▼
[4. Đẩy Kết quả & Ghi nhận Log qua Đầu nhận của Tool Proxy]
    • Plugin đẩy toàn bộ: Thời gian chạy thực tế, trạng thái, kết quả (hoặc lỗi bị Kill)
      vào Đầu nhận Log của Tool Proxy.
    • Tool Proxy lưu lịch sử quản lý và trả kết quả cuối cùng về cho AI.
```

---

## 6. Chuẩn hóa "Đầu nhận" và "Giao ước" cho Plugin (Standard Plugin Contract)

Để bất kỳ lập trình viên nào (hoặc AI Agent) cũng có thể viết thêm Plugin mới (cho SQL Server, MongoDB, Redis, v.v.) nhúng vào nền tảng mà không cần sửa đổi Tool Proxy, mọi Plugin chỉ cần tuân thủ đúng **4 Cổng giao tiếp chuẩn**:

1. **Cổng Đồng bộ Cấu trúc (`Sync / Export Catalog`):**
   * **Nhiệm vụ của Plugin:** Tự kết nối vào bên thứ 3, lấy thông tin cấu trúc (bảng, trường, index...), tự phân mảnh/chia nhỏ và xuất ra định dạng chuẩn đẩy vào Đầu nhận Cấu trúc của Tool Proxy.
2. **Cổng Kiểm tra & Lập kế hoạch (`Pre-Check & Dry-Run Plan`):**
   * **Nhiệm vụ của Plugin:** Nhận yêu cầu của AI và bộ Rule từ Tool. Tự thực hiện kiểm tra (như lấy Explain Plan, kiểm tra cấm JOIN, phân loại lệnh để gán thời gian chạy 15s hay 30s) và đẩy báo cáo Plan về Đầu nhận Plan của Tool Proxy.
3. **Cổng Thực thi có Giám sát (`Execute with Constraints`):**
   * **Nhiệm vụ của Plugin:** Thực thi yêu cầu vào bên thứ 3 với giới hạn thời gian nghiêm ngặt. Nếu quá giờ, tự động kích hoạt cơ chế hủy/kill của bên thứ 3 đó. Đẩy kết quả và thông số chạy về Đầu nhận Log của Tool Proxy.
4. **Cổng Ngắt Khẩn cấp (`Abort / Kill`):**
   * **Nhiệm vụ của Plugin:** Khi nhận tín hiệu `Stop` từ người dùng trên Tool Proxy, ngay lập tức can thiệp vào bên thứ 3 để hủy bỏ câu lệnh đang chạy.

---

## 7. Định hướng Phát triển theo Giai đoạn (Project Milestones)

1. **Giai đoạn 1: Xây dựng Lõi AegisGate (Core Platform & Standard Sinks)**
   * Xây dựng khung hệ thống lõi hoàn toàn độc lập với bên thứ 3.
   * Thiết kế các **Đầu nhận chuẩn (Standard Sinks)** cho việc nhận Kho cấu trúc, nhận Explain Plan và nhận Log từ Plugin.
   * Xây dựng hệ thống quản lý `Rule`, `Skill`, `doc.md` và Kho dữ liệu cấu trúc.
   * Xây dựng bộ điều phối trạng thái hỗ trợ `Auto Mode`, `Pause`, `Resume`, `Stop`.
   * Mở cổng kết nối cho AI (qua API, MCP...).
2. **Giai đoạn 2: Xây dựng Giao diện Quản lý & Giám sát (Harness Control Center)**
   * Giao diện quản lý Kho cấu trúc, soạn thảo `doc.md`, `Skill`, `Rule` và nút kích hoạt đồng bộ lại dữ liệu từ Plugin.
   * Giao diện Giám sát Thực thi (Live Monitor): Hiển thị câu lệnh của AI, hiển thị Plan để duyệt, nút bật/tắt `Auto Mode`, các nút bấm `Pause / Resume / Stop` trực quan.
   * Giao diện Quản lý Log: Xem lại chi tiết từng lần AI gọi, thời gian chạy, Plan đã dùng và kết quả đầu ra.
3. **Giai đoạn 3: Phát triển Plugin Mẫu đầu tiên (Plugin SQL Server)**
   * Đóng gói riêng biệt một Plugin dành cho SQL Server nhúng vào Tool Proxy.
   * Xử lý quản lý kết nối, lấy danh sách Bảng/Trường/Index đẩy về Đầu nhận của Tool.
   * Xử lý việc lấy Execution Plan để phát hiện các bảng tham gia truy vấn (nhằm chặn các cặp bảng cấm JOIN với nhau) và đẩy Plan về cho Tool hiển thị.
   * Xử lý giới hạn thời gian chạy (Select 15s, Update 30s) và cơ chế tự động Kill phiên chạy quá giờ hoặc khi có lệnh Stop từ Tool.
4. **Giai đoạn 4: Mở rộng Hệ sinh thái Plugin (MongoDB, PostgreSQL...)**
   * Dựa trên khung giao ước có sẵn của Tool Proxy, phát triển tiếp các Plugin độc lập cho NoSQL (MongoDB) và các hệ thống bên thứ 3 khác mà không cần sửa đổi lại lõi của Tool Proxy.
