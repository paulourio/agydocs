# Stage 7: Rule Elevation, Agent Hooks, and Monorepo Integration

Autonomous agents use progressive disclosure to preserve context tokens: skills remain unread until activated by matching user prompts or direct request. If an agent does not activate a skill during query construction, engineering invariants remain unenforced.

```markdown
<!-- Global Rule Snippet: Mandating Skill Usage -->
### Tooling Engineering Integrity (Mandatory Skill Usage)
Whenever authoring, revising, or reviewing code for <Target Tool>:
- You MUST activate and strictly adhere to the `<target-skill>` skill.
- Zero formatting debt: Format and verify all source files using the canonical tool formatter.
- Strict Architectural Naming: Follow structural layer suffixes and standardized class words.
```

---

## 1. The Rule Elevation Protocol

To guarantee that autonomous agents consistently apply skill standards, teams elevate the skill's non-negotiable invariants into global rule files (`GEMINI.md`, `AGENTS.md`, or `RULE[user_global]`).

In the `agydocs` project, the author elevated the BigQuery skill invariants into Item 7 of the global instructions:
- **Mandatory Skill Usage:** Forcing the agent to load the skill whenever writing or auditing GoogleSQL.
- **Zero Formatting Debt:** Prohibiting hand-rolled whitespace formatting and mandating `bqfmt` execution.
- **Strict Architectural Naming:** Enforcing Kimball layer suffixes and ISO 11179 class words.

Elevating invariants into always-on rules bridges the gap between passive skill documentation and active agent execution.

---

## 2. Precedence Hierarchy for Agent Directives

The runtime environment evaluates instructions according to a strict priority hierarchy:

```
┌────────────────────────────────────────────────────────┐
│ 1. Active User Prompts (Direct Turn Directives)        │
├────────────────────────────────────────────────────────┤
│ 2. Global Agent Rules (RULE[user_global], GEMINI.md)   │
├────────────────────────────────────────────────────────┤
│ 3. Activated Specialized Skills (references/, docs/)   │
├────────────────────────────────────────────────────────┤
│ 4. Pre-Trained Model Weights (Default Baselines)       │
└────────────────────────────────────────────────────────┘
```

Elevating critical constraints into Layer 2 ensures that rules override generic model assumptions even when a skill is not loaded immediately.

---

## 3. Standardized Setup Documentation (`README.md`)

Every skill repository must provide a clear `README.md` detailing operational prerequisites:
- **Toolchain Prerequisites:** Document CLI utilities (such as `gcloud`, `bq`, or `bqfmt`) and required runtime versions.
- **Configuration Deployment:** Provide copy commands to install default formatter configurations (`cp examples/dot_bqfmt.toml .bqfmt.toml`).
- **Agent Hook Snippets:** Provide the exact markdown block that engineers paste into their project or global rule files.

---

## 4. Monorepo Integration and Root Makefile Targets

Tool skills must integrate into the project's central build workflow. The repository `Makefile` coordinates building binaries, testing, and documentation audits:

| Target | Executed Action | Validation Scope |
| :--- | :--- | :--- |
| **`make test`** | Executes Go and Python test suites | Unit tests in `examples/` and `scripts/` |
| **`make audit`** | Executes compiled `quality_gate` binary | Stylometric checks across `references/` and `SKILL.md` |
| **`make clean`** | Removes cache and bytecode artifacts | Cleans `.quality_gate_cache`, `__pycache__`, and test output |

Binding the skill into global configuration symlinks (`~/.gemini/config/skills/<skill-name>`) and central Makefile targets ensures that standards remain active, verified, and permanent across all developer workflows.
