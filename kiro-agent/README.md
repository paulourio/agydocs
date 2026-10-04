# Antigravity Custom Agent for Kiro IDE (Native No-MCP)

This package provides a native custom agent for Kiro IDE and CLI that replicates Google Antigravity engineering standards and GEMINI.md behavioral invariants. The agent operates through Kiro built-in tool categories (`read`, `write`, `shell`, `web`, `subagent`), eliminating dependencies on external Model Context Protocol (MCP) servers or background daemon processes.

| Subsystem Component | File Path | Operational Role |
| :--- | :--- | :--- |
| **Agent Definition (Markdown)** | `kiro-agent/antigravity.md` | Canonical agent configuration and system prompt |
| **Agent Definition (JSON)** | `kiro-agent/antigravity.json` | Programmatic JSON schema representation |
| **System Prompt Body** | `kiro-agent/antigravity.prompt.md` | Pure markdown prompt body referenced by JSON config |
| **Scout Subagent** | `kiro-agent/antigravity-scout.md` | Read-only search and repository exploration subagent |
| **Operational Steering** | `kiro-agent/steering/` | Workspace rules for Gate 0, anti-cheat, and execution |
| **Workflow Recipes** | `kiro-agent/workflows/` | Deterministic pipeline recipes for quality gates and review |
| **Lifecycle Hooks** | `kiro-agent/hooks/` | Event-driven automations for session initialization |
| **Installer Utility** | `kiro-agent/install.sh` | Deployment script for global and workspace scopes |
| **Verification Suite** | `kiro-agent/tests/` | Automated schema validation and NLP quality gate tests |

---

## 1. Architectural Foundation and Tools

The `antigravity` agent configures native Kiro tools to match Google Antigravity runtime behaviors:

1. **Surgical Line-Anchored Modifications**: All targeted file modifications execute via `str_replace`. New files or complete module rewrites execute via `fs_write` atomically.
2. **Non-Interactive Shell Discipline**: Commands execute non-interactively with `PAGER=cat NO_COLOR=1 CI=1`. Terminal output is sanitized of ANSI escape sequences before evaluating assertions in test suites.
3. **Working Directory Integrity**: Commands execute from the project root using explicit relative or absolute path arguments. Standalone `cd` commands are avoided in favor of compound commands.
4. **Clickable Link Generation**: All file paths and code symbols format as clickable github-style links using the `file://` scheme.
5. **Zero-Tolerance Anti-Cheating**: The agent never comments out, deletes, or weakens test assertions. Git commits bypassing pre-commit hooks via `--no-verify`, `-n`, or hook redirection are blocked by declarative deny rules.
6. **Mandatory Gate 0 Quality Gate**: The agent guarantees zero formatting debt, zero linter warnings, clean static typing, and 100% passing test suites before declaring work complete.
7. **Steering Priority Semantics**: Steering files represent RFC 2119 mandatory requirements (MUST, MUST NOT) that override general model defaults. Context-heavy domain protocols load automatically on demand.
8. **Subagent and Workflow Delegation**: Multi-stage tasks delegate to deterministic workflows or isolated subagents. Repository reconnaissance delegates to the read-only `antigravity-scout` subagent.

---

## 2. Workflows and Multi-Agent Orchestration

Kiro 1.2 introduces native workflow orchestration and inter-agent messaging. The `antigravity` agent coordinates deterministic workflows alongside ad-hoc subagent delegation.

### Enabling Workflows in Kiro IDE
Workflows require explicit enablement in workspace (`.kiro/settings.json`) or global (`~/.kiro/settings.json`) settings:
```json
{
  "kiroAgent.workflows.enabled": true
}
```

### Delegation Architecture and Tool Routing
Kiro enforces contextual tool availability based on session depth:

| Context | Available Orchestration Tools | Prohibited Operations |
| :--- | :--- | :--- |
| **Root Interactive Session** | `run_workflow`, `inspect_workflow`, `validate_workflow`, `send_message` | Top-level `invoke_sub_agent` (suppressed by Kiro when workflows are enabled) |
| **Workflow Step Session** | `invoke_sub_agent`, `orchestrate_subagent`, `send_message` | Recursive `run_workflow` calls |

### Bundled Workflow Recipes
The package bundles declarative workflow definitions deployed to `.kiro/workflows/` or `~/.kiro/workflows/`:

1. **Zero-Debt Quality Gate (`zero-debt-gate.workflow.json`)**:
   - Executes non-interactive format validation, unit test verification, and stylometric audits.
   - Iteratively remediates root causes within a bounded loop (up to 5 iterations) without weakening assertions.

2. **Three-Layer Independent Peer Review (`peer-review.workflow.json`)**:
   - Coordinates Layer 0 verifiable execution traces, Layer 1 adversarial verification, and Layer 2 severity triage.
   - Captures Layer 0 structured findings non-destructively through step output and reconciles confirmed findings in Layer 2.

### Step Signaling Protocol
Workflow steps report outcome states through `send_message` and structured artifacts:
- `severity: "success"`: Emits a success notification into the parent session context.
- `severity: "warning"`: Emits an advisory warning without halting turn progression.
- `severity: "error"`: Emits an error notification indicating failure or blockers.
- Step execution loops advance deterministically via `stopCondition` (such as `fileCheck` in `zero-debt-gate` or `completionSignal`).

---

## 3. Installation and Deployment

### Standard Installation (Markdown Format)
Run the installer script from the repository root to deploy `antigravity.md`, steering files, and workflow recipes:
```bash
bash kiro-agent/install.sh
```

### Installation Options
```bash
# Deploy strictly to user global configuration (~/.kiro/)
bash kiro-agent/install.sh --global-only

# Deploy strictly to current workspace (.kiro/)
bash kiro-agent/install.sh --workspace-only

# Skip installing lifecycle hooks
bash kiro-agent/install.sh --no-hooks

# Skip installing workflow recipes
bash kiro-agent/install.sh --no-workflows

# Deploy JSON configuration with external prompt reference
bash kiro-agent/install.sh --format json

# Override the model identifier for your corporate environment
bash kiro-agent/install.sh --model claude-sonnet-5

# Perform a dry-run check without filesystem modifications
bash kiro-agent/install.sh --dry-run
```

### Activating in Kiro IDE
1. Open your workspace in Kiro IDE.
2. In the AI Chat panel header, click the agent selector dropdown.
3. Select **antigravity**.
4. The IDE loads the Antigravity prompt and capability rules for the session.

---

## 4. Verification Suite

Run the automated test suite to validate configuration integrity and stylometrics:
```bash
# Run all unit tests
python3 -m unittest discover -s kiro-agent/tests -p "test_*.py" -v

# Run the NLP stylometric quality gate
writing/bin/quality_gate --profile rfc kiro-agent/antigravity.md
```
