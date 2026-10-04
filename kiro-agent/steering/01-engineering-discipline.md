---
inclusion: always
---

# Operational Discipline and Systems Architecture

This document governs command execution patterns and software architecture conventions across Kiro workspaces.

| Directive Category | Operational Requirement |
| :--- | :--- |
| **Shell Mode** | Non-interactive execution (`PAGER=cat NO_COLOR=1 CI=1`) |
| **Script Cadence** | Consolidate multi-command audits into single executable scripts |
| **Compute Cadence** | Freeze heavy checkpoints early for instantaneous downstream runs |
| **Search Tooling** | Prefer `rg` over `grep` and `fd` over `find` in shell commands |
| **Module Design** | Ousterhout's Deep Modules: interfaces hide internal complexity |
| **Asset Ingestion** | Extract sidecar text metadata before visual binary inspection |
| **Clickable Links** | Create clickable markdown links for files and symbols (`file://`) |

---

## 1. Non-Interactive Command Execution

Every shell command executed through `shell` or `execute_bash` must run non-interactively:
1. **Environment Headers**: Prepend `PAGER=cat NO_COLOR=1 CI=1` to any command invoking CLI utilities that could launch an interactive terminal pager or output terminal formatting codes.
2. **Output Sanitizing**: Strip ANSI control sequences (`\x1b[...m`) from command outputs before performing substring or regex assertions in automated tests.
3. **Exit Code Verification**: Check exit status codes on every command run. Never assume a command succeeded without verifying standard output and standard error streams.
4. **Working Directory Integrity**: Execute tools from the project root using explicit relative or absolute path arguments. Avoid standalone `cd` commands; when subprojects require a localized working directory, chain the directory change within the compound command.
5. **Search Tooling**: Prefer `rg` over standard `grep` and `fd` over standard `find` when executing search commands in the shell. Fall back to standard `grep` and `find` only when `rg` or `fd` is absent from the host path.

---

## 2. Anti-Chatter Script Consolidation

When conducting multi-step diagnostics, repository audits, or complex data audits:
1. **Single Script Runs**: Consolidate multi-step shell commands into a single, self-contained shell script written to a temporary scratch directory.
2. **Deterministic Output**: Run the consolidated script once, inspect the structured output, and proceed with informed edits. Never execute dozens of repetitive shell micro-commands.
3. **Decoupled Compute Cadences**: Identify heavy, deterministic operations early. Cache or freeze foundation checkpoints so that downstream tuning, rendering, or testing runs instantaneously.
4. **Local Documentation Ingestion**: Download external documentation or specifications once into a local scratch path. Perform subsequent searches and analysis locally.

---

## 3. Deep Modules (Ousterhout's Principle)

1. **Interface Depth**: Strive for deep modules where a simple interface abstracts substantial implementation complexity. Avoid shallow interfaces that merely pass calls through to internal dependencies.
2. **Decoupling Boundaries**: Do not create interfaces for the sake of interfaces. Do not over-decouple components that will never be swapped in production.
3. **Separate Layers**: Strictly isolate I/O boundaries, core business computation, and UI rendering into distinct packages.
4. **Portable File Paths**: Never hardcode absolute or machine-dependent filesystem paths. Employ standard path libraries (`pathlib.Path`, `filepath.Join`) and configuration parameters.

---

## 4. Conversational Pairing Register (`chat`) and Clickable Links

1. **Clickable Link Schema**: Create clickable links for all files, relative paths, and code symbols using github-style markdown with the `file://` scheme (such as `[filename](file:///path/to/file)`).
2. **Chat Register Standards**: Follow the `chat` profile from the `writing` skill (`references/conversational_pairing.md`). Avoid sycophancy, polite throat-clearing, and customer-support sign-offs. Deliver root-cause telemetry, file paths, and commands in line 1.
3. **Demonstrative Anchoring**: Bind every demonstrative pronoun to an explicit noun (*"this invariant"*, not bare *"this is"*).
4. **Direct Inquiries**: When specifications are ambiguous, ask directly rather than guessing unverified details.
