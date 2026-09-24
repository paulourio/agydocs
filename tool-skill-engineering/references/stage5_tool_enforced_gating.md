# Stage 5: Tool-Enforced Gating, Formatting Verification, and SDK Parity

Natural language instructions cannot ensure consistent code style or API correctness across generative agent outputs. Relying on prompt phrases such as "write clean and idiomatic code" produces uneven line indents, mixed casing, and unverified library calls.

```bash
# Automated verification workflow for skill code examples
bqfmt -config examples/dot_bqfmt.toml -w examples/*.sql
go -C examples test -count=1 ./...
python3 -m unittest examples/test_schema_extraction.py
bash scripts/verify.sh
```

---

## 1. Machine-Enforced Formatting vs. Subjective Prompting

During the initial construction of `bigquery-googlesql`, the user flagged severe style discrepancies across generated SQL queries in thread `be48a759-f10b-48b1-8ec7-e0e65803a978`:

> *"all of your SQL code and examples must be formatted correctly. Even the style is wrong. You can check with ~/dev/gsql/bqfmt and learn what it is failing, and improve your own guide."*

A production tooling skill eliminates subjective formatting debates by shipping the tool's canonical formatter configuration directly within the skill repository:
- **Canonical Configuration:** Ship `dot_bqfmt.toml` specifying exact column gutters, indentation steps, and casing rules.
- **Automated Validation:** Run the formatter against all code examples during CI or smoke verification. If formatting generates a diff, the test fails.
- **Portable Paths:** Use relative paths or environment variables (`bqfmt`) rather than machine-dependent absolute paths.

---

## 2. Multi-Language SDK Parity and Unit Testing

Tool skills frequently require client library utilities in multiple programming languages (such as Go and Python). Example code must never consist of untested pseudocode.

### Mandatory Verification Matrix
Every language implementation included in the skill must include automated test coverage:

| Component | Implementation File | Verification Suite | Execution Command |
| :--- | :--- | :--- | :--- |
| **Go Client** | `examples/client.go` | `examples/client_test.go` | `go -C examples test -count=1 ./...` |
| **Python Client** | `examples/client.py` | `examples/test_client.py` | `python3 -m unittest discover -s examples -p "test_*.py"` |
| **Shell Utilities** | `scripts/*.sh` | `bash -n syntax checking` | `bash -n scripts/verify.sh` |

If a client feature cannot pass unit tests in the local environment, it must not be shipped as reference code.

---

## 3. The Artifact Verification Script (`verify.sh`)

Every skill repository must provide a single consolidated smoke runner (`scripts/verify.sh`). This script executes all language linters, type checks, and unit tests without requiring manual developer action:

```bash
#!/usr/bin/env bash
set -euo pipefail
# Executes compiler checks, linters, and unit tests across examples/
```

Integrating formatters, unit tests, and smoke scripts transforms code listings from decorative snippets into reliable reference implementations.

---

## 4. Tool Execution Architecture: CLI, SDKs, and MCP Servers

Tooling skills coordinate three operational layers depending on the execution environment:

1. **Deterministic Local CLI Utilities:** Formatters (`bqfmt`), linters, and compiler frontends run locally via shell commands. These utilities execute offline, incur zero network latency, and gate agent output directly.
2. **In-Tree Client SDK Scripts:** Programmatic pipelines and schema extraction routines reside in `examples/`. These scripts provide verified code patterns for developers and agents.
3. **Model Context Protocol (MCP) Integration:** Stateful language servers (such as `gopls-mcp-server`) and cloud service endpoints operate via lazy-loaded MCP tools. Tool skills document necessary MCP server configurations while keeping code formatting and unit tests mechanically gated by local scripts.

### Operational Boundaries Matrix

| Tool Layer | Typical Tooling | Latency Profile | Verification Mechanism |
| :--- | :--- | :--- | :--- |
| **Local CLI Binaries** | `bqfmt`, `go vet`, `bash` | Sub-millisecond, offline | Direct execution via `scripts/verify.sh` |
| **Client SDK Scripts** | `examples/client.go`, `client.py` | Millisecond, local | Unit test suites (`go test`, `unittest`) |
| **MCP Servers** | `gopls-mcp-server`, database MCPs | Variable, remote or daemon | Lazy-loaded tool invocation and schema matching |
