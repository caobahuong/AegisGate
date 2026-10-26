# AegisGate Frontend Architecture & Component Guidelines

## Overview
AegisGate's web dashboard is built on **Next.js 14 (App Router)**, **React 18**, **Tailwind CSS**, and **TypeScript**. It serves as an intuitive governance operations center for AI agent execution workflows, runtime inspection, policy configuration, and multi-target database connectivity.

Following Phase 3 modularization, the frontend enforces a strict **feature-sliced architecture**, strict file size caps (< 250 lines), zero `alert()` usage, comprehensive WCAG AA accessibility compliance, and visual regression testing across both Light and Dark modes.

---

## 1. Directory & Feature Structure

```
frontend/src/
├── app/
│   ├── layout.tsx             # Root layout with pre-hydration dark mode boot script
│   ├── page.tsx               # Root composition page (<150 lines hard rule)
│   └── globals.css            # Tailwind directives, CSS variables & Light Mode overrides
├── features/                  # Domain-specific feature modules
│   ├── monitor/               # Real-time state machine & query simulator
│   │   ├── components/        # Subcomponents (<250 lines each)
│   │   ├── hooks/             # Feature hooks (useExecutions)
│   │   └── index.ts           # Public feature exports
│   ├── plugins/               # Pluggable target connector management
│   │   ├── components/        # Cards, modals (Add, Edit, Uninstall, Certify)
│   │   ├── hooks/             # Feature hooks (usePlugins)
│   │   └── index.ts
│   ├── audit/                 # Audit & compliance ledger
│   │   ├── components/        # Audit table, drawer, output tabs
│   │   ├── hooks/             # useAuditLogs
│   │   ├── lib/               # parseResult helper
│   │   └── index.ts
│   ├── knowledge/             # Partitioned knowledge chunks & governance rules
│   │   ├── components/        # Chunks view, doc/skill editor, rule modal
│   │   ├── hooks/             # useKnowledgeAndRules
│   │   └── index.ts
│   ├── guide/                 # In-app user guide & interactive documentation
│   │   ├── components/        # UserGuideModal, section tabs
│   │   └── index.ts
│   └── mcp/                   # Model Context Protocol modal & connection snippets
│       ├── components/        # McpConfigModal
│       └── index.ts
├── shared/                    # Reusable cross-feature primitives
│   ├── hooks/                 # Generic hooks (useTheme, useFocusTrap, useToast, useSse)
│   ├── lib/
│   │   └── api/               # Domain API client modules (executions, plugins, rules, etc.)
│   └── ui/                    # Accessible UI component library
│       ├── Button.tsx
│       ├── Badge.tsx
│       ├── Card.tsx
│       ├── Modal.tsx
│       ├── Drawer.tsx
│       ├── Tabs.tsx
│       ├── Field.tsx
│       ├── ErrorBoundary.tsx
│       ├── EmptyState.tsx
│       ├── LoadingSpinner.tsx
│       └── SseIndicator.tsx
├── types/                     # Shared TypeScript interfaces & OpenAPI generated types
│   ├── api.generated.ts       # Generated from backend OpenAPI schema
│   └── index.ts               # Domain types, UI models, and contract types
└── __tests__/                 # Vitest component and accessibility suites
```

---

## 2. Hard Architectural Rules

1. **Maximum File Length**: No component file may exceed **~250 lines**. If a component grows past this, extract sub-views, forms, or custom hooks.
2. **Thin Root Composition**: `frontend/src/app/page.tsx` must remain a thin composition file strictly **under 150 lines**. It delegates state management to custom hooks (`useDashboardState`, `useExecutions`, `usePlugins`) and renders top-level views inside `<ErrorBoundary>`.
3. **Container / Presentational Split**:
   - Container components or custom hooks manage state, network requests, and event handlers.
   - Presentational components focus purely on rendering UI primitives, receiving data via typed props.
4. **Zero `alert()` Policy**:
   - The browser native `alert()`, `confirm()`, and `prompt()` functions are strictly forbidden.
   - User notifications and status messages must use the accessible `useToast()` hook (`showToast("...", "info" | "error" | "success")`).
   - Modals and Drawers must be used for confirmations and detailed workflows.

---

## 3. Shared UI Primitives (`frontend/src/shared/ui/`)

| Primitive | Purpose | Key Accessibility / Design Features |
| :--- | :--- | :--- |
| `Button` | Standardized interactive button | `variant` ("primary", "secondary", "danger", "ghost", "outline"), loading spinner state, focus visible rings. |
| `Badge` | Status, scope, and metric tag | `variant` ("default", "success", "warning", "danger", "info", "neutral"), contrast-tuned for light & dark mode. |
| `Card` | Content container pane | Rounded borders, consistent border and background CSS tokens. |
| `Modal` | Centered dialog overlay | `role="dialog"`, `aria-modal="true"`, focus trap (`useFocusTrap`), Esc key dismiss, backdrop click close. |
| `Drawer` | Slide-in side drawer | `role="dialog"`, focus trap, smooth slide transition, right-docked inspector for deep inspection. |
| `Tabs` | Tabbed navigation bar | `role="tablist"` with `role="tab"`, keyboard accessible, active indicator badge. |
| `Field` | Form field wrapper | Associated `<label>`, helper text, error text, consistent font hierarchy. |
| `ErrorBoundary` | React error boundary | Catches render crashes, displays graceful fallback, retry action, prevents white-screen crashes. |
| `EmptyState` | Empty state placeholder | Icon, title, description, and optional call-to-action button. |
| `LoadingSpinner` | Inline or overlay spinner | Accessible `role="status"` with screen-reader text (`aria-live="polite"`). |
| `SseIndicator` | Live stream connection status | Displays Live Stream status ("Connected", "Reconnecting...", "Offline") with pulse animations. |

---

## 4. Theme & Design Tokens

### Dual-Theme Architecture
- **Default Theme**: **Light Mode** (`bg-slate-50` / `bg-white`).
- **Dark Mode**: Activated via `.dark` class on the root `<html>` element.

### Zero Theme Flash
To prevent the unsightly "light flash" when a user with stored dark mode refreshes the page, `frontend/src/app/layout.tsx` injects an inline pre-render script before React hydration:
```html
<script dangerouslySetInnerHTML={{ __html: `
  try {
    const saved = localStorage.getItem("aegisgate-theme");
    if (saved === "dark" || (!saved && window.matchMedia("(prefers-color-scheme: dark)").matches)) {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
  } catch (e) {}
`}} />
```

### Light Mode Contrast Inversion
Tailwind's slate scale is customized in `globals.css` with dedicated overrides for light mode:
- Translucent badges and buttons (`bg-indigo-500/10`, `text-indigo-700`) maintain crisp AA readability on pure white backgrounds.
- High-contrast border borders (`border-slate-200` in light, `border-slate-800` in dark).

---

## 5. Accessibility (A11y) Guidelines

Every component must satisfy WCAG 2.1 AA standards. AegisGate enforces this via automated `vitest-axe` tests:

1. **Dialog Accessibility**:
   - Every `Modal` and `Drawer` component uses `useFocusTrap()` to prevent keyboard focus from escaping into the background DOM.
   - Must expose `aria-labelledby` or `aria-label`.
   - Must dismiss on `Escape` key press and return focus to the trigger button.
2. **Tablist Accessibility**:
   - Containers with `role="tablist"` must strictly contain only elements with `role="tab"`. Non-tab navigation elements must reside outside the tablist container.
3. **Form Accessibility**:
   - All input elements must have an associated `<label>` or explicit `aria-label`.
4. **Live Regions**:
   - Asynchronous status updates (such as SSE indicators or loading alerts) must use `aria-live="polite"` and `role="status"`.

---

## 6. How to Add a New UI Feature

Follow this step-by-step workflow when adding a new view or major functionality:

### Step 1: Create Feature Directory
Create `frontend/src/features/<featureName>/`:
```bash
frontend/src/features/reports/
├── components/
│   ├── ReportsView.tsx
│   └── ReportItemModal.tsx
├── hooks/
│   └── useReports.ts
└── index.ts
```

### Step 2: Implement the Domain API Client
Add API methods to `frontend/src/shared/lib/api/<featureName>.ts`:
```typescript
import { apiGet, apiPost } from "./client";

export async function fetchReports(): Promise<ReportResponse[]> {
  return apiGet<ReportResponse[]>("/api/reports");
}
```

### Step 3: Implement Custom Hook & Subcomponents
1. Create `useReports.ts` to encapsulate data fetching, pagination, and mutations.
2. Build UI subcomponents utilizing shared primitives (`Card`, `Button`, `Badge`, `Modal`).
3. Ensure no single `.tsx` file exceeds 250 lines.

### Step 4: Mount into Dashboard
In `frontend/src/app/page.tsx`:
1. Add tab to `Sidebar.tsx`.
2. Render `<ReportsView ... />` conditionally inside the `<ErrorBoundary>`.

### Step 5: Write Tests
1. Add unit & rendering tests in `frontend/src/__tests__/components.test.tsx`.
2. Add axe-core accessibility verification in `frontend/src/__tests__/accessibility.test.tsx`.
3. Verify test suite and typechecks pass:
   ```bash
   cd frontend
   npm run test
   npm run typecheck
   npm run lint
   ```
