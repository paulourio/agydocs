# Antigravity Custom Agent for Kiro IDE (Native No-MCP)

This package provides a native custom agent for Kiro IDE that replicates Google Antigravity engineering standards and GEMINI.md behavioral invariants. The agent operates through Kiro built-in tool categories (`read`, `write`, `shell`, `web`, `subagent`, `code`, `goal`), eliminating dependencies on external Model Context Protocol (MCP) servers or background daemon processes.

| Subsystem Component | File Path | Operational Role |
| :--- | :--- | :--- |
| **Agent Definition (Markdown)** | `kiro-agent/antigravity.md` | Canonical agent configuration and system prompt |
| **Agent Definition (JSON)** | `kiro-agent/antigravity.json` | Programmatic JSON schema representation |
| **System Prompt Body** | `kiro-agent/antigravity.prompt.md` | Pure markdown prompt body referenced by JSON config |
| **Operational Steering** | `kiro-agent/steering/` | Workspace rules for Gate 0, anti-cheat, and execution |
| **Lifecycle Hooks** | `kiro-agent/hooks/` | Event-driven automations for session initialization |
| **Installer Utility** | `kiro-agent/install.sh` | Deployment script for global and workspace scopes |
| **Verification Suite** | `kiro-agent/tests/` | Automated schema validation and NLP quality gate tests |

---

## 1. Architectural Foundation and Tools

The `antigravity` agent configures native Kiro tools to match Google Antigravity runtime behaviors:

1. **Surgical Line-Anchored Modifications**: All file modifications execute via `write` and `fs_write`. The agent reads context lines before editing, rejecting blind whole-file overwrites.
2. **Non-Interactive Shell Discipline**: Commands execute non-interactively with `CI=1 PAGER=cat NO_COLOR=1`. Terminal output is sanitized of ANSI escape sequences before evaluating assertions.
3. **Working Directory Integrity**: Commands execute from the project root using explicit relative or absolute path arguments. Issuing `cd` commands is prohibited.
4. **Clickable Link Generation**: All file paths and code symbols format as clickable github-style links using the `file://` scheme.
5. **Zero-Tolerance Anti-Cheating**: The agent never comments out, deletes, or weakens test assertions. Git commits with `--no-verify` or `-n` are blocked by permission rules.
6. **Mandatory Gate 0 Quality Gate**: The agent guarantees zero formatting debt, zero linter warnings, clean static typing, and 100% passing test suites before declaring work complete.
7. **Steering Priority Semantics**: Steering files represent RFC 2119 mandatory requirements (MUST, MUST NOT) that override general model defaults.
8. **Subagent and Autonomous Loops**: Complex tasks delegate to parallel subagents with isolated context, leveraging the `goal` tool for iterative loops.

---

## 2. Installation and Deployment

### Standard Installation (Markdown Format)
Run the installer script from the repository root to deploy `antigravity.md` and steering files:
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

## 3. Verification Suite

Run the automated test suite to validate configuration integrity and stylometrics:
```bash
# Run all unit tests
python3 -m unittest discover -s kiro-agent/tests -p "test_*.py" -v

# Run the NLP stylometric quality gate
writing/bin/quality_gate --profile rfc kiro-agent/antigravity.md
```
