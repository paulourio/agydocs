# Stage 6: Adversarial Operational Testing and Prompt Simulation

Static linters and documentation checkers verify file formatting and syntactic validity. They cannot confirm whether an autonomous agent correctly applies skill guidance when generating code. Validating a tooling skill requires adversarial operational testing through realistic developer tasks executed in clean agent sessions.

```
                  Adversarial Prompt Simulation Loop
                                  │
    ┌─────────────────────────────┼─────────────────────────────┐
    ▼                             ▼                             ▼
Prompt Simulation          Output Inspection             Gap Remediation
• Complex task prompt      • Formatter zero diffs        • Feed gaps into references/
• Clean session context    • ISO 11179 naming words      • Add missing example patterns
• Non-trivial math/logic   • Sargable partition pruning  • Run eval_runner.py in CI
```

---

## 1. Simulating Realistic Engineering Prompts

During the development of `bigquery-googlesql`, reviewers issued challenging prompts across fresh sessions to verify operational behavior:

1. **Partitioned Statistical Metric:** Thread `e340273e-80aa-4d90-b37d-014b0c1132bf` tested drift calculation across partitioned tables:
   > *"let's say I want to write a code to compute PSI of some features comparing table base with predictions, which is partitioned by month_dt. use the skill to give me"*
2. **Analytical Risk Modeling:** Thread `a3c79b53-0c46-4880-ba74-53c62ed4fbd1` tested credit scorecard metrics against a binary target:
   > *"let's say I want to write a bigquery sql code to compute gini of some credit scorecard against a binary target"*

These evaluation prompts confirmed whether the agent could translate architectural guidelines into executable queries without manual correction.

---

## 2. Inspecting Generated Artifacts Against Core Invariants

Reviewers inspect generated artifacts directly against the skill's physical invariants:

| Audit Criterion | Verification Method | Common Failure Mode |
| :--- | :--- | :--- |
| **Formatting Conformance** | Pipe emitted query into formatter (`bqfmt`) | Unformatted keywords or non-standard clause indentation |
| **Dialect Purity** | Scan for foreign syntax tokens | Hallucinated clauses (such as `AS MATERIALIZED`) |
| **Architectural Naming** | Inspect dataset, table, and column names | Missing ISO 11179 class words (`_amt`, `_ind`, `_dt`) |
| **Partition Pruning** | Inspect outer `WHERE` filters | Unsargable date expressions (`WHERE DATE(ts) = ...`) |
| **Precision Control** | Inspect transformed `FLOAT64` projections | Unrounded floating point values leaking IEEE 754 noise |

---

## 3. Remediation and Self-Consistency Audits

When an agent fails an operational challenge, the failure indicates an ambiguity or conflict within the skill documentation:
- **Eliminating Conflicts:** In thread `1829fe69-d9b7-4916-89ab-8b39dafbd973`, the user identified a conflict regarding `SELECT *` projection rules. The specification was refined to allow wildcard projection from temporary tables while strictly prohibiting it on external tables.
- **Expanding Concrete Examples:** When the agent struggled to format trapezoidal math for Gini curves, authors added `examples/scorecard_metrics.sql` directly into the repository.

---

## 4. The Automated Evaluation Runner (`eval_runner.py`)

Ad-hoc manual prompt simulation uncovers initial regressions, but maintaining long-term skill quality requires automated assertion tooling.

The skill toolchain includes `resources/eval_runner.py`:
- **Specification Files (`eval_spec.json`):** Declare prohibited dialect tokens, mandatory filter tokens, and naming regex patterns.
- **Automated Invariant Assertion:** The runner verifies code artifacts against target engine invariants, flagging dialect bleed and style anomalies.
- **Continuous Regression Testing:** Automated test suites execute `eval_runner.py` during smoke checks, catching regressions whenever reference documentation changes.

### Evaluation Workflow Architecture

```
Agent Emitted Code ──► eval_runner.py (--spec eval_spec.json) ──► JSON Audit Report
                              │
       ┌──────────────────────┼──────────────────────┐
       ▼                      ▼                      ▼
Dialect Token Check    Required Filter Check   Naming Convention Scan
```
