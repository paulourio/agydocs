# Scientific Papers & Formal Research: Expository Rigor, Proof Architecture, and the Human Voice

This reference establishes the writing standards for scientific manuscripts, arXiv preprints, algorithmic analyses, and formal mathematical derivations. It adapts the practices of master computer scientists (specifically Donald Knuth and Scott Aaronson) to produce research that is mathematically uncompromising, epistemically modest, and engaging to read.

---

## 1. Register Profile & Target Metrics

Scientific writing demands high semantic density and rigorous formal definitions, but must avoid the bureaucratic numbness of passive nominalization chains.

| Metric | Profile Target | Rule / Rationale |
| :--- | :--- | :--- |
| **Burstiness ($CV = \frac{\sigma}{\mu}$)** | $0.40 - 0.70$ | Alternates short assertions with detailed mathematical derivation. |
| **Syntactic Overhead ($M_{\text{ov}}$)** | $\le 6.5$ | Bounds subject-verb distance and preposition chaining. |
| **Zombie Nominals ($Z_{\text{nom}}$)** | $\le 2.0\%$ | Limits Latinate noun endings while permitting established domain terminology. |
| **Demonstrative Anchoring ($DAI$)** | $\ge 0.85$ | Requires sentence-initial "This" or "These" to bind to an explicit noun. |
| **Punctuation Balance Ratio ($PBR$)** | $\ge 2.0$ | Balances structural colons and semicolons against em-dashes. |
| **Em-Dashes per 100 words** | $\le 0.15$ | Prevents fragmented clause sprawl. |
| **Max Concrete Anchor Lag** | $\le 300$ words | Grounds derivations in concrete numbers within 300 words of a section header. |
| **Composite Indices** | $HVI \ge 85.0$, $TPI \ge 85.0$ | Enforces authentic cadence and formal mathematical grounding. |
| *Mean Sentence Length (Advisory)* | $20 - 30$ words | Advisory guideline for sustained academic exposition (un-gated). |

---

## 2. Voice & Agency: The Participatory "We" vs. Cold Bureaucracy

### The Knuth-Halmos Principle
Scientific tradition often defaults to cold, agentless passive voice (*"It was observed that the bound holds..."*). This artificial distance obscures the reasoning process. 

Donald Knuth and Paul Halmos established the modern gold standard:
> *"The word 'we' is often useful to avoid passive voice... But this use of 'we' should be used in contexts where it means 'you and me together', not a formal equivalent of 'I'. Think of a dialog between author and reader."* (Knuth, *Mathematical Writing*, Stanford CS 209)

- **The Participatory "We" (Encouraged):** Invites the reader along on a joint intellectual journey:
  - *"We now show that the set $S$ is closed under convolution."*
  - *"If we set $\epsilon = 1 / \sqrt{n}$, the error term vanishes as $n \to \infty$."*
- **The Accountable "I" (Encouraged for Single Authors):** Used when acknowledging specific intellectual choices, conjectures, or historical credit:
  - *"I conjecture that $\mathsf{BQP} \not\subseteq \mathsf{BPP}$ even in the presence of advice."*
- **The Imperial "We" (Prohibited):** Using "we" to puff up a solo author's status or simulate consensus where none exists.

### Discourse-Appropriate Agentless Passives (The Given-New Contract)
In scientific writing, agentless passive is linguistically necessary when the experimental apparatus, specimen, or formal mathematical structure is the **thematic Given**:
- **Correct Thematic Passive:**
  - *"The quantum state $|\psi\rangle$ was prepared using Hadamard gates. It was then measured in the computational basis."*
  - *(The state is the focus. Writing "I prepared the quantum state" shifts focus needlessly to the operator).*
- **Defective Agent-Evasion Passive:**
  - *"Mistakes in data collection were made during trial 4."*
  - *(Hides who is responsible; rewrite as "We miscalibrated the sensor in trial 4").*

---

## 3. Motivating Proofs and Invariants

### Beyond the Bourbaki Trap
Presenting mathematics in the sterile format of **Definition $\to$ Lemma $\to$ Theorem $\to$ Proof** makes papers appear logically unassailable, but leaves the reader completely mystified as to *why* the definitions exist in that specific form.

In *Surreal Numbers*, Knuth demonstrated the power of motivating definitions through constructive discovery:
1. **Show the Naive Approach First:** Walk the reader through the intuitive first attempt that almost works.
2. **Expose the Structural Failure:** Demonstrate the concrete edge case or contradiction that breaks the naive approach.
3. **Introduce the Invariant as the Resolution:** Introduce the formal definition as the exact mathematical structure required to resolve the failure mode demonstrated in step 2.

### Framing Fundamental Impossibility Results
When introducing profound theoretical results, do not treat them as mere manipulations of formal symbols. Frame them as **foundational trade-offs forcing a fundamental choice**:
- *Scott Aaronson (Berkeley PhD Thesis):*
  > *"Either the Extended Church-Turing Thesis is false, or quantum mechanics must be modified, or the factoring problem is solvable in classical polynomial time. All three possibilities seem like wild, crackpot speculations—but at least one of them is true!"*
- **Operational Rule:** When proving an impossibility result or computational lower bound, frame it as an explicit trade-off boundary between foundational assumptions.

---

## 4. Mathematical Micro-Syntax

From Stanford CS 209 (*Mathematical Writing*), adhere to these mechanical rules to eliminate working-memory friction:

### Rule 1: Never Begin a Sentence with a Formula or Symbol
Readers depend on sentence-initial capitalization to signal grammatical restart. Beginning with a lower-case variable or mathematical symbol disrupts phonological parsing.
- *Bad:* "$x^n - a$ has $n$ distinct zeroes."
- *Good:* "The polynomial $x^n - a$ has $n$ distinct zeroes."
- *Bad:* "`O(N \log N)` is the upper bound."
- *Good:* "The upper bound is $O(N \log N)$."

### Rule 2: Formula Separation (Intervening Words)
Never place two mathematical formulas adjacent without intervening grammatical words. Adjacent formulas blend together visually and confuse syntax.
- *Bad:* "Consider $S_q, q < p$."
- *Good:* "Consider $S_q$, where $q < p$."
- *Bad:* "For all $x \in A, y \in B$..."
- *Good:* "For all $x \in A$ and $y \in B$..."

### Rule 3: Prose Words over Logic Shorthand
Do not use symbolic shorthand (such as `\therefore`, `\Rightarrow`, `\forall`, `\exists`, `\iff`) inside running text. These symbols belong in displayed formal deductions, not in English sentences.
- *Bad:* "$\forall \epsilon > 0, \exists \delta > 0 \implies |f(x) - L| < \epsilon$."
- *Good:* "For every $\epsilon > 0$, there exists $\delta > 0$ such that $|f(x) - L| < \epsilon$."

### Rule 4: The Concrete Trace Anchor (TAOCP Axiom)
Before presenting abstract asymptotic proofs, trace the algorithm or formula on **concrete numerical values**:
- In TAOCP Vol. 1 §1.1, Knuth traces Euclid's algorithm on $m=544, n=119$ step-by-step ($544 = 4 \times 119 + 68$, etc.) before introducing termination invariants or induction.
- Grounding physical numbers establishes immediate empirical reality.

---

## 5. Adversarial and Game-Theoretic Proof Structuring
 
When proving computational lower bounds or distributed separation results, structure arguments around formal adversary methods:
- **Yao's Minimax Principle (Randomized Complexity):** Model algorithm execution as a two-player zero-sum game between an algorithm designer selecting query strategies and an adversary constructing input distributions. Applying von Neumann's minimax theorem establishes that randomized query complexity corresponds to the optimal distributional lower bound against deterministic algorithms.
- **Quantum Adversary Bounds:** Model distinguishing oracle inputs as tracking inner-product deviation between superpositions. Bounding the rate at which queries diminish state overlaps (the BBBV hybrid argument or Ambainis adversary method) establishes unconditional quantum query lower bounds.

---

## 6. Constructive Steelmanning (The "Sure/Shor" Strategy)

When addressing academic critics, alternative conjectures, or skepticism:
- **Never dismiss skepticism with ad hominem rhetoric or vague hand-waving.**
- **Formalize the skeptic's intuition into a well-defined mathematical object.**
  - Example: Scott Aaronson formalized skepticism about large-scale quantum entanglement into the **"Sure/Shor separator"** (a hypothetical mathematical property separating small verified lab states from 500-digit integer factoring states).
  - Defining the complexity class $\mathsf{TreeBQP} \subseteq \Sigma_3^{\mathsf{P}} \cap \Pi_3^{\mathsf{P}}$ transformed an ideological dispute into a fertile domain of concrete open theorems.

---

## 7. Epistemic Modesty & Calibrated Nuance

Scientific rigor requires precise epistemic stance. Distinguish clearly between what is proven, what is conjectured, and what is empirically observed:

```markdown
┌───────────────────────┬────────────────────────────────────────────────────────┐
│ EPISTEMIC CATEGORY    │ AUTHORITATIVE FORMULATION                              │
├───────────────────────┼────────────────────────────────────────────────────────┤
│ Proven Theorem        │ "Theorem 3 establishes that L(M) is undecidable."      │
│ Conditional Result    │ "Conditioned on the Generalized Riemann Hypothesis..." │
│ Open Conjecture       │ "We conjecture that no such separator exists in BQP."  │
│ Empirical Observation │ "In 10,000 Monte Carlo trials, error never exceeded ε."│
│ Limitation            │ "This bound holds only for planar graphs with d <= 4." │
└───────────────────────┴────────────────────────────────────────────────────────┘
```

- **Reject Performative AI Hand-Wringing:** Eliminate *"It is important to remember that...", "One must cautiously consider that..."*
- **Embrace Formal Mathematical Caveats:** State precise mathematical boundaries directly (*"This reduction holds only in the classical oracle setting; in the quantum oracle setting, the separation collapses"*).

---

## 8. Informative Footnotes: High-Gain Technical Wit

Authors frequently use footnotes to provide high-information-gain remarks that illuminate technical subtleties:
- *Scott Aaronson on Quantum Factoring:*
  > *"The most celebrated practical achievement of quantum computation to date is the factoring of 15 into $3 \times 5$."*
- *Donald Knuth on Algorithm Verification:*
  > *"Beware of bugs in the above code; I have only proved it correct, not tried it."*
- **The Rule:** Technical wit is permitted only if it has **high information gain** and is intelligible only to someone who understands the technical subtlety. Performative keynote cheerleading and theatrical suspense are strictly prohibited.
