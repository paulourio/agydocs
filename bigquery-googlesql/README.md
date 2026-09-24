# GoogleSQL and BigQuery Engineering Skill: Setup and Requirements

This guide specifies system prerequisites, installation procedures, and operational rules for deploying the `bigquery-googlesql` skill across autonomous coding environments. Teams use these standards to configure agents, enforce code style, and validate GoogleSQL pipelines.

```
Skill Deployment Pipeline:
1. Tool Installation -> 2. Formatter Config -> 3. Agent Instruction Hook -> 4. Validation Suite
```

---

## 1. Prerequisites and Tool Installation

Engineers install command-line utilities and language runtimes to format SQL files, estimate query scan footprints, and test schema definitions.

### 1.1 Google Cloud CLI (`bq`)
The Google Cloud SDK provides the `bq` utility to run dry-run queries and inspect schemas.
Install the CLI through the package manager:
```bash
gcloud components install bq
```
Verify authentication and project configuration before submitting jobs:
```bash
bq version
```

### 1.2 GoogleSQL Formatter (`bqfmt`)
Engineers format all queries and DDL files with the `bqfmt` tool before committing code.
Install the binary directly with Go:
```bash
go install github.com/paulourio/gsql/cmd/bqfmt@latest
```
Add the Go binary path to your shell environment:
```bash
export PATH="${PATH}:${HOME}/go/bin"
```
Verify the installation:
```bash
bqfmt -help
```

### 1.3 SDK Runtimes and Test Suites
The validation tools require Go 1.21 or newer and Python 3.10 or newer.
Install the Python dependencies for the schema client:
```bash
pip install -r examples/requirements.txt
```

---

## 2. Agent Configuration and Requirements

Add this configuration block to agent rule files (`GEMINI.md`, `AGENTS.md`, or system instructions) to enforce BigQuery standards:

```markdown
### GoogleSQL & BigQuery Engineering Integrity (Mandatory Skill Activation)
Whenever authoring, revising, optimizing, or reviewing GoogleSQL queries, routines, DDL, DML, or BigQuery schema architectures:
- You MUST activate and strictly adhere to the `bigquery-googlesql` skill (`skills/bigquery-googlesql/SKILL.md`) and its specialized references.
- Zero formatting debt: All GoogleSQL queries and DDL statements must be formatted and verified using `bqfmt` with the project's `.bqfmt.toml` configuration (`bqfmt -config ~/.gemini/config/skills/bigquery-googlesql/examples/dot_bqfmt.toml <file>` or piped via stdin). Hand-rolled, unverified whitespace formatting is prohibited.
- Strict Architectural Naming: Datasets must declare domain, subdomain, and lifecycle layer (`<domain>_<subdomain>_<layer>`, e.g. `risk_monitoring_08_met`). Tables must declare structural Kimball/Feature Store suffixes (`_dim`, `_fact`, `_met`, `_pred`, `_feat`, `_jnl`). Columns must strictly terminate with ISO 11179 class words (`_id`, `_bk`, `_nm`, `_dt`, `_ts`, `_amt`, `_qty`, `_val`, `_rt`, `_p`, `_ind`, `_cd`).
```

---

## 3. Project Configuration Setup

### 3.1 Deploying Formatter Settings
Copy the reference configuration file to the repository root. This file defines two-space gutters, uppercase keywords, and single-quote string styles:
```bash
cp examples/dot_bqfmt.toml .bqfmt.toml
```
Format a sample query to verify the local configuration:
```bash
bqfmt -config .bqfmt.toml examples/optimized_patterns.sql
```

### 3.2 Skill Placement
Install the skill into user configuration or project directories:
```bash
# Global user directory
mkdir -p ~/.gemini/config/skills
cp -r . ~/.gemini/config/skills/bigquery-googlesql

# Target project directory
mkdir -p .gemini/skills
cp -r . .gemini/skills/bigquery-googlesql
```

---

## 4. Verification and Testing

Run test suites and validation scripts to verify that local tools function as expected:
```bash
# Run Go unit tests and Python test cases
cd examples && go test -count=1 ./...
python3 -m unittest test_schema_extraction.py

# Run a query dry run to verify credentials and billing access
../scripts/dry_run.sh "SELECT 1 AS test_val"

# Check formatting across all SQL examples
bqfmt -config examples/dot_bqfmt.toml -w examples/*.sql
```

---

## 5. Repository Structure and Navigation

```
bigquery-googlesql/
├── SKILL.md                 # Core engineering invariants and routing matrix
├── README.md                # System requirements and agent setup rules
├── docs/                    # Official BigQuery documentation with rewritten local relative links
│   ├── README.md            # Master navigation index and document catalog
│   ├── standard-sql/        # GoogleSQL Classic and Pipe Syntax documentation
│   ├── bigqueryml/          # BigQuery ML (BQML) reference documentation
│   ├── graph/               # Graph Query Language (GQL) in BigQuery documentation
│   ├── information-schema/  # INFORMATION_SCHEMA system views documentation
│   └── system/              # System procedures and system variables
├── references/              # Technical specifications for engine subsystems
│   ├── ddl_reference.md     # Tables, clones, snapshots, indexes, and TVFs
│   ├── dml_and_transactions.md # Mutations, ACID transactions, and merge patterns
│   ├── query_design_and_optimization.md # Seven-phase query optimization framework
│   ├── language_and_syntax.md # Declarative grammar, clauses, and JSON functions
│   ├── pipe_syntax.md       # Linear relational dataflow operators
│   ├── style_and_formatting.md # Casing invariants, clause gutters, and bqfmt rules
│   └── naming_conventions.md# Three-tier naming hierarchy and ISO 11179 taxonomy
├── resources/               # Anti-patterns catalog, cheat sheet, and schema templates
│   ├── anti_patterns_catalog.md # Mechanical failure modes and corrected code
│   ├── cheat_sheet.md       # Clause mapping, diagnostic metrics, and CLI flags
│   └── schema_templates.md  # Canonical schema definitions
├── examples/                # Runnable SQL patterns, bqfmt config, and client code
│   ├── dot_bqfmt.toml       # Reference bqfmt formatter configuration
│   ├── schema_extraction.go # Go SDK schema extraction client
│   └── schema_extraction.py # Python SDK schema utility
└── scripts/                 # Automation scripts for dry runs, verification, exports, and docs ingestion
    ├── fetch_docs.py        # BigQuery documentation fetcher and link rewriter
    ├── fetch_docs.sh        # Runner script for docs ingestion
    ├── test_fetch_docs.py   # Unit tests for documentation fetcher
    ├── dry_run.sh           # Dry run cost and scan estimator
    ├── extract_schema.sh    # Schema definition exporter
    └── verify.sh            # Artifact and query validator
```
