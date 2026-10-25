# Contributing to AegisGate

Thank you for your interest in contributing to AegisGate! This document outlines our development workflow, coding standards, and contribution process to help you get started quickly.

---

## 🚀 Environment Setup

### Prerequisites
- **Python**: 3.11+ (Python 3.13 recommended)
- **Node.js**: 18+ (Node 20+ recommended) & npm 9+
- **Git**

### Initial Setup (Fresh Clone)
```bash
# 1. Clone repository
git clone https://github.com/caobahuong/AegisGate.git
cd AegisGate

# 2. Install Python package in editable mode with development dependencies
pip install -e ".[dev]"

# 3. Install Frontend dependencies
cd frontend && npm install && cd ..

# 4. Seed development database
python scripts/tasks.py seed

# 5. Verify installation
python scripts/tasks.py check
```

---

## 🛠 Everyday Development Commands

We provide a Windows-first, cross-platform task runner:

```bash
# Start backend and frontend servers together with colored logs
python scripts/tasks.py dev

# Run all unit tests (Backend pytest + Frontend Vitest)
python scripts/tasks.py test

# Run full CI quality checks (Ruff, Mypy, Pytest, ESLint, TypeScript tsc, Vitest)
python scripts/tasks.py check

# Seed demo data against simulated plugin
python scripts/tasks.py seed

# Clean temporary build and cache artifacts
python scripts/tasks.py clean
```

*(Unix/macOS users may also use `make dev`, `make test`, `make check`, `make seed`, `make clean`).*

---

## 🧪 Testing Guidelines

AegisGate enforces high test coverage and strict type safety:

### 1. Backend Unit Tests
```bash
python -m pytest -q --ignore=tests/browser_verification.py --ignore=tests/system_verification.py
```

### 2. Frontend Component Tests
```bash
cd frontend && npx vitest run
```

### 3. Opt-in Live SQL Server Integration Tests
To test against a real Microsoft SQL Server instance, set the following environment variables:
- `AEGISGATE_TEST_MSSQL_SERVER` (e.g. `localhost` or IP)
- `AEGISGATE_TEST_MSSQL_PORT` (default: `1433`)
- `AEGISGATE_TEST_MSSQL_DATABASE` (e.g. `EnterpriseSales`)
- `AEGISGATE_TEST_MSSQL_AUTH` (`SQL Server Authentication` or `Windows Authentication`)
- `AEGISGATE_TEST_MSSQL_USER` (e.g. `sa`)
- `AEGISGATE_TEST_MSSQL_PASSWORD`
- `AEGISGATE_TEST_MSSQL_TRUST` (`true` or `false`)

When these variables are absent, integration tests automatically skip safely.

### 4. Browser UI Verification
Playwright browser automation tests run via:
```bash
python tests/browser_verification.py
```

---

## 📋 Coding Standards

1. **Language & Text**: Code, inline comments, docstrings, documentation, and UI text must be in **English**.
2. **Type Annotations**: 100% type hints required for Python (`mypy` clean) and TypeScript (`tsc --noEmit` clean).
3. **Exception Handling**: Zero bare `except:` or `except Exception:` without structured handling or re-raising.
4. **No Secrets**: Never commit real database passwords, API tokens, or server IPs to the repository.
5. **Light Mode Contrast**: Dashboard default is Light mode with dark toggle. Verify all UI badges, buttons, and text maintain WCAG AA contrast on white backgrounds.

---

## 🔌 Extension Guides

### 1. Adding a New Governance Rule Type
1. Add rule identifier to `core.engine.governance.RULE_TYPES`.
2. Add inspection logic to `core.engine.governance.GovernanceEngine.inspect_query()`.
3. Add SQL token extraction in `plugins.sql_inspector` if query parsing is needed.
4. Add the rule type option to the form in `frontend/src/components/KnowledgeAndRules.tsx`.
5. Add unit test coverage in `tests/test_governance_hardening.py`.

### 2. Adding a New Target Database Plugin
1. Create a new directory under `plugins/<plugin_name>/`.
2. Create `plugin_manifest.json` describing name, driver, entrypoint (`python adapter.py --serve`), and `default_config`.
3. Implement the 4 standard RPC ports (`sync_knowledge`, `dry_run`, `execute`, `abort`) using `aegisgate-sdk`.
4. Run certification tests using `core.engine.plugin_linter.PluginLinter`.

### 3. Adding a New UI Feature
1. Place React components in `frontend/src/components/`.
2. Strictly type component props in `frontend/src/types/index.ts`.
3. Add unit test assertions in `frontend/src/__tests__/components.test.tsx`.

---

## 📦 Conventional Commits

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:
- `feat(...)`: A new feature or capability
- `fix(...)`: A bug fix
- `docs(...)`: Documentation updates
- `test(...)`: Adding or updating test cases
- `chore(...)`: Tooling, configuration, or packaging updates

---

## 📝 Pull Request Checklist

Before submitting a PR, ensure:
- [ ] `python scripts/tasks.py check` passes with 0 errors.
- [ ] All new code includes unit tests.
- [ ] No database files (`*.db`) or credentials are staged.
- [ ] Documentation (`docs/` and `README.md`) updated if relevant.
- [ ] PR title follows Conventional Commits.
