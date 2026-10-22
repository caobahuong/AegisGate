"use client";

import React, { useState } from "react";
import {
  BookOpen,
  X,
  Layers,
  Terminal,
  Shield,
  Activity,
  Boxes,
  FileText,
  Copy,
  Check,
  CheckCircle2,
  AlertTriangle,
  Database,
  Sparkles,
  Clock,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface UserGuideModalProps {
  isOpen: boolean;
  onClose: () => void;
}

type GuideSection =
  | "overview"
  | "mcp"
  | "plugins"
  | "rules"
  | "execution"
  | "audit";

export const UserGuideModal: React.FC<UserGuideModalProps> = ({ isOpen, onClose }) => {
  const [activeSection, setActiveSection] = useState<GuideSection>("overview");
  const [copiedSnippet, setCopiedSnippet] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleCopyCode = (code: string, id: string) => {
    if (typeof navigator !== "undefined" && navigator.clipboard) {
      navigator.clipboard.writeText(code);
    } else {
      const textarea = document.createElement("textarea");
      textarea.value = code;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      document.body.removeChild(textarea);
    }
    setCopiedSnippet(id);
    setTimeout(() => setCopiedSnippet(null), 2000);
  };

  const sections = [
    { id: "overview" as GuideSection, label: "1. Tổng quan & Kiến trúc", icon: Layers },
    { id: "mcp" as GuideSection, label: "2. Kết nối AI qua MCP", icon: Terminal },
    { id: "plugins" as GuideSection, label: "3. Quản lý Pluggable Targets", icon: Boxes },
    { id: "rules" as GuideSection, label: "4. Governance Rules & Scope", icon: Shield },
    { id: "execution" as GuideSection, label: "5. Live Monitor & Phê duyệt", icon: Activity },
    { id: "audit" as GuideSection, label: "6. Audit Logs Input / Output", icon: FileText },
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 animate-in fade-in duration-150">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-4xl w-full h-[88vh] shadow-2xl flex flex-col overflow-hidden">
        
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-950/60 flex-shrink-0">
          <div className="flex items-center space-x-3">
            <div className="h-9 w-9 rounded-xl bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center">
              <BookOpen className="h-5 w-5 text-indigo-400" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-slate-100 flex items-center space-x-2">
                <span>Hướng dẫn Sử dụng Hệ thống AegisGate</span>
                <span className="text-[10px] px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 font-mono">
                  v2.0 Enterprise
                </span>
              </h2>
              <p className="text-xs text-slate-400">
                Tài liệu vận hành cổng kiểm soát an toàn cơ sở dữ liệu cho AI Agents (Claude, Cursor, Cline).
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            data-testid="close-user-guide-btn"
            title="Đóng"
            className="text-slate-400 hover:text-slate-200 p-1.5 rounded-lg hover:bg-slate-800 transition-colors"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Modal Body: Left Navigation & Right Content */}
        <div className="flex flex-1 overflow-hidden">
          
          {/* Left Navigation Sidebar */}
          <div className="w-64 border-r border-slate-800 p-4 space-y-1.5 bg-slate-950/40 flex-shrink-0 overflow-y-auto">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 block px-2.5 pb-1">
              Chủ đề Hướng dẫn
            </span>
            {sections.map((sec) => {
              const Icon = sec.icon;
              const isActive = activeSection === sec.id;
              return (
                <button
                  key={sec.id}
                  onClick={() => setActiveSection(sec.id)}
                  className={cn(
                    "w-full flex items-center space-x-2.5 px-3 py-2.5 rounded-lg text-xs font-medium transition-all text-left",
                    isActive
                      ? "bg-indigo-600/20 text-indigo-300 border border-indigo-500/30 font-semibold shadow-sm"
                      : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/40"
                  )}
                >
                  <Icon className={cn("h-4 w-4 flex-shrink-0", isActive ? "text-indigo-400" : "text-slate-500")} />
                  <span className="truncate">{sec.label}</span>
                </button>
              );
            })}

            <div className="pt-4 border-t border-slate-800/80 mt-4 space-y-2">
              <div className="p-3 rounded-lg bg-indigo-600/10 border border-indigo-500/20 space-y-1">
                <span className="text-[10px] font-bold text-indigo-400 flex items-center space-x-1">
                  <Sparkles className="h-3 w-3" />
                  <span>Trạng thái Gateway</span>
                </span>
                <p className="text-[11px] text-slate-300 leading-snug">
                  Cổng MCP Server đang hoạt động tại cổng <code className="text-indigo-300 font-mono">8000</code>.
                </p>
              </div>
            </div>
          </div>

          {/* Right Content Area */}
          <div className="flex-1 p-6 overflow-y-auto space-y-6 text-xs text-slate-300 leading-relaxed">
            
            {/* 1. OVERVIEW */}
            {activeSection === "overview" && (
              <div className="space-y-4 animate-in fade-in duration-150">
                <div>
                  <h3 className="text-sm font-bold text-slate-100 flex items-center space-x-2">
                    <Layers className="h-4 w-4 text-indigo-400" />
                    <span>1. Tổng quan Kiến trúc Zero-Trust Database Gateway</span>
                  </h3>
                  <p className="text-slate-400 mt-1">
                    AegisGate là lớp phòng thủ trung gian giữa AI Agents (Claude Code, Cursor, Cline) và các Database Production (SQL Server, MongoDB, PostgreSQL).
                  </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 space-y-1.5">
                    <div className="flex items-center space-x-1.5 text-indigo-400 font-bold text-xs">
                      <Database className="h-3.5 w-3.5" />
                      <span>Port 1: Structural Cache</span>
                    </div>
                    <p className="text-[11px] text-slate-400">
                      AI Agent đọc cấu trúc bảng, cột, khóa chính và tài liệu nghiệp vụ từ bộ đệm AegisGate mà <strong>không chạm trực tiếp vào DB</strong>.
                    </p>
                  </div>

                  <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 space-y-1.5">
                    <div className="flex items-center space-x-1.5 text-amber-400 font-bold text-xs">
                      <Shield className="h-3.5 w-3.5" />
                      <span>Port 2: Dry-Run Inspection</span>
                    </div>
                    <p className="text-[11px] text-slate-400">
                      Trước khi thực thi, câu lệnh được phân tích Showplan XML, tính toán chi phí và đối soát chính sách bảo mật (Governance Rules).
                    </p>
                  </div>

                  <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 space-y-1.5">
                    <div className="flex items-center space-x-1.5 text-emerald-400 font-bold text-xs">
                      <Activity className="h-3.5 w-3.5" />
                      <span>Port 3: Guarded Execution</span>
                    </div>
                    <p className="text-[11px] text-slate-400">
                      Chạy truy vấn dưới cơ chế giám sát timeout nghiêm ngặt, theo dõi SPID tiến trình và hỗ trợ nút dừng khẩn cấp (Emergency Kill).
                    </p>
                  </div>
                </div>

                <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 space-y-2">
                  <h4 className="font-bold text-slate-200">Luồng vòng đời của một câu truy vấn (Lifecycle)</h4>
                  <ol className="list-decimal list-inside space-y-1.5 text-[11px] text-slate-300">
                    <li><strong className="text-indigo-400">AI Submission:</strong> AI gửi câu truy vấn kèm mục đích (Reasoning) qua MCP hoặc REST API.</li>
                    <li><strong className="text-amber-400">Dry-Run & Rule Check:</strong> Gateway kiểm tra vi phạm (Full Table Scan, cấm Join bảng nhạy cảm). Nếu vi phạm -&gt; <strong>REJECTED</strong> ngay lập tức.</li>
                    <li><strong className="text-indigo-400">Human Approval / Auto:</strong> Nếu bật Auto Mode -&gt; Tự động chạy. Nếu tắt -&gt; Tạm dừng ở trạng thái <strong>PAUSED_FOR_REVIEW</strong> chờ con người phê duyệt.</li>
                    <li><strong className="text-emerald-400">Guarded Run:</strong> Thực thi an toàn dưới Timeout Guard và lưu nhật ký kiểm toán (Audit Log) chi tiết Input/Output.</li>
                  </ol>
                </div>
              </div>
            )}

            {/* 2. MCP CONNECTION */}
            {activeSection === "mcp" && (
              <div className="space-y-4 animate-in fade-in duration-150">
                <div>
                  <h3 className="text-sm font-bold text-slate-100 flex items-center space-x-2">
                    <Terminal className="h-4 w-4 text-indigo-400" />
                    <span>2. Hướng dẫn Kết nối AI Clients qua giao thức MCP</span>
                  </h3>
                  <p className="text-slate-400 mt-1">
                    Cung cấp chuẩn giao tiếp Model Context Protocol (MCP) dạng Stdio transport cho Claude Desktop, Cursor và Cline.
                  </p>
                </div>

                <div className="space-y-3">
                  <h4 className="font-bold text-slate-200">Cách lấy cấu hình kết nối:</h4>
                  <p className="text-slate-400">
                    Bấm vào nút <strong>&quot;MCP Config&quot;</strong> trên thanh Header (kết nối toàn cục) hoặc nút terminal trên từng thẻ Plugin (kết nối riêng cho database đó).
                  </p>

                  <div className="space-y-1.5">
                    <div className="flex justify-between items-center">
                      <span className="text-[11px] font-mono text-slate-400">Cấu hình mẫu cho Cursor (.cursor/mcp.json) hoặc Claude Desktop:</span>
                      <button
                        onClick={() => handleCopyCode(JSON.stringify({
                          mcpServers: {
                            "aegisgate": {
                              command: "python",
                              args: ["-m", "core.gateway.mcp_server"],
                              env: { AEGISGATE_API_URL: "http://localhost:8000" }
                            },
                            "aegisgate-sqlserver_prod": {
                              command: "python",
                              args: ["-m", "core.gateway.mcp_server", "--plugin", "sqlserver_prod"],
                              env: { AEGISGATE_API_URL: "http://localhost:8000" }
                            }
                          }
                        }, null, 2), "mcp_json")}
                        className="flex items-center space-x-1 bg-slate-800 hover:bg-slate-700 text-slate-200 px-2 py-0.5 rounded text-[10px] transition-colors"
                      >
                        {copiedSnippet === "mcp_json" ? <Check className="h-3 w-3 text-emerald-400" /> : <Copy className="h-3 w-3" />}
                        <span>{copiedSnippet === "mcp_json" ? "Đã chép!" : "Copy Snippet"}</span>
                      </button>
                    </div>

                    <pre className="p-3 bg-slate-950 border border-slate-800 rounded-xl font-mono text-[11px] text-slate-300 overflow-x-auto">
{`{
  "mcpServers": {
    "aegisgate": {
      "command": "python",
      "args": ["-m", "core.gateway.mcp_server"],
      "env": { "AEGISGATE_API_URL": "http://localhost:8000" }
    },
    "aegisgate-sqlserver_prod": {
      "command": "python",
      "args": ["-m", "core.gateway.mcp_server", "--plugin", "sqlserver_prod"],
      "env": { "AEGISGATE_API_URL": "http://localhost:8000" }
    }
  }
}`}
                    </pre>
                  </div>
                </div>

                <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 space-y-2">
                  <h4 className="font-bold text-slate-200">4 MCP Tools AI Agent có thể sử dụng:</h4>
                  <ul className="space-y-1.5 text-[11px]">
                    <li><code className="text-indigo-400 font-bold font-mono">get_catalog(target_id?, partition_key?)</code>: Xem danh sách bảng, cột, khóa chính và index từ cache.</li>
                    <li><code className="text-indigo-400 font-bold font-mono">get_knowledge(target_id?, partition_key?)</code>: Đọc doc nghiệp vụ (doc.md), query skills và danh sách rules.</li>
                    <li><code className="text-indigo-400 font-bold font-mono">submit_execution(query, target_id?, reasoning?)</code>: Gửi câu lệnh SQL qua quy trình Dry-Run &amp; thực thi có bảo vệ.</li>
                    <li><code className="text-indigo-400 font-bold font-mono">check_execution_status(execution_id)</code>: Kiểm tra trạng thái duyệt và lấy kết quả dữ liệu trả về.</li>
                  </ul>
                </div>
              </div>
            )}

            {/* 3. PLUGINS */}
            {activeSection === "plugins" && (
              <div className="space-y-4 animate-in fade-in duration-150">
                <div>
                  <h3 className="text-sm font-bold text-slate-100 flex items-center space-x-2">
                    <Boxes className="h-4 w-4 text-indigo-400" />
                    <span>3. Quản lý Pluggable Targets (Database Connectors)</span>
                  </h3>
                  <p className="text-slate-400 mt-1">
                    Mỗi database là một tiến trình con (Subprocess Stdio) độc lập, tự định nghĩa giao diện (Dynamic UI Schema) và card theo dõi chuyên biệt.
                  </p>
                </div>

                <div className="space-y-2">
                  <h4 className="font-bold text-slate-200">Tính năng trên Tab Pluggable Targets:</h4>
                  <ul className="space-y-2 text-[11px]">
                    <li className="p-2.5 rounded-lg bg-slate-950 border border-slate-800">
                      <strong className="text-indigo-400 block mb-0.5">Chỉnh sửa thông số (Edit Configuration):</strong>
                      Bấm nút <strong>&quot;Edit Configuration&quot;</strong> trên từng thẻ plugin để sửa Server, Port, Database Name, Username, Password. Khi lưu, Gateway tự động gửi tín hiệu tái khởi tạo kết nối (<code className="text-indigo-300 font-mono">re-init</code>) xuống adapter.
                    </li>
                    <li className="p-2.5 rounded-lg bg-slate-950 border border-slate-800">
                      <strong className="text-indigo-400 block mb-0.5">Đồng bộ Catalog (Sync Schema &amp; Indexes Now):</strong>
                      Bấm để quét lại cấu trúc bảng và index thực tế từ database đích và cập nhật vào bộ nhớ đệm cache của AI.
                    </li>
                    <li className="p-2.5 rounded-lg bg-slate-950 border border-slate-800">
                      <strong className="text-red-400 block mb-0.5">Gỡ bỏ Plugin (Uninstall):</strong>
                      Bấm nút icon thùng rác màu đỏ để vô hiệu hóa tạm thời (Soft Deactivate) hoặc xóa vĩnh viễn (Hard Delete) khỏi database.
                    </li>
                  </ul>
                </div>
              </div>
            )}

            {/* 4. RULES & SCOPING */}
            {activeSection === "rules" && (
              <div className="space-y-4 animate-in fade-in duration-150">
                <div>
                  <h3 className="text-sm font-bold text-slate-100 flex items-center space-x-2">
                    <Shield className="h-4 w-4 text-indigo-400" />
                    <span>4. Quản trị Governance Rules &amp; Phân vùng Phạm vi (Scoping)</span>
                  </h3>
                  <p className="text-slate-400 mt-1">
                    Thiết lập các rào chắn kiểm soát query tự động để ngăn ngừa tai nạn dữ liệu do AI gây ra.
                  </p>
                </div>

                <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
                  <h4 className="font-bold text-slate-200">Tạo mới và Chỉnh sửa Rule (Create &amp; Edit Rule):</h4>
                  <p className="text-slate-400 text-[11px]">
                    Tại tab <strong>&quot;Governance Rules&quot;</strong>, bấm <strong>&quot;Create Rule&quot;</strong> để thêm mới, hoặc bấm icon cây bút <strong>&quot;Edit&quot;</strong> trên từng rule để cập nhật:
                  </p>
                  <ul className="list-disc list-inside space-y-1 text-[11px] pl-2 text-slate-300">
                    <li><strong className="text-indigo-400">Target Scope:</strong> Chọn <code className="text-indigo-300 font-mono">Global Scope</code> để áp dụng cho tất cả cơ sở dữ liệu, hoặc chọn đích danh một plugin (VD: <code className="text-emerald-300 font-mono">sqlserver_prod</code>).</li>
                    <li><strong className="text-indigo-400">Rule Type:</strong>
                      <ul className="list-circle list-inside pl-4 pt-1 space-y-1">
                        <li><code className="text-indigo-300 font-mono">FORBID_JOIN</code>: Cấm join các bảng nhạy cảm (VD: <code className="text-slate-200">Orders,AuditLogs</code>).</li>
                        <li><code className="text-indigo-300 font-mono">FORBID_TABLE_SCAN</code>: Chặn các truy vấn thiếu mệnh đề WHERE gây quét toàn bộ bảng.</li>
                        <li><code className="text-indigo-300 font-mono">MAX_EXECUTION_TIME</code>: Giới hạn số giây tối đa được phép thực thi (VD: 15 giây).</li>
                        <li><code className="text-indigo-300 font-mono">CUSTOM</code>: Biểu thức regex tùy biến theo yêu cầu nghiệp vụ.</li>
                      </ul>
                    </li>
                  </ul>
                </div>

                <div className="p-3 rounded-lg bg-indigo-600/10 border border-indigo-500/20 text-[11px] space-y-1">
                  <span className="font-bold text-indigo-400 block">Bộ lọc Target Scope:</span>
                  <p className="text-slate-300">
                    Dropdown chọn Target ở góc trên tab Knowledge &amp; Rules cho phép lọc tức thì giữa <em>All Pluggable Targets</em>, <em>Global Scope Only</em>, hoặc xem riêng rules của từng Plugin.
                  </p>
                </div>
              </div>
            )}

            {/* 5. EXECUTION & AUTO MODE */}
            {activeSection === "execution" && (
              <div className="space-y-4 animate-in fade-in duration-150">
                <div>
                  <h3 className="text-sm font-bold text-slate-100 flex items-center space-x-2">
                    <Activity className="h-4 w-4 text-indigo-400" />
                    <span>5. Live Execution Monitor &amp; Cơ chế Phê duyệt (Gatekeeper)</span>
                  </h3>
                  <p className="text-slate-400 mt-1">
                    Quan sát luồng thực thi theo thời gian thực qua Server-Sent Events (SSE).
                  </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 space-y-1.5">
                    <div className="flex items-center space-x-1.5 text-amber-400 font-bold text-xs">
                      <Clock className="h-3.5 w-3.5" />
                      <span>Manual Review Mode (Mặc định)</span>
                    </div>
                    <p className="text-[11px] text-slate-400">
                      Khi công tắc trên Header để <strong className="text-slate-200">OFF</strong>: Sau khi Dry-Run thành công, câu lệnh tạm dừng ở trạng thái <code className="text-amber-400 font-mono">PAUSED_FOR_REVIEW</code>. Người dùng bấm <strong>&quot;Approve &amp; Run&quot;</strong> để thực thi hoặc <strong>&quot;Reject&quot;</strong> để hủy.
                    </p>
                  </div>

                  <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 space-y-1.5">
                    <div className="flex items-center space-x-1.5 text-emerald-400 font-bold text-xs">
                      <CheckCircle2 className="h-3.5 w-3.5" />
                      <span>Auto Approval Mode (Tự động)</span>
                    </div>
                    <p className="text-[11px] text-slate-400">
                      Bật công tắc trên Header sang <strong className="text-emerald-400">ON</strong>: Bất kỳ truy vấn an toàn nào (0 vi phạm policy) sẽ được Gateway tự động cấp phép và chạy ngay lập tức, trả kết quả về cho AI trong vài chục mili-giây.
                    </p>
                  </div>
                </div>

                <div className="p-3.5 rounded-xl bg-red-500/10 border border-red-500/20 text-red-300 text-[11px] space-y-1">
                  <div className="flex items-center space-x-1.5 font-bold text-red-400">
                    <AlertTriangle className="h-4 w-4" />
                    <span>Nút ngắt khẩn cấp (Emergency Kill SPID):</span>
                  </div>
                  <p>
                    Nếu một câu truy vấn có dấu hiệu treo hoặc tiêu tốn tài nguyên quá ngưỡng, nút <strong>&quot;Stop &amp; KILL Session Now&quot;</strong> sẽ gửi lệnh hủy tiến trình database ngay lập tức để bảo toàn server.
                  </p>
                </div>
              </div>
            )}

            {/* 6. AUDIT LOGS */}
            {activeSection === "audit" && (
              <div className="space-y-4 animate-in fade-in duration-150">
                <div>
                  <h3 className="text-sm font-bold text-slate-100 flex items-center space-x-2">
                    <FileText className="h-4 w-4 text-indigo-400" />
                    <span>6. Sổ cái Kiểm toán (Audit Logs) &amp; Chi tiết Input / Output</span>
                  </h3>
                  <p className="text-slate-400 mt-1">
                    Ghi lại toàn diện lịch sử truy vấn, phân định rõ ràng đầu vào (Input) và đầu ra (Output).
                  </p>
                </div>

                <div className="space-y-2">
                  <h4 className="font-bold text-slate-200">Hai phần thông tin trong Audit Inspector:</h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-[11px]">
                    <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 space-y-1">
                      <strong className="text-indigo-400 block font-bold text-xs">📥 Thông tin Input:</strong>
                      <p className="text-slate-400">• Câu lệnh SQL / Command đầy đủ.</p>
                      <p className="text-slate-400">• AI Intent &amp; Reasoning (Lý do AI chạy query).</p>
                      <p className="text-slate-400">• Target Database &amp; Loại câu lệnh (READ/WRITE).</p>
                    </div>

                    <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 space-y-1">
                      <strong className="text-emerald-400 block font-bold text-xs">📤 Thông tin Output:</strong>
                      <p className="text-slate-400">• Bảng dữ liệu tương tác (Interactive Data Table).</p>
                      <p className="text-slate-400">• Số dòng kết quả trả về (Rows Returned/Affected).</p>
                      <p className="text-slate-400">• Thời gian phản hồi thực tế (Latency tính bằng ms).</p>
                      <p className="text-slate-400">• Xem JSON thô và copy kết quả dễ dàng.</p>
                    </div>
                  </div>
                </div>
              </div>
            )}

          </div>
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3.5 border-t border-slate-800 bg-slate-950/80 flex justify-between items-center flex-shrink-0">
          <span className="text-[11px] text-slate-500">
            AegisGate Protection Protocol • Pair Programming Assistant
          </span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold transition-colors shadow-md shadow-indigo-600/30"
          >
            Đã hiểu, đóng tài liệu
          </button>
        </div>

      </div>
    </div>
  );
};
