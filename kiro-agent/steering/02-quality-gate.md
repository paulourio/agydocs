---
inclusion: always
---

# Zero-Debt Quality Gate Specification

This document establishes the mandatory pre-completion quality gate for code authored or modified within Kiro workspaces.

| Gate Stage | Validation Scope | Target Standard |
| :--- | :--- | :--- |
| **Stage 1: Formatting** | Whitespace, layout, syntax formatting | Zero formatting debt across changed files |
| **Stage 2: Linting** | Static analysis, dead code, style | Zero unresolved linter warnings or errors |
| **Stage 3: Typing** | Type inference, type checking | 100% clean static type check |
| **Stage 4: Tests** | Unit tests, contract tests | 100% passing test assertions |
| **Stage 5: Text Quality** | Technical docs and schemas | Stylometric quality gate pass with zero debt |

---

## 1. Quality Gate Invariants

Zero technical debt is permitted. Before completing any task, delivering artifacts, or proposing git commits, the agent must guarantee compliance across five distinct validation stages.
1. **Formatting**: All modified files must conform strictly to the project's formatting standard (`cargo fmt`, `gofmt`, `prettier`, `ruff format`).
2. **Linting**: Resolve all compiler warnings and static linter findings (`ruff`, `eslint`, `golangci-lint`).
3. **Static Typing**: Static type checking must pass cleanly with zero detected type errors across the entire package.
4. **Test Suite**: Run all relevant unit and integration test suites. Every test assertion must pass cleanly. Prioritize integration tests at subsystem and stage boundaries over trivial getter coverage.
5. **Full-Stack Verification**: Test template variable bindings, DOM element IDs, API payloads, and frontend utility functions through automated tests.
6. **Canonical Single Source**: When data appears across multiple formats, every representation must derive deterministically from one frozen source.

---

## 2. Git Commit Conventions

All git commit messages must adhere strictly to the Conventional Commits v1.0.0-beta.2 specification.
1. **Message Structure**: Every commit subject must follow the structured format `<type>[optional scope]: <description>`.
2. **Allowed Commit Types**: Supported commit types include `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, and `chore`.
3. **Imperative Subject Mood**: Write the subject in imperative, present tense (*"add feature"*, not *"added feature"*).
4. **Hook Integrity Policy**: Never bypass pre-commit validation hooks using the command flags `--no-verify` or `-n`.

---

## 3. Specialized Domain Quality Standards

Code modifying documentation or analytics schemas must meet domain standards:
1. **Technical Writing**: Run the automated stylometric quality gate script on documentation files before delivery. Zero quality gate violations are permitted.
2. **GoogleSQL & BigQuery**: Format queries via `bqfmt`. Datasets must follow `<domain>_<subdomain>_<layer>`. Tables must declare structural suffixes (`_dim`, `_fact`, `_met`, `_pred`, `_feat`, `_jnl`). Columns must terminate with ISO 11179 class words (`_id`, `_bk`, `_nm`, `_dt`, `_ts`, `_amt`, `_qty`, `_val`, `_rt`, `_p`, `_ind`, `_cd`).
