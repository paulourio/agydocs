# Global Writing Guidance: Core Principles & Operational Style Guide

This guide establishes the standards for clear, precise technical writing across specifications, architecture decision records, research papers, developer guides, and interactive pairing. It prioritizes concrete technical accuracy and direct human voice while eliminating corporate filler, unearned rhetorical reframes, and robotic AI patterns.

---

## 1. Choosing Exact Technical Vocabulary

### Technical Precision vs. The Jargon Trap
Technical terms are valuable because they carry exact definitions. When an engineer says an operation is *idempotent*, they mean that executing it multiple times leaves the system in the same state as executing it once. 

Replacing that word with a phrase like "asking a box for a number twice gives you the same number" does not make the sentence clearer. Instead, it obscures essential distinctions regarding mutations, network retries, and side effects. 

We should always choose the simplest word that is completely accurate. But when an exact technical term already exists (such as *linearizable*, *deterministic*, or *backpressure*), adopting a clumsy circumlocution creates confusion rather than clarity. Technical vocabulary fails when it hides an empty thought; it succeeds when it names an exact behavioral guarantee.

### Vocabulary Register vs. Sentence Structure
Prose sounds bureaucratic or artificial when simple ideas are buried under tangled sentence structures and action-obscuring nouns (*nominalizations*):

```
                       [VOCABULARY REGISTER]
                                ▲
                                │
    Clear Technical Precision   │ Corporate Jargon & AI Slop
    (Lamport, Brooks, Ritchie)  │ (Zombie nouns, passive chains)
    "Monotonic counters         │ "The orchestration of operational
     prevent replay attacks."   │  resilience facilitates alignment."
  ──────────────────────────────┼─────────────────────────────► [SENTENCE COMPLEXITY]
    Direct Conversational       │ Circumlocutory Oversimplification
    (Clean, punchy speech)      │ (Vague circumlocutions; domain terms omitted)
    "Turn off the power         │ "The coordination server tells the
     before swapping cards."    │  worker nodes to remain safe."
                                │
```

- **Top-Left (Clear Technical Precision):** Exact domain terminology combined with simple, active sentence structure. Short, punchy statements using precise primitives.
- **Top-Right (Corporate Jargon & AI Slop):** Chained prepositional phrases, passive voice, and abstract nouns ending in *-tion*, *-ment*, or *-ance* where actors and physical actions disappear.
- **Bottom-Right (Circumlocutory Oversimplification):** Imprecise phrasing produced when domain-specific invariants are replaced with generic descriptions to satisfy blunt readability scores.
- **Bottom-Left (Direct Conversational):** Everyday vocabulary with simple syntax. Ideal for conversational instructions, but insufficient for formal protocol specifications or compiler passes.

### Hayakawa’s Ladder of Abstraction & The Concrete Trace
S. I. Hayakawa’s (1939) Ladder of Abstraction explains how effective technical communicators maintain clarity:
1. **Move Rapidly Between Abstract and Concrete:**
   State an architectural invariant (*"Conceptual integrity is the central consideration in system design"*), and immediately ground it in a concrete trace (*"One architect designs the module interfaces, data structures, and register assignments"*).
2. **Avoid Floating Abstractions:**
   Generic corporate and AI writing chains one high-level abstraction to another without ever referencing memory buffers, network packets, hardware limits, or source code.
3. **Avoid Unnecessary Concrete Drudgery:**
   Exclusively describing low-level details without stating the governing invariant makes it impossible for the reader to understand system architecture.

---

## 2. The Conditional Style Guide

Rhetorical devices, including contrastive framing, em-dashes, and domain vocabulary, clarify technical trade-offs when applied to essential constraints, but obscure meaning when used as decorative filler.

Before using a rhetorical device, apply two tests:
1. **The Pruning Test:** If you cut the device, does the sentence lose essential technical meaning? If not, cut it.
2. **The Strawman Test:** Does the device negate an absurd or trivial position that no practitioner would argue? If so, cut the negation and state the point directly.

---

### Directive 1: Contrastive Reframes (*"Not X; it's Y"* / *"Not just X, but Y"*)

#### The Problem
Language models frequently assert statements like `"Programming is about problem solving, not typing speed"` or `"Terms are not decorative ornamentation; they are compression operators."`

Practitioners do not treat programming as a typing contest or systems terms as decorative ornamentation. Setting up a trivial or absurd position ($X$) just to knock it down with a dramatic reveal ($Y$) produces a preachy, patronizing lecture.

#### Cut by Default:
- **Trivial Strawmen:** Negating a cliché or absurdity no practitioner would argue (*"Debugging is about diagnosing defects, not staring at screens"*).
- **The Redundant Foil:** Negating something already established or self-evident.
- **The Transition Crutch:** Using *"It's not about X; it's about Y"* as a filler bridge to transition between paragraphs.
- **The Semicolon Reveal:** Joining a strawman negation to a dramatic reveal with a semicolon (*"X is not decorative; it is..."*).

#### Allow When:
- **Correcting an Active Misconception:** When industry intuition holds a common belief that causes real failures:
  > *"Raft does not guarantee zero data loss during physical disk crashes; it guarantees state machine replication across surviving honest nodes."*
- **Disambiguating Frequently Conflated Concepts:** When engineers routinely confuse two distinct technical terms:
  > *"Eventual consistency is not eventual correctness; it guarantees replicas converge to the same value, not that the converged value reflects external physical reality."*
- **Reporting Counter-Intuitive Profiling Results:** When benchmark measurements contradict theory:
  > *"The bottleneck is not memory bandwidth; it is branch misprediction in the deserialization loop."*

**The Operational Rule:** Ask: *"Would a competent engineer plausibly argue X?"* If no, delete the "not X" clause and state Y directly.

---

### Directive 2: The Em-Dash (`—`)

#### The Problem
Language models often deploy the em-dash as an escape hatch to defer grammatical closure. This habit fragments sentence cadence.

#### Cut by Default:
- **The Keynote Synthesis Pause:** Using an em-dash to deliver an emotional punchline or synthetic profundity (*"Distributed consensus requires coordination—and that changes everything"*).
- **The Lazy Clause Joiner:** Replacing a semicolon, period, or conjunction (`and`, `but`) with an em-dash to avoid finishing a sentence.
- **Consecutive Sentence Em-Dashes:** Placing em-dashes in adjacent sentences.

#### Allow When:
- **Critical Operational Constraints:** Setting off an operational constraint where parentheses would de-emphasize criticality and commas would create ambiguous attachment:
  > *"The primary replica commits entries to the write-ahead log before dispatching RPC acknowledgments—persisting all state to non-volatile disk to survive power failure."*
- **Hardware Metric Details:** Expanding a formal noun with immediate concrete numbers or hardware registers:
  > *"The L1 data cache—32 KB, 8-way set associative per core—cannot hold the entire working set."*

**Quantitative Guardrails:** Maximum **1 instance per 500 words** ($\le 0.20/100$w) in systems RFCs, tightened to **$\le 0.15/100$w** in scientific papers and tutorials, and **$\le 0.10/100$w** in chat and briefings; strictly 0 instances of theatrical emotional conclusions.

---

### Directive 3: Elevated & Latinate Vocabulary

#### The Problem
Deploying rare, high-register words (*parsimoniously, bifurcate, obfuscate, ubiquitous, inextricably*) as decorative veneer in casual technical prose triggers stylistic dissonance.

#### Cut by Default:
- **Decorative Latinate Synonyms for Physical Actions:** Using high-register words where standard active verbs are natural:
  - *Avoid:* *"We allocate thread pool workers parsimoniously."* $\to$ *Prefer:* *"We keep the thread pool small."*
  - *Avoid:* *"Let us delve into the database schema."* $\to$ *Prefer:* *"Let's inspect the database schema."*
- **Bureaucratic Zombie Nominals (Agent-Obscuring Abstractions):** Chaining nouns ending in *-tion, -ment, -ance, -ity* that bury the actor and action:
  - *Avoid:* *"The implementation of the optimization of resource utilization facilitates latency reduction."* $\to$ *Prefer:* *"Optimizing CPU caches reduces latency."*

#### Allow When:
- **Canonical Irreducible Technical Terms:** When the term represents an exact mathematical, physical, or computational invariant:
  - *Allow:* *Idempotent, linearizability, Byzantine, monotonic, deterministic, amortized, polymorphism, orthogonal, heuristic.*
- **Peer Register in Formal Specifications:** When writing RFCs, architecture decision records (ADRs), or academic publications where domain precision demands exactitude.

---

### Directive 4: Epistemic Hedging & Calibrated Nuance

#### Cut by Default:
- **Equidistant Hedging on Settled Truths:** Treating poor engineering practices as equally valid alternatives to standard practices for the sake of "balance."
- **Performative Modesty Preambles:** *"It is worth noting that...", "One might argue that...", "It should be remembered that..."*

#### Allow When:
- **Formal Engineering Trade-Offs:** Articulating explicit trade-off boundaries under established theorems (such as CAP, PACELC, or Amdahl's Law):
  > *"While asynchronous replication minimizes write latency, it introduces a bounded window of data loss during ungraceful primary failover."*
- **Empirical Variance & Hardware Boundaries:** Stating measured confidence intervals or hardware boundaries:
  > *"On PCIe 4.0 NVMe drives, write throughput reached 6.2 GB/s; performance under sustained random 4K writes on older SATA SSDs remains uncharacterized."*

---

### Directive 5: Participial Tailing Clauses (*"-ing"* Present Participle Clauses)

#### Cut by Default:
- Moralizing, summarizing, or purposive appendages (*highlighting, underscoring, fostering, ensuring, showcasing, paving the way*). End the sentence cleanly at the period.
  - *Avoid:* *"We migrated the database to PostgreSQL, ensuring that the team remains agile and paving the way for future scale."*
  - *Prefer:* *"We migrated the database to PostgreSQL. Connection pooling now handles up to 5,000 concurrent sessions."*

#### Allow When:
- **Simultaneous Physical or Computational Mechanics:** Describing a secondary mechanical process executing concurrently with the main verb:
  > *"The garbage collector traverses the heap, marking live objects while background worker threads continue processing read requests."*

---

## 3. Reading Flow for Inline Code and Formulas

When readers scan technical prose, they frequently skim over complex symbols, formulas, code identifiers, or type signatures.
- **The Verification Check:** Sentences containing inline formulas, code snippets, or identifiers must remain grammatically complete and phonologically coherent when every code token or mathematical symbol is replaced with the placeholder word **"blah"**.
- **Violation Example:**
  - *"If for all $x \in S$, $f(x) > 0$ holds, is monotonic."*
  - *Blah Test:* *"If for all blah, blah holds, is monotonic."* (yields unreadable syntactic fragmentation).
- **Correct Formulation:**
  - *"The function $f(x)$ is monotonic if $f(x) > 0$ for every element $x \in S$."*
  - *Blah Test:* *"The function blah is monotonic if blah for every element blah."* (fully grammatical and clear).

---

## 4. Demonstrative Pronoun Anchoring

### The Problem of Floating Pronouns
Writers and AI models frequently use the demonstrative pronouns "this", "that", "these", and "those" as solitary subjects:
- *"This means that latency spikes."*
- *"This is because the cache was evicted."*
- *"These are crucial for scalability."*

When "this" stands alone, the reader's working memory must scan backward across multiple clauses to infer what "this" refers to. In complex technical systems with multiple interacting components, floating "this" introduces fatal ambiguity.

### The Demonstrative Anchoring Index ($DAI$)
- **The Rule:** At least 80% of sentence-initial instances of "This" or "These" must be directly bound to a concrete governing head noun.
- **Correct Examples:**
  - *"This invariant prevents double-spending during network partitions."*
  - *"This cache eviction policy degrades throughput under bursty traffic."*
  - *"These telemetry counters indicate packet drops at the switch buffer."*
- **Quantitative Target:** The index is defined as $\text{DAI} = \text{Sentence-Initial } (\text{"This/These"} + [\text{Noun}]) / \text{Total Sentence-Initial } \text{"This/These"} \ge 0.80$.

---

## 5. Technical Authoring and Review Workflow

To prevent outsourcing critical technical reasoning to an LLM without verification:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ PHASE 1: HUMAN CORE DRAFT                                                  │
│ - Author drafts core invariants, trade-offs, and empirical measurements.    │
│ - Grounded in verified system behavior and benchmark numbers.               │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ PHASE 2: ADVERSARIAL INTERROGATION                                          │
│ - Auditor identifies unhandled edge cases, race conditions, failure modes.  │
│ - Tests boundary assumptions and hunts for strawman reframes.               │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ PHASE 3: CONSTRAINED LOCAL-FIRST EXPANSION                                  │
│ - Text is synthesized strictly anchored to local repository files, test     │
│   outputs, and verified architectural notes.                                │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ PHASE 4: AUTOMATED QUALITY GATE AUDIT                                       │
│ - Run quality_gate.py to verify sentence burstiness, syntax overhead, DAI.  │
│ - Apply surgical sentence-coordinate fixes.                                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Document Architecture: Core Specification vs. Verification Appendix

Technical documentation often serves two distinct purposes:
1. **The Human Engineer:** Needs rapid, high-density truth, invariants, failure modes, and trade-offs.
2. **The Compliance Auditor / Tooling:** Needs exhaustive schema diffs, checklists, and machine-readable definitions.

Combining these two documentation functions into running prose produces unreadable filler. Partition major specifications using the **Two-Section Specification Model**:

```markdown
# [SYSTEM COMPONENT / RFC TITLE]

## SECTION 1: THE CORE SPECIFICATION (Gated for Human Systems Engineers)
- Maximum 300 words.
- Explicit invariant summary, architectural decisions, and trade-offs.
- Zero corporate fluff, minimal non-domain nominalizations (Z_nom <= 1.5%).
- Explicit failure modes and negative controls.

---

## SECTION 2: VERIFICATION & COMPLIANCE APPENDIX (Auditors & Tooling)
- Complete interface schemas (Protobuf, OpenAPI, JSON Schema).
- Raw benchmark execution logs, flamegraphs, and reproduction commands.
- Exhaustive failure mode matrices and regulatory traceability tables.
```

---

## 7. Why Word Blacklists Fail

Telling an author or language model *"Do not use `delve`, `tapestry`, or `crucial`"* fails because synonyms replace the banned words without fixing the underlying structure:
- For every banned token, adjacent synonyms are selected (`delve` $\to$ `explore`, `tapestry` $\to$ `mosaic`, `crucial` $\to$ `vital`).
- The underlying defect (monotonous sentence lengths, lack of concrete referents, chained prepositional phrases, and absence of an active actor) remains completely intact.
- **The Solution:** Enforce structural and grammatical invariants (sentence length variance, active verbs, demonstrative anchoring, and concrete anchors) alongside critical human review for tone and substance. Automated gates catch syntactic variance, but cannot replace critical review for preachy posturing or unearned strawmen.
