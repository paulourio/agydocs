---
name: writing
description: >-
  Audits and refines technical prose for systems specifications and research papers.
  Eliminates AI clichés, formulaic contrastive strawmen, and decorative filler while
  preserving formal technical precision. Use when authoring or reviewing RFCs, ADRs,
  research manuscripts, or performing adversarial writing critiques.
---

# Technical Writing and Review

This skill provides an operational workflow, stylometric quality gate, and modular reference library for authoring and auditing technical prose. It enforces sentence variation, concrete technical anchoring, and concise reasoning across engineering documents.

## Scope and Activation Boundaries

Apply this skill and its quality gate to persisted technical prose:
- Systems RFCs, Architecture Decision Records (ADRs), and product specifications.
- Scientific preprints, research papers, and technical evaluation reports.
- Developer guides, operational manuals, and project README files.
- Incident postmortems and executive briefings.

Do NOT run the quality gate or enforce formal prose thresholds on:
- Conversational assistant turns and scratch notes.
- Git commit messages (governed separately by `conventional-commits`).
- Inline code comments, unit tests, or raw CLI command outputs.

## Workflow

### Quick Invocation
Execute the Go binary with compact formatting for automated agent loops:
```bash
writing/bin/quality_gate --profile rfc --level standard --format compact path/to/doc.md
```

### 1. Lazy Reference Loading
To minimize context token consumption, load only the single reference matching your document type:
- **Systems RFCs, ADRs, and specs**: Read [technical_systems.md](references/technical_systems.md) (touchstones: Lamport, Ongaro).
- **Scientific papers and preprints**: Read [scientific_papers.md](references/scientific_papers.md) (touchstones: Shannon, Knuth).
- **Developer guides and tutorials**: Read [guides_tutorials.md](references/guides_tutorials.md) (touchstones: Feynman, Pike).
- **Technical briefings and incident postmortems**: Read [briefing_format.md](references/briefing_format.md).
- **Code reviews and technical pairing**: Read [conversational_pairing.md](references/conversational_pairing.md) (touchstone: Torvalds).
- **Core principles and stylistic invariants**: Read [global_guidance.md](references/global_guidance.md).

Do not load [anti_patterns_catalog.md](resources/anti_patterns_catalog.md) or [metric_cheat_sheet.md](resources/metric_cheat_sheet.md) during initial drafting. Open them only if the quality gate flags a specific Stage 1 lexical violation or unexplained metric failure.

### 2. Draft the Technical Core
State concrete invariants, numbers, and decisions first:
- Ground abstract statements in physical referents (such as file paths, system calls, or benchmark metrics) within two sentences.
- Anchor demonstrative pronouns to explicit nouns (*"this trade-off"*, not *"this is"*).
- Syntactically integrate inline code and formulas so sentences remain grammatical if symbols are replaced with standard nouns.
- Wrap third-party quotes or non-standard legacy excerpts in `<!-- gate:off -->` and `<!-- gate:on -->` comments to skip validation.

### 3. Review with Bounded Remediation
Execute the automated quality gate using the Go binary:
```bash
# Recommended agent loop invocation (compact output, standard tier)
writing/bin/quality_gate --profile rfc --level standard --format compact path/to/doc.md

# Explanatory full report with remediation hints
writing/bin/quality_gate --profile paper --level standard path/to/paper.md

# Rapid advisory check during early drafting
writing/bin/quality_gate --profile tutorial --level draft --format compact path/to/guide.md

# Strict verification for publication preprints and external releases
writing/bin/quality_gate --profile essay --level strict path/to/doc.md

# Concurrent batch audit across a directory
writing/bin/quality_gate references/ --profile essay --workers 8

# Structured JSON output for automated CI pipelines
writing/bin/quality_gate --profile rfc --json path/to/doc.md
```

#### Remediation Protocol
1. **Target errors only**: Remediate fatal `[ERROR]` findings (Stage 1 findings, or any finding under --level strict). Do not alter working technical sentences solely to optimize advisory `[WARN]` or `[INFO]` scores.
2. **Cap iteration loops**: Enforce a strict bound of **at most two remediation passes**. If errors persist after two targeted edits, inspect the specific lines manually. Never enter recursive rewrite loops.

### 4. Apply Adversarial Critique Posture
When reviewing existing prose:
- **Audit adversarially**: Search for domain laundry lists, unearned contrastive strawmen, and pseudo-intellectual buzzwords. Do not defend text simply because it exists in the repository.
- **Look beyond automated scores**: Automated scripts verify syntactic baselines. They cannot judge technical clarity, epistemic honesty, or conversational tone. Evaluate whether the text explains ideas clearly or merely uses jargon to simulate depth.

---

## Universal Invariants

All technical prose produced or audited under this skill must uphold five structural invariants:

1. **Syntactic variation (profile target $0.30 \le CV \le 0.75$):** Vary sentence lengths. Avoid metronomic blocks where every sentence spans 20–25 words. Follow complex technical statements with short, direct sentences.
2. **Demonstrative anchoring (profile target $DAI \ge 0.75 - 0.85$):** Anchor demonstratives ("this", "these") to an explicit governing noun (*"this invariant"*, *"this race condition"*).
3. **Grammatical symbol integration:** Inline identifiers, formulas, and code tokens must flow naturally within normal grammatical sentence structure.
4. **Zero meta-commentary:** Remove self-referential commentary, conversational cheerleading, and theatrical preamble.
5. **Concrete grounding:** Connect theoretical claims to empirical referents (such as source locations or system metrics) within two sentences.

---

## Quality Gate Thresholds and Enforcement Tiers

The quality gate binary ([`bin/quality_gate`](bin/quality_gate)) enforces three validation stages:
- **Stage 1 (Hard Invariants):** Fast-fails on AI clichés, winks, sycophancy, domain laundry lists, participial tailing clauses, smothered verbs, and sentence-initial mathematical/code symbols.
- **Stage 2 (Stylometric Bands):** Verifies burstiness ($CV$), syntactic overhead ($M_{\text{ov}}$), zombie nominalizations ($Z_{\text{nom}}$), demonstrative anchoring ($DAI$), em-dash frequency, punctuation balance ($PBR$), concrete anchor lag, and low-information contrastive reframes.
- **Stage 3 (Composite Indices):** Reports Human Voice Index ($HVI$) and Technical Precision Index ($TPI$).

### Strictness Tiers (`--level`)
- **`draft`**: Stage 1 lexical hits (clichés, winks, sycophancy) remain errors. Other Stage 1 rules drop to warnings, and Stage 2 stylometric bands and Knuth micro-syntax checks are switched off.
- **`standard` (default)**: Stage 1 hard invariants are errors. Stage 2 band deviations are warnings and Stage 3 composite scores are informational, so only Stage 1 findings fail the gate.
- **`strict`**: Every finding, including Stage 2 deviations and the composite voice score, is an error. Use it for preprints and published specifications.

| Metric | `rfc` (Specs / ADRs) | `paper` (Research) | `essay` (Architecture) | `tutorial` (Guides) | `chat` (Pairing) | `briefing` (Summaries) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Burstiness ($CV$)** | $0.32 - 1.00$ | $0.40 - 1.35$ | $0.38 - 0.85$ | $0.30 - 0.65$ | $0.30 - 1.05$ | $0.35 - 0.65$ |
| **Max Syntactic Overhead ($M_{\text{ov}}$)** | $\le 6.5$ | $\le 6.5$ | $\le 5.5$ | $\le 4.5$ | $\le 4.0$ | $\le 4.5$ |
| **Max Zombie Nominals ($Z_{\text{nom}}$)** | $\le 1.8\%$ | $\le 2.0\%$ | $\le 1.2\%$ | $\le 1.0\%$ | $\le 1.0\%$ | $\le 1.5\%$ |
| **Demonstrative Anchoring ($DAI$)** | $\ge 0.50$ | $\ge 0.30$ | $\ge 0.40$ | $\ge 0.70$ | $0.00$ (un-gated) | $\ge 0.30$ |
| **Max Em-Dashes per 100w** | $\le 0.20$ | $\le 0.20$ | $\le 0.25$ | $\le 0.20$ | $\le 0.10$ | $\le 0.10$ |
| **Min Punctuation Balance ($PBR$)** | $\ge 1.5$ | $\ge 2.0$ | $\ge 1.5$ | $\ge 1.0$ | $\ge 1.0$ | $\ge 1.5$ |
| **Max Concrete Anchor Lag** | $\le 4000$w | N/A | $\le 250$w | $\le 550$w | N/A | N/A |
| **Min Human Voice Index ($HVI$)** | $80.0$ | $85.0$ | $85.0$ | $80.0$ | $85.0$ | $80.0$ |
| **Min Precision Index ($TPI$)** | $85.0$ | $85.0$ | $80.0$ | $75.0$ | $80.0$ | $80.0$ |

---

## Benchmark Corpus Verification

The quality gate is continuously verified against empirical ground-truth corpora:
- **Canonical Human Monuments (20 Masterworks)**: Shannon, Knuth, Hardy, Dirac, Pólya, Feynman, Vaswani, Quirk, Lamport, Torvalds, and IETF RFCs (passing under strict mode with 0 errors, HVI = 100.0, TPI = 100.0).
- **Gen-AI Benchmark Corpus (18 Documented Incidents)**: Real-world retracted papers, hallucinated legal briefs (*Mata v. Avianca*), CNET arithmetic errors, and Claude-ese slop (yielding 88.9% strict rejection).

For full benchmark inventories, strict scorecards, and incident details, consult [writing/README.md](README.md).
