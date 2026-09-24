# Stage 3: Two-Tier Knowledge Architecture: Synthesized RFCs vs. Exhaustive Dictionaries

A common architectural error when constructing technical skills is collapsing upstream documentation and engineering standards into a single directory. Dumping hundreds of raw vendor documentation pages directly into a skill overwhelms model context, obscures project standards, and exhausts token limits.

---

## 1. The Core Architectural Boundary

During evaluation in thread `65c3bd41-571c-494c-8008-c29529391df5`, the user questioned how external documentation related to internal reference guides:

> *"does the skill link to docs/ ?"*
> *"so when it uses our own references/ vs external docs/ ?"*

This principle separates an **Architectural Synthesis** from an **Exhaustive Grammar Dictionary**:

```
                           Agent Operational Request
                                      │
            ┌─────────────────────────┴─────────────────────────┐
            ▼                                                   ▼
   references/ (Synthesized RFCs)                      docs/ (Upstream Dictionary)
   • Physical execution mechanics                      • docs/INDEX.md topic catalog
   • Sargable partition pruning rules                  • Exact operator signatures
   • Automated formatter styling rules                 • Complete parameter options
   • Incremental merge control patterns                • All system view schemas
```

---

## 2. When to Consult `references/` (Synthesized RFCs)

Engineers and agents consult `references/` for **architectural decisions, physical invariants, performance optimization, and project conventions**. 

The `references/` directory contains dense, opinionated engineering specifications that upstream documentation does not provide:
- **Physical Execution Planning:** Worker slot scheduling, shuffle memory limits, disk spills, and resolving straggler slots.
- **Data Lifecycle Standards:** Multi-tier architectural layers (`01_landing` to `08_metrics`), table lifecycles, and table expiry rules.
- **Incremental Control Patterns:** Standardizing surrogate key hashing, change-data-capture digests (`data_hd`), and partition pruning in mutation statements.
- **Architectural Naming Taxonomies:** Domain-first or entity-first schemas, table suffixes (`_dim`, `_fact`, `_met`, `_jnl`), and standardized class words (`_id`, `_amt`, `_ind`).

Each RFC in `references/` serves as an authoritative systems standard. Documents in this tier must remain concise (under 500 to 1,000 words), densely packed with technical rules, and grounded in physical engine mechanics.

---

## 3. When to Consult `docs/` (Exhaustive Upstream Dictionary)

Engineers and agents consult `docs/` when they require **exact signatures, rare parameters, or complete catalog schemas**.

The `docs/` directory contains the raw, comprehensive upstream reference:
- **Built-in Function Signatures:** Rare string manipulations, cryptographic functions, and hyperloglog sketches.
- **Machine Learning Hyperparameters:** Specific training parameters and objective functions for specialized model architectures.
- **System View Column Schemas:** Exact column names, data types, and nullability flags across system metadata views.

---

## 4. Architectural Division of Responsibilities

The following matrix defines the boundaries between Tier 1 synthesized RFCs and Tier 2 reference dictionaries:

| Technical Dimension | Tier 1: `references/` (RFC Standards) | Tier 2: `docs/` (API Dictionary) |
| :--- | :--- | :--- |
| **Primary Audience** | Autonomous agents planning architectural tasks | Agents extracting exact function parameters |
| **Authoring Style** | Opinionated, dense, prescriptive engineering rules | Descriptive, exhaustive upstream vendor documentation |
| **Token Budget** | Compact (under 1,000 words per specification file) | Large (often spanning hundreds of individual pages) |
| **Update Cadence** | Revised when project conventions or invariants evolve | Updated during scheduled upstream documentation ingestion |
| **Storage Structure** | Flat directory of domain RFCs (`references/*.md`) | Categorized tree mirrored via `docs/INDEX.md` |

---

## 5. The Tiered Lookup Protocol for Autonomous Agents

Autonomous coding agents follow a three-step lookup workflow to minimize context usage while maintaining precision:

1. **Step 1 (Strategy & Rules in `references/`):**
   The agent inspects the relevant synthesized guide to select the correct architectural pattern (such as partition gating, hash fingerprint generation, or temporary table materialization).
2. **Step 2 (Navigation via `docs/INDEX.md`):**
   When specific parameter options or column schemas are required, the agent reads `docs/INDEX.md` to identify the exact local file target.
3. **Step 3 (Syntax & Parameters in `docs/`):**
   The agent reads only the targeted markdown page, extracting the exact signature without scanning unreferenced directories.

This tiered layout prevents context bloat, guarantees adherence to project conventions, and provides instant access to exhaustive technical details.
