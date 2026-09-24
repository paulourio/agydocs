# Tool Skill Engineering: Setup and Requirements

This repository defines the standardized methodology, directory structures, and verification workflows for constructing enterprise tooling skills across autonomous coding environments.

```
Tool Skill Scaffold:
skills/<tool-name>/
├── SKILL.md            # Entry point, core invariants, routing matrix
├── README.md           # System prerequisites and agent rule hooks
├── docs/               # Ingested upstream documentation with relative links
│   └── INDEX.md        # Categorized topic catalog for fast local lookup
├── references/         # Synthesized engineering RFCs and standards
├── resources/          # Cheat sheets, anti-patterns, and eval_runner.py
├── examples/           # Formatted code listings and tested SDK clients
└── scripts/            # Automated verification, dry-run, and fetcher tools
```

---

## 1. Prerequisites and Tooling

Engineers and agents developing technical skills must install standard formatters, language runtimes, and validation tooling:
- **Go Runtime (1.21+):** For compiling the documentation quality gate and testing Go SDK examples.
- **Python Runtime (3.10+):** For running documentation fetchers and Python SDK test suites.
- **Target Tool Formatter:** The official formatting binary for the target engine (such as `bqfmt`, `terraform fmt`, or `clang-format`).
- **Stylometric Quality Gate:** The project quality gate binary compiled from `writing/cmd/quality_gate`.

---

## 2. Agent Rule Configuration

To enforce skill usage during code generation, add this instruction block to your agent configuration files (`GEMINI.md` or `AGENTS.md`):

```markdown
### Tool Skill Engineering Discipline (Mandatory Protocol)
Whenever authoring, revising, or reviewing an autonomous pair-programming skill for a technical tool, database, compiler, or cloud platform:
- Follow the 7-stage lifecycle in `tool-skill-engineering/SKILL.md`.
- Enforce two-tier documentation separation (`docs/` vs `references/`).
- Eliminate foreign dialect syntax through complete omission rather than negative lecturing.
- Ship machine-enforced formatter configurations and verify all code examples with unit tests.
- Audit all documentation files using `quality_gate --profile rfc`.
```

---

## 3. Scaffolding a New Tool Skill

Generate a fully compliant directory skeleton and boilerplate configuration using the scaffolding utility:

```bash
# Scaffold a new tool skill directory in the current workspace
bash tool-skill-engineering/scripts/scaffold_tool_skill.sh <tool-name>
```

This utility creates the canonical directory hierarchy, copies template routers, populates initial SDK client implementations, and initializes verification runners.

---

## 4. Verification and Quality Gating

Execute verification checks to ensure zero static analysis debt and zero stylometric defects:

```bash
# Verify skill test suites and scripts
bash tool-skill-engineering/scripts/verify.sh

# Audit all documentation against the RFC writing profile
writing/bin/quality_gate tool-skill-engineering/ --profile rfc --workers 8
```
