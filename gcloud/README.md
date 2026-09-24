# Google Cloud CLI (gcloud) Skill Setup and Deployment Guide

This guide specifies toolchain tools, setup paths, smoke tests, and rule elevation requirements for the Google Cloud CLI (`gcloud`) skill.

```
Skill Deployment Sequence:
1. Tools ──► 2. Doc Mirror ──► 3. Skill Placement ──► 4. Rule Elevation ──► 5. Smoke Tests
```

---

## 1. Toolchain Prerequisites

Executing and testing this skill requires five core developer utilities:

- **Google Cloud CLI:** Version 500.0.0 or higher provides the core binary (`gcloud`).
- **Python Runtime:** Python 3.11 or higher executes the test runner and doc tools.
- **Go Toolchain:** Go 1.22 or higher compiles and runs SDK client tests.
- **Shell Formatters & Linters:** `shfmt` and `ruff` format and lint scripts.
- **Stylometric Quality Gate:** The Go binary `writing/bin/quality_gate` audits Markdown files.

```bash
# Verify Google Cloud CLI installation and version
gcloud version

# Verify Go, Python, and shell formatting utilities
go version
python3 --version
shfmt -version
ruff --version
```

---

## 2. Skill Setup Paths

Engineers install the skill across workspace or global scopes depending on developer workflows.

### 2.1 Workspace Project Setup
To track the skill in Git alongside infrastructure code, deploy the skill folder into the repository root:

```bash
# Target repository root directory
mkdir -p .agents/skills

# Copy or symlink the gcloud skill directory into the workspace
cp -r /path/to/gcloud .agents/skills/gcloud
```

Antigravity discovers workspace skills by scanning up from the working folder to the Git root.

### 2.2 Global User-Level Setup
To expose the skill across all repositories on a local workstation:

```bash
# Establish global configuration directory
mkdir -p ~/.gemini/config/skills

# Link the gcloud skill into the global discovery path
ln -s /path/to/gcloud ~/.gemini/config/skills/gcloud
```

The runtime exposes the skill router to every agent session launched by the developer.

---

## 3. Elevating Invariants to Direct Agents

Progressive disclosure keeps skills dormant until matching keywords appear in chat prompts. The agent inspects only the top-level name and description until a task demands deep reference docs.

### 3.1 Unconstrained Prompt Fallbacks
When a user prompt lacks exact keywords (such as "delete that staging VM" or "copy my folder to the bucket"), the model often fails to load the specialized skill. In unconstrained turns, the model falls back to base weights.

Base model weights exhibit recurring bugs when generating cloud commands:
- Piping unfiltered resource listings into client-side `grep` or `awk`, burning API quotas.
- Freezing headless continuous integration runners on interactive terminal prompts.
- Persisting long-lived service account JSON private keys to disk.
- Emitting deprecated standalone tools like `gsutil` or obsolete `gcloud docker` commands.
- Building raw shell strings inside subprocess calls, creating shell injection risks.

### 3.2 Precedence Hierarchy and Layer 2 Rules
Antigravity evaluates instructions across four strict precedence layers:

```
┌────────────────────────────────────────────────────────┐
│ Layer 1: Active User Directives (Turn Prompts)         │
├────────────────────────────────────────────────────────┤
│ Layer 2: Global & Workspace Rules (GEMINI.md, AGENTS)  │
├────────────────────────────────────────────────────────┤
│ Layer 3: Activated Specialized Skills (references/)    │
├────────────────────────────────────────────────────────┤
│ Layer 4: Pre-Trained Model Weights (Default Baselines) │
└────────────────────────────────────────────────────────┘
```

Elevating rules moves core engineering invariants from Layer 3 into Layer 2. Placing invariants in Layer 2 forces the agent to use the `gcloud` skill before generating any cloud command, even when user prompts remain brief or ambiguous.

---

## 4. Mandatory Agent Rule Block

To elevate skill invariants, copy this markdown rule block into your project rule file (`GEMINI.md` or `.agents/rules/gcloud.md`) or global config (`~/.gemini/config/GEMINI.md`):

```markdown
### Google Cloud Platform & gcloud Engineering Integrity (Mandatory Skill Directives)
Whenever authoring, revising, optimizing, executing, or reviewing gcloud commands, shell deployment scripts, or GCP programmatic client wrappers:
- You MUST activate and strictly adhere to the `gcloud` skill (`skills/gcloud/SKILL.md`) and its specialized references.
- Mandatory Project Parameter: Always declare `--project=PROJECT_ID` on every command initiating API requests.
- Headless Automation: Append `--quiet` (`-q`) or set `export CLOUDSDK_CORE_DISABLE_PROMPTS=1` to suppress interactive prompts.
- Server-Side Filter Discipline: Prune resources using `--filter="EXPRESSION"`; piping unfiltered output into grep or awk is prohibited.
- Keyless Identity Assumption: Use service account impersonation (`--impersonate-service-account`); static private JSON keys are prohibited.
- Toolchain Hygiene: Standardize storage operations on `gcloud storage`; invoking deprecated `gsutil` commands is prohibited.
- Structured Machine Projections: Extract output fields using `--format="value(...)"` or `--format="json"`; parsing unstructured text is prohibited.
```

Adding this rule block ensures that every agent session follows production cloud rules.

---

## 5. Verification and Test Suite Execution

Run the consolidated smoke test script to verify documentation mirrors, Go clients, Python wrappers, and evaluation runners:

```bash
# Execute consolidated verification checks
bash gcloud/scripts/verify.sh
```

All 18 automated checks must pass before merging pull requests.
