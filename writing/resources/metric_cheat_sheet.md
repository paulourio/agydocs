# Stylometric Metric Reference & Authoring Guide

This reference details the metrics computed by the Go quality gate (`bin/quality_gate`) alongside qualitative heuristics used during editorial review.

> [!NOTE]
> Automated metrics catch syntactic uniformity, passive nominal density, and specific word patterns. They are **necessary but not sufficient** for good technical writing. Text can achieve high scores while still sounding pompous if it employs preachy strawmen, domain laundry lists, or pseudo-intellectual jargon.

---

## Part 1: Automated Metrics Computed by the Quality Gate

### 1. Rhythmic Cadence & Burstiness

#### Coefficient of Variation ($CV$)
Measures sentence length variation across the document:
$$CV = \frac{\sigma}{\mu} = \frac{\sqrt{\frac{1}{N-1}\sum_{i=1}^N (L_i - \mu)^2}}{\mu}$$
- **$L_i$:** Word count of sentence $i$.
- **$\mu$:** Mean sentence length across the document.
- **Diagnostic Bands:**
  - **$CV < 0.30$:** Metronomic pacing (sentences march mechanically at roughly the same length).
  - **$0.30 \le CV \le 0.75$:** Target human range across profiles, spanning RFCs (0.32–0.65), papers (0.40–0.70), and pairing chat (0.30–0.75).
  - **$CV > 0.75$:** Run-on sprawling or fragmented stream of consciousness.

---

### 2. Sentence Structure & Overhead

#### Syntactic Memory Overhead ($M_{\text{overhead}}$)
Approximates the cognitive load imposed by sentence structure:
$$M_{\text{overhead}} = 0.6 \times \overline{\text{SVD}} + 0.8 \times \min(\text{PPD}_{\text{max}}, 6) + 1.0$$
- **$\overline{\text{SVD}}$:** Mean subject-verb distance estimated using sentence-initial clausal prefixes (defaults to 2.0).
- **$\text{PPD}_{\text{max}}$:** Longest consecutive chain of prepositional phrases lacking an intervening verb (capped at 6).
- **$+1.0$:** Baseline syntactic intercept representing root clause processing cost.
- **Guideline:** Keep $M_{\text{overhead}} \le 6.5$ for technical specs; $\le 4.5$ for guides.

---

### 3. Action Clarity & Nominalizations

#### Zombie Nominalization Ratio ($Z_{\text{nom}}$)
Measures bureaucratic nouns (*-tion, -ment, -ance, -ence, -ity, -ization*) that obscure actors and actions:
The ratio is defined as $Z_{\text{nom}} = (\text{Count of Non-Domain Zombie Nominals} / \text{Total Word Count}) \times 100\%$.
- **Target:** $\le 0.8\%$ in tutorials; $\le 1.0\%$ in essays, chat, and briefings; $\le 1.5\%$ in systems specs; $\le 2.0\%$ in scientific papers.
- **Exclusion Policy:** Canonical technical terms (*idempotency, linearizability, authentication, partition, configuration*) are excluded.

---

### 4. Demonstrative & Punctuation Anchoring

#### Demonstrative Anchoring Index ($DAI$)
Evaluates whether sentence-initial demonstratives ("This", "These") attach to a concrete governing noun:
The index is defined as $\text{DAI} = \text{Sentence-Initial } (\text{"This/These"} + [\text{Noun}]) / \text{Total Sentence-Initial } \text{"This/These"}$.
- **Unanchored:** *"This means latency spikes."* (Floating subject).
- **Anchored:** *"This timeout causes latency spikes."* (Bound to head noun).
- **Target:** $\text{DAI} \ge 0.75 - 0.85$ depending on profile.

#### Punctuation Balance Ratio ($PBR$)
Compares deliberate structural punctuation (colons and semicolons) against breathy em-dashes:
The ratio is defined as $PBR = (\text{Count of Colons} + \text{Count of Semicolons}) / (\text{Count of Em-Dashes} + 1)$.
- **Target:** $PBR \ge 1.5$ in systems RFCs, essays, and briefings; $PBR \ge 2.0$ in academic research papers.
- **Enforcement:** Punctuation balance violations trigger only when a document contains 3 or more em-dashes, avoiding false alarms on documents that use em-dashes sparingly.

#### Concrete Anchor Lag
Measures word count from a section heading to the first concrete code block, table, or concrete data point.
- **Target in Guides (`--profile tutorial`):** $\le 150$ words.

---

## Part 2: Qualitative Heuristics for Authors and Reviewers

These properties require human semantic evaluation and cannot be verified by regex counters alone:

### 1. Contrastive Reframe Verification
When using *"Not X, but Y"* or *"X is not Y; it is Z"*:
- **The Pruning Test:** Cut the negative clause. Does the sentence retain its technical meaning? If yes, cut the negative clause and state the point directly.
- **The Strawman Test:** Would any competent engineer argue or believe $X$?
  - *Strawman:* *"Programming is not about typing speed; it is about problem solving."* *(The negated premise is self-evident; cut the negation and state the technical role directly).*
  - *Valid Misconception:* *"Raft does not guarantee zero data loss during disk corruption; it guarantees consensus across surviving honest replicas."* (Corrects a dangerous false assumption).

### 2. Propositional Density
Avoid padding explanations with generic meta-commentary:
- State what the system does, what breaks when it fails, and the exact trade-offs accepted.
- Avoid throat-clearing domain lists (*"In computing, architecture, mathematics, and engineering..."*).
- Avoid grandiose renaming (*"formal axiomatic compression operators"* instead of *"precise technical terms"*).

---

## Part 3: Target Profile Matrix

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
