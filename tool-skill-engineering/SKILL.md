---
name: tool-skill-engineering
description: >-
  Expert blueprint and lifecycle methodology for engineering, verifying, and maintaining production-grade
  tooling skills for complex platforms, databases, compilers, CLI utilities, and SDKs (such as BigQuery,
  Snowflake, ClickHouse, DuckDB, or Kubernetes). Use this skill when authoring, auditing, refactoring,
  or testing an enterprise tool skill to enforce two-tier documentation architectures, zero dialect bleed,
  machine-verified formatting, and adversarial integration testing.
---

# Tool Skill Engineering: The Production Blueprint

Engineering an autonomous pair-programming skill for a complex data engine, compiler, or cloud platform requires more than summarizing documentation. Language models exhibit known failure modes when generating technical commands: hallucinating foreign dialect constructs, inventing unsupported flags, emitting unformatted code, burning API quotas on redundant searches, and delivering superficial advice that fails against physical execution engines.

This skill codifies the seven-stage lifecycle used to construct and harden enterprise tool skills (demonstrated by the `bigquery-googlesql` implementation). It establishes strict protocols for scope isolation, offline documentation ingestion, two-tier knowledge architectures, dialect hygiene, machine-enforced formatting, adversarial integration testing, and global rule elevation.

```
Stage 1: Scope & Boundaries ──► Stage 2: Offline Ingestion ──► Stage 3: Two-Tier Architecture
                                                                             │
Stage 6: Adversarial Testing ◄── Stage 5: Tool-Enforced Gating ◄── Stage 4: Dialect Hygiene
          │
          ▼
Stage 7: Rule Elevation & Monorepo Integration
```

---

## Core Engineering Invariants

Every production tooling skill must enforce eight non-negotiable engineering invariants:

- **Physical Architecture Grounding:** Ground the skill in the tool's physical storage, compute, and memory architecture rather than presenting it as an abstract syntax layer. Analytical database skills must model distributed worker slots, columnar compression layouts, network shuffle fabrics, and memory spill mechanics. Cloud infrastructure skills must model control planes, reconcile loops, and resource quotas.
- **Offline Documentation Ingestion (Download Once, Analyze Locally):** Never burn live search engine queries or web requests repeatedly for technical documentation. Ingest upstream documentation into a local offline mirror (`docs/`), rewrite all cross-links to local relative markdown paths, protect code fences, and verify the fetcher with unit tests.
- **Deterministic Foundation Caching:** Detect heavy, deterministic operations and external resource dependencies early. If an operation or external fetch can be performed once and re-used, cache or freeze the foundational checkpoint into local storage or intermediate temporary tables. Downstream execution, tuning, or rendering passes must read directly from the frozen checkpoint, prohibiting repeated recomputation or redundant network retrieval.
- **Two-Tier Knowledge Isolation:** Strictly separate synthesized engineering standards (`references/`) from exhaustive upstream reference dictionaries (`docs/`). Agents consult `references/` for architectural strategy, optimization protocols, and formatting invariants; agents consult `docs/INDEX.md` and `docs/` for parameter matrices, function signatures, and system view schemas.
- **Dialect Hygiene & Complete Omission:** Eliminate foreign dialect constructs, obsolete syntaxes, and out-of-scope services. When a construct does not exist in the target tool, omit the construct entirely. Never lecture on non-existent features or construct artificial contrastive strawmen.
- **Machine-Enforced Formatting & SDK Parity:** Code formatting must never rely on model discretion. Integrate standard formatters into the skill toolchain with explicit configuration files. Provide verified client implementations across all primary supported languages, backed by automated unit test suites in `examples/`.
- **Adversarial Operational Testing:** Validate the skill by issuing complex, multi-step engineering prompts to clean agent sessions. Verify that emitted artifacts compile, pass linters, adhere to architectural naming taxonomies, and execute correctly without manual corrections using `resources/eval_runner.py`.
- **Rule Elevation & Centralized CI Verification:** Elevate core non-negotiable invariants into global agent instructions (`RULE[user_global]`, `GEMINI.md`). Embed automated linting, test suites, and stylometric quality gate checks into a root project `Makefile`.

---

## Unified Architecture and Routing Matrix

| Operational Stage | Primary Specification Link | Subsystem Scope and Core Topics |
| :--- | :--- | :--- |
| **Stage 1: Scope & Boundaries** | [Scope & Invariants Guide](references/stage1_scope_and_invariants.md) | Positive inclusion, negative boundary definition, physical engine modeling |
| **Stage 2: Offline Ingestion** | [Documentation Ingestion Guide](references/stage2_docs_ingestion.md) | Scraping pipelines, code fence protection, relative links, `docs/INDEX.md` |
| **Stage 3: Two-Tier Architecture** | [Two-Tier Architecture Guide](references/stage3_two_tier_architecture.md) | `docs/` vs `references/`, indexed routing, progressive disclosure, directories |
| **Stage 4: Dialect Hygiene** | [Dialect Hygiene Guide](references/stage4_dialect_hygiene.md) | Eliminating dialect bleed, omission principles, banning contrastive strawmen |
| **Stage 5: Tool-Enforced Gating** | [Tool-Enforced Gating Guide](references/stage5_tool_enforced_gating.md) | Deterministic formatters, multi-language SDK parity, CLI vs MCP boundaries |
| **Stage 6: Adversarial Testing** | [Adversarial Testing Guide](references/stage6_adversarial_testing.md) | Realistic prompt simulation, naming compliance, automated `eval_runner.py` |
| **Stage 7: Rule Elevation** | [Rule Elevation Guide](references/stage7_rule_elevation.md) | Global instruction hooks, `Makefile` integration, packaging, deployment |

---

## Production Quick Reference

| Dimension | Anti-Pattern | Recommended Production Pattern | Reference Link |
| :--- | :--- | :--- | :--- |
| **Information Gathering** | Live web searching during query generation | Ingest docs locally once into `docs/` with rewritten relative links | [Docs Ingestion](references/stage2_docs_ingestion.md) |
| **Execution Cadence** | Recomputing deterministic steps or refetching resources | Freeze checkpoints early; compute/fetch once and re-use local assets | [Anti-Patterns](resources/anti_patterns_catalog.md) |
| **Documentation Scope** | Monolithic text dump mixing API docs and standards | Two-tier separation: `references/` (RFC standards) + `docs/` (API dictionary) | [Two-Tier Architecture](references/stage3_two_tier_architecture.md) |
| **Dialect Boundaries** | Hallucinating foreign constructs or lecturing on differences | Omit foreign constructs entirely; present only valid idiomatic patterns | [Dialect Hygiene](references/stage4_dialect_hygiene.md) |
| **Code Style** | Prompting model to "write clean, formatted code" | Ship project formatter config and automated verification scripts | [Tool Gating](references/stage5_tool_enforced_gating.md) |
| **SDK Coverage** | Providing code snippets only in one language without tests | Parity across Go and Python SDKs with automated unit test suites | [Tool Gating](references/stage5_tool_enforced_gating.md) |
| **Skill Validation** | Skimming markdown for typographical mistakes | Adversarial prompt evaluation in fresh sessions against complex tasks | [Adversarial Testing](references/stage6_adversarial_testing.md) |
| **Enforcement** | Leaving skill discovery purely to model discretion | Elevate mandatory invariants to global rules and hook into root Makefile | [Rule Elevation](references/stage7_rule_elevation.md) |

---

## Production Resources and Executable Tooling

- **Setup and Deployment:** Consult [Setup and Requirements Guide](README.md) for prerequisite toolchains, directory conventions, and verification steps.
- **Reference SDK Clients:** Inspect [Reference Examples](examples/README.md) for verified Go and Python implementations with unit tests.
- **Anti-Patterns Catalog:** Consult [Anti-Patterns Catalog](resources/anti_patterns_catalog.md) for mechanical failure modes, root causes, and remediation patterns.
- **Automated Eval Runner:** Execute [Eval Runner](resources/eval_runner.py) to assert dialect purity, formatting, and naming taxonomies against code artifacts.
- **Skill Scaffolding Script:** Execute [Scaffold Tool Skill](scripts/scaffold_tool_skill.sh) to generate compliant directory skeletons, boilerplate configurations, and verification scripts.
- **Skill Templates:** Inspect [SKILL.md Template](resources/skill_template/SKILL.md.tmpl), [README.md Template](resources/skill_template/README.md.tmpl), and [Verification Runner Template](resources/skill_template/scripts/verify.sh.tmpl).
