# Catalog of Anti-Patterns in Tool Skill Engineering

This catalog documents recurring failure modes observed during the design, synthesis, and maintenance of autonomous tooling skills. Each entry identifies the anti-pattern, explains the failure mechanism, and provides the corrected production pattern.

```
┌───────────────────────────────┬───────────────────────────────┐
│ Observed Anti-Pattern         │ Corrected Production Pattern  │
├───────────────────────────────┼───────────────────────────────┤
│ Iterative Search Engine Scans │ Offline Ingestion ("Download Once") │
│ Foreign Dialect Contamination │ Strict Complete Omission      │
│ Negative Pedagogical Lecturing│ Direct Idiomatic Documentation│
│ Monolithic Markdown Dumping   │ Two-Tier Architecture         │
│ Subjective Formatting Prompts │ Machine-Enforced Formatters   │
│ Untested Code Snippets        │ Tested SDK Implementation     │
│ Passive Discovery Reliance    │ Global Rule Elevation         │
│ Repeated Compute & Fetching   │ Foundation Caching & Checkpoints│
└───────────────────────────────┴───────────────────────────────┘
```

---

## 1. Iterative Search Engine Scans

- **Anti-Pattern:** Firing repetitive search queries or scraping requests to retrieve syntax details during code generation.
- **Failure Mechanism:** Exhausts API search quotas, slows agent execution, and produces inconsistent code snippets across iterations.
- **Corrected Pattern:** Execute an automated fetcher once during skill creation. Ingest all target documentation into a local offline mirror (`docs/`), rewrite links to local relative paths, and query files locally using fast grep searches.

---

## 2. Foreign Dialect Contamination

- **Anti-Pattern:** Blending syntax, clauses, or flags from competing platforms into code examples (such as using PostgreSQL `WITH ... AS MATERIALIZED` in BigQuery).
- **Failure Mechanism:** Language models train on diverse corpora and bleed familiar keywords into the wrong dialect, causing immediate parser failures.
- **Corrected Pattern:** Enforce strict dialect boundaries. Inspect all emitted code against target language parsers and eliminate all non-native constructs.

---

## 3. Negative Pedagogical Lecturing

- **Anti-Pattern:** Adding warnings that explain why unsupported features do not work ("Dialect-specific hints like X are rejected with syntax errors").
- **Failure Mechanism:** Mentioning foreign tokens primes generative models to emit those exact tokens, while wasting context tokens on negative framing.
- **Corrected Pattern:** Apply the Rule of Complete Omission. Remove every mention of unsupported or foreign constructs. Document only what the target engine supports.

---

## 4. The Monolithic Markdown Dump

- **Anti-Pattern:** Concatenating hundreds of vendor documentation pages into a single massive file or unorganized folder.
- **Failure Mechanism:** Overwhelms model context windows, obscures project-specific invariants, and makes targeted retrieval impossible.
- **Corrected Pattern:** Deploy a two-tier layout: keep synthesized engineering RFCs in `references/` and preserve exhaustive official dictionaries in `docs/`.

---

## 5. Subjective Formatting Prompts

- **Anti-Pattern:** Prompting models with vague adjectives ("write clean, readable, properly indented SQL").
- **Failure Mechanism:** Models interpret style subjectively, producing inconsistent casing, erratic indents, and unaligned clauses.
- **Corrected Pattern:** Ship the project's canonical formatter configuration (`.bqfmt.toml`, `.clang-format`) within the skill repository and enforce zero formatting diffs in CI.

---

## 6. Untested Code Snippets

- **Anti-Pattern:** Authoring sample scripts or SDK integrations directly in markdown without runtime execution.
- **Failure Mechanism:** Code contains subtle bugs, deprecated methods, or incorrect imports that fail during developer execution.
- **Corrected Pattern:** Maintain runnable code files in `examples/`, accompanied by automated unit test suites (`go test`, `unittest`).

---

## 7. Passive Discovery Reliance

- **Anti-Pattern:** Relying solely on skill discovery descriptions without establishing rule anchors.
- **Failure Mechanism:** The model frequently bypasses the skill during quick requests, ignoring critical engineering invariants.
- **Corrected Pattern:** Elevate mandatory invariants into global rule files (`GEMINI.md`, `RULE[user_global]`) and link verification checks to the root `Makefile`.

---

## 8. Repeated Compute and Uncached Resource Retrieval

- **Anti-Pattern:** Recomputing deterministic operations repeatedly across iterations or repeatedly fetching identical external resources, documents, or API responses.
- **Failure Mechanism:** Wastes compute resources, exhausts external network and search quotas, causes execution stalls, and risks inconsistent state drift between downstream steps.
- **Corrected Pattern:** Foundation Caching and Compute Decoupling. Identify heavy, deterministic operations and external resource dependencies early. If an operation or fetch can be performed once and re-used, cache or freeze the checkpoint into local storage or intermediate tables. Downstream execution, evaluation, and rendering passes must read directly from the frozen local checkpoint.
