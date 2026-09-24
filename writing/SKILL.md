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

## Workflow

### 1. Select the Register
Identify the target document type and consult its specialized reference:
- **Systems RFCs, ADRs, and specs**: Consult [technical_systems.md](references/technical_systems.md).
- **Scientific papers and preprints**: Consult [scientific_papers.md](references/scientific_papers.md).
- **Developer guides and tutorials**: Consult [guides_tutorials.md](references/guides_tutorials.md).
- **Technical briefings and incident postmortems**: Consult [briefing_format.md](references/briefing_format.md).
- **Code reviews and technical pairing**: Consult [conversational_pairing.md](references/conversational_pairing.md).
- **Core principles and stylistic invariants**: Consult [global_guidance.md](references/global_guidance.md).

### 2. Draft the Technical Core
State concrete invariants, numbers, and decisions first:
- Ground abstract statements in physical referents (such as file paths, system calls, or benchmark metrics) within two sentences.
- Anchor demonstrative pronouns to explicit nouns (*"this trade-off"*, not *"this is"*).
- Syntactically integrate inline code and formulas so sentences remain grammatical if symbols are replaced with standard nouns.

### 3. Review and Self-Audit
Audit drafts against common AI anti-patterns:
- Consult [anti_patterns_catalog.md](resources/anti_patterns_catalog.md) for banned clichés and direct human alternatives.
- Check metric thresholds and qualitative heuristics in [metric_cheat_sheet.md](resources/metric_cheat_sheet.md).
- Inspect register golden benchmarks in [benchmarks/](benchmarks/) ([RFC](benchmarks/rfc_kernel_bypass.md), [Paper](benchmarks/paper_async_fixed_point.md), [Tutorial](benchmarks/tutorial_lockfree_spsc.md), [Essay](benchmarks/essay_leaky_abstractions.md), [Chat](benchmarks/chat_socket_starvation.md), and [Briefing](benchmarks/briefing_incident_summary.md)).
- Review editorial side-by-side edits in [before_after_transformations.md](examples/before_after_transformations.md).

Run the automated stylometric quality gate using the Go binary or shell wrapper:
```bash
# Audit an RFC or ADR using the shell wrapper or compiled Go binary
writing/scripts/quality_gate.sh --profile rfc path/to/doc.md
writing/bin/quality_gate --profile rfc path/to/doc.md

# Audit a scientific paper or research note
writing/bin/quality_gate --profile paper path/to/paper.md

# Audit a developer guide or tutorial
writing/bin/quality_gate --profile tutorial path/to/guide.md

# Concurrent batch audit across a directory
writing/bin/quality_gate references/ --profile essay --workers 8

# Structured JSON output for agent pipelines
writing/bin/quality_gate --profile rfc --json path/to/doc.md
```

### 4. Apply Adversarial Critique Posture
When reviewing or auditing existing prose:
- **Audit adversarially**: Actively search for domain laundry lists, unearned contrastive strawmen, and pseudo-intellectual buzzwords. Do not defend text simply because it exists in the repository.
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

## Quality Gate Thresholds

The quality gate tools ([`bin/quality_gate`](bin/quality_gate) and [`scripts/quality_gate.sh`](scripts/quality_gate.sh)) enforce three stages of validation:
- **Stage 1 (Hard Invariants):** Fast-fails on AI clichés, winks, sycophancy, domain laundry lists, participial tailing clauses, smothered verbs, and sentence-initial mathematical/code symbols.
- **Stage 2 (Stylometric Bands):** Verifies burstiness ($CV$), syntactic overhead ($M_{\text{ov}}$), zombie nominalizations ($Z_{\text{nom}}$), demonstrative anchoring ($DAI$), em-dash frequency, punctuation balance ($PBR$), concrete anchor lag, and low-information contrastive reframes.
- **Stage 3 (Composite Indices):** Reports Human Voice Index ($HVI$) and Technical Precision Index ($TPI$).

| Metric | `rfc` (Specs / ADRs) | `paper` (Research) | `essay` (Architecture) | `tutorial` (Guides) | `chat` (Pairing) | `briefing` (Summaries) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Burstiness ($CV$)** | $0.32 - 0.65$ | $0.40 - 0.70$ | $0.38 - 0.70$ | $0.30 - 0.60$ | $0.30 - 0.75$ | $0.35 - 0.65$ |
| **Max Syntactic Overhead ($M_{\text{ov}}$)** | $\le 6.5$ | $\le 6.5$ | $\le 5.5$ | $\le 4.5$ | $\le 4.0$ | $\le 4.5$ |
| **Max Zombie Nominals ($Z_{\text{nom}}$)** | $\le 1.5\%$ | $\le 2.0\%$ | $\le 1.0\%$ | $\le 0.8\%$ | $\le 1.0\%$ | $\le 1.0\%$ |
| **Demonstrative Anchoring ($DAI$)** | $\ge 0.80$ | $\ge 0.85$ | $\ge 0.80$ | $\ge 0.75$ | $\ge 0.85$ | $\ge 0.85$ |
| **Max Em-Dashes per 100w** | $\le 0.20$ | $\le 0.15$ | $\le 0.25$ | $\le 0.15$ | $\le 0.10$ | $\le 0.10$ |
| **Min Punctuation Balance ($PBR$)** | $\ge 1.5$ | $\ge 2.0$ | $\ge 1.5$ | $\ge 1.0$ | $\ge 1.0$ | $\ge 1.5$ |
| **Max Concrete Anchor Lag** | $\le 200$w | $\le 300$w | $\le 250$w | $\le 150$w | N/A | N/A |
| **Min Human Voice Index ($HVI$)** | $80.0$ | $85.0$ | $85.0$ | $80.0$ | $85.0$ | $80.0$ |
| **Min Precision Index ($TPI$)** | $85.0$ | $85.0$ | $80.0$ | $75.0$ | $80.0$ | $80.0$ |
