# Stage 1: Scope Definition, Boundary Setting, and Physical Invariants

A tooling skill must define its operational domain before authoring documentation or writing code examples. Ambiguous scope produces bloated skills that attempt to cover entire enterprise ecosystems superficially while failing on production mechanics.

---

## 1. Defining Positive Scope and Deliberate Exclusions

Every technical skill requires an explicit boundary specification separating supported engine operations from excluded features.

```
┌───────────────────────────────────────┬───────────────────────────────────────┐
│ Positive Scope (In-Scope)             │ Negative Scope (Deliberate Exclusion) │
├───────────────────────────────────────┼───────────────────────────────────────┤
│ Core declarative syntax and operators │ Deprecated or legacy syntax variants  │
│ Physical storage layouts and encodings│ Unmanaged external object formats     │
│ Query execution and worker scheduling │ Remote serverless user functions      │
│ Partitioning and clustering rules     │ Complex enterprise IAM access rules   │
│ Language SDKs and client interfaces   │ Third-party orchestration frameworks  │
└───────────────────────────────────────┴───────────────────────────────────────┘
```

### The Exclusion Principle
Engineers frequently attempt to document every feature mentioned in vendor release notes. During early iterations of the `bigquery-googlesql` skill, authors attempted to cover BigLake object tables, remote Cloud Functions, and legacy SQL syntax. The user intervened to mandate immediate pruning:

> *"Review all files because I think it is not tailored to BigQuery. There are several things that are not possible in BigQuery although implemented in GoogleSQL. These items should be simply removed from our skill."*

Pruning out-of-scope surfaces focuses agent effort on core invariants:
- **Prune Legacy Interfaces:** Drop legacy syntaxes that mislead agents into generating obsolete patterns.
- **Prune Unmanaged Surfaces:** Drop external storage abstractions that lack deterministic schema control.
- **Prune Administrative Overhead:** Isolate operational engineering from organizational identity management unless identity management is the primary subject.

---

## 2. Grounding in Physical Engine Architecture

High-performance tooling skills ground their instructions in physical hardware and systems architecture rather than treating the platform as a syntax translator.

### Analytical Database Invariants
Analytical query skills must explain how declarative statements translate into physical hardware operations:
- **Worker Slot Scheduling:** Queries compile into directed acyclic graphs executed across distributed worker pools. The skill must document worker memory thresholds, shuffle bottlenecks, and long-tail straggler mitigation.
- **Columnar Storage Formats:** Modern engines store data in columnar formats using run-length encoding, dictionary encoding, and bit-packing. The skill must explain how projecting unreferenced columns wastes memory bandwidth and disk read throughput.
- **Network Shuffle Interconnects:** Joins and aggregations transfer data across a high-speed network fabric. Key skew concentrates data volume onto single worker nodes, producing memory spills and delayed execution stages.
- **Persistent Disk Spills:** When worker memory fills, intermediate partitions spill to persistent local disk. The skill must instruct agents to identify spilled bytes and optimize join keys to preserve in-memory throughput.

### Infrastructure and Systems Invariants
For infrastructure tools such as Kubernetes or Terraform, grounding requires physical systems modeling:
- **State Reconciliation Loops:** Explain control loop intervals, etcd Raft consensus mechanics, and serialization limits.
- **Resource Quotas and Scheduling:** Model physical CPU core pinouts, memory limits, and kernel cgroup constraints.

---

## 3. Defining Non-Negotiable Engineering Invariants

Once scope and physical models are established, extract non-negotiable rules for the main skill router:

| Engineering Invariant | Physical Engine Mechanism | Agent Enforcement Rule |
| :--- | :--- | :--- |
| **Strict Projection Discipline** | Columnar memory bus saturation | Explicit column lists; wildcard projection permitted only with guaranteed schema control |
| **Partition & Index Pruning** | Metadata-level file skipping | Sargable boundary predicates in top-level `WHERE` filters; prohibit scalar wrappers on partition keys |
| **Intermediate Materialization** | Execution DAG multi-evaluation | Materialize shared intermediate views into temporary tables rather than duplicating inline CTEs |
| **Numerical Precision Control** | IEEE 754 floating-point drift | Explicit rounding on aggregated ratios; calibrate numeric types to avoid memory expansion |
| **Architectural Naming Standards** | Multi-layer metadata governance | Strict Kimball layer suffixes (`_dim`, `_fact`, `_met`, `_jnl`) and ISO 11179 class words (`_id`, `_amt`, `_ts`) |

---

## 4. Operational Scope Checklist for Skill Authors

Before drafting reference documents or code examples, authors must complete this operational validation checklist:

1. **Document Boundaries:** Are deprecated syntaxes and third-party integrations explicitly excluded from all reference indexes?
2. **Hardware Constraints:** Does the skill document the engine's memory limits, execution DAG topology, and disk spill behavior?
3. **Mechanical Invariants:** Are naming taxonomies, formatting rules, and partition pruning constraints defined as non-negotiable rules?
4. **Targeted Surface:** Is the skill tailored strictly to the specific tool rather than a generic language family?

Establishing these boundary constraints upfront ensures that every subsequent reference document reinforces uniform engineering standards.
