# AegisGate Frontend Dashboard

The **Frontend Dashboard** is an enterprise management, real-time monitoring, and gatekeeper control interface for AegisGate. Built with **Next.js 14 (App Router), TypeScript, Tailwind CSS, and Lucide React**, it strictly adheres to the UI rules defined in [`design.md`](../docs/ui_design_system_frontend_architecture_rulebook.md) and the coding standards in [`typescript_clean_code.md`](../docs/typescript_clean_code_skill.md).

---

## 🎨 Design System & Visual Identity

### 1. Dark-First Theme Palette

| Token                 | Tailwind Class                | Hex Value | Role                                                      |
| :-------------------- | :---------------------------- | :-------- | :-------------------------------------------------------- |
| **Main Background**   | `bg-slate-950`                | `#020617` | Global dark background                                    |
| **Component Surface** | `bg-slate-900`                | `#0f172a` | Cards, sidebar, header, and modal surfaces                |
| **Borders**           | `border-slate-800`            | `#1e293b` | Structural dividers and card borders                      |
| **Brand / Primary**   | `indigo-600` / `indigo-500`   | `#4f46e5` | Primary buttons, active indicators                        |
| **Success State**     | `emerald-500` / `emerald-400` | `#10b981` | `COMPLETED` state, `Auto Mode ON`, successful dry-run     |
| **Warning / Paused**  | `amber-500` / `amber-400`     | `#f59e0b` | `PAUSED_FOR_REVIEW`, `Auto Mode OFF`                      |
| **Danger / Rejected** | `red-500` / `red-400`         | `#ef4444` | `REJECTED`, `TIMEOUT`, Kill/Stop buttons, rule violations |

### 2. Typography

- **UI Text:** `Inter` for headers, labels, buttons, and body.
- **Monospace:** `JetBrains Mono` for all SQL queries, JSON payloads, execution plans, SPIDs, and Session IDs (`#exec_...`).

---

## 📐 Layout Architecture

```text
+-----------------------------------------------------------------------------------------+
| TOP HEADER (h-16): Logo | MCP Server Status Indicator | Auto Approval Mode Toggle Switch |
+-----------------------+-----------------------------------------------------------------+
| LEFT SIDEBAR (w-64)   | MAIN CONTENT AREA                                               |
|                       |                                                                 |
| • Live Monitor        | [Tab 1: Live Execution Monitor - 3-Column Balanced Grid]        |
| • Pluggable Targets   |   Col 1: AI Query & Reasoning (Input form + quick presets)     |
| • Knowledge & Rules   |   Col 2: Plugin Dry-Run & Explain Plan (Plan viewer + alerts)   |
| • Audit Logs          |   Col 3: Gatekeeper Controls (Status badge, Pause/Resume/Stop)  |
|                       |                                                                 |
|                       | [Tab 2: Pluggable Targets - Two-Card Layout per Target]         |
|                       |   Card 1: Configuration & Adapters (Driver, Dry-Run, Abort)     |
|                       |   Card 2: Live Metrics & Pool (SPIDs, latency, active status)   |
|                       |   + Modal: Add New Plugin with instant reactive update          |
|                       |                                                                 |
|                       | [Tab 3: Knowledge & Rules]                                      |
|                       |   • Schema Viewer (Partitions, tables, columns, indexes)        |
|                       |   • Markdown Editor (doc.md & skills.md with save button)       |
|                       |   • Governance Rules Editor (CRUD rules, severity badges)       |
|                       |                                                                 |
|                       | [Tab 4: Audit Logs]                                             |
| • Connected Targets   |   • Search & Status Filter Bar                                  |
|   (Live status footer)|   • Logs Table + Inspect Drawer Modal                           |
+-----------------------+-----------------------------------------------------------------+
```

---

## ⚡ Strict TypeScript Standards (`typescript_clean_code.md`)

- **Zero `any` Policy:** Every prop, state variable, and API payload is explicitly typed using interfaces defined in [`src/types/index.ts`](./src/types/index.ts).
- **Clean SSE Lifecycle:** Subscribes to `/api/monitor/events` via `EventSource`. The connection is strictly closed in the `useEffect` cleanup hook (`eventSource.close()`) to prevent browser memory leaks.
- **Immutability:** React state updates always use immutable operators (`[...prev]`, `.map()`, `.filter()`).

---

## 🚀 Getting Started

### 1. Install Dependencies

```bash
npm install
```

### 2. Run Development Server

```bash
npm run dev
```

Dashboard opens at [http://localhost:3000](http://localhost:3000).

### 3. Production Build & Start

```bash
npm run build
npm run start
```

---

## 🧪 Unit Testing

Frontend component tests are powered by **Vitest** and **React Testing Library**:

```bash
npm test
```

Tests verify Header toggle behaviors, Sidebar navigation, and Audit Log table search/filtering.
