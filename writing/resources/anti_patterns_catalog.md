# Anti-Patterns Catalog: Lexical Tells, Claudisms, and Human Replacements

This catalog indexes formulaic AI writing motifs, pseudo-intellectual Claudisms, bureaucratic zombie verbs, and conversational fluff. It provides direct, authoritative human replacements for every pattern. Cut the fluff. Clear technical writing demands concrete terms and active verbs.

---

## 1. Formulaic Corporate AI Motifs

These phrases stem from RLHF length biases, constitutional critique loops, and corporate defensive culture. Avoid them. State your engineering claims directly.

| Claudism Motif | Why It Fails | Authentic Human Replacement |
| :--- | :--- | :--- |
| **"load-bearing"** *(applied abstractly: "load-bearing concept", "load-bearing prose")* | Metaphorical inflation; idea bears zero physical structural weight. | *"critical invariant"*, *"core prerequisite"*, *"mandatory constraint"*. *(Allow only for physical structures or database tables/indexes).* |
| **"sit with [this / that / the realization]"** | Theatrical reflective pose intended to feign solemnity. | Cut entirely. State the conclusion or trade-off directly. |
| **"the physics of [software / the problem]"** | Confers the inevitability of natural physical law onto mutable human choices. | *"hardware limits"*, *"network boundaries"*, *"kernel constraints"*, *"memory hierarchy"*. |
| **"doing [the / real] work"** | Vague epistemic validator; erases the actual mechanism. | State the exact action: *"serializes mutations"*, *"enforces linearizability"*, *"bounds lock contention"*. |
| **"the honest take" / "an honest conversation"** | Performative candor preceding a diplomatic summary. | Cut entirely. Deliver the unhedged technical finding. |
| **"exact grain"** | Vague pseudo-technical jargon. | *"byte offset"*, *"time resolution"*, *"granularity"*, *"metric sampling interval"*. |
| **"compounds over time"** *(applied metaphorically to abstract concepts)* | Misappropriates financial or biological growth models to describe ordinary drift. | *"accumulates technical debt"*, *"degrades throughput"*, *"increases cache miss rates"*. |

---

## 2. Generic AI Tells & Elevated Buzzwords

These words recur with unnatural statistical frequency across LLM responses because crowd-annotators rewarded elevated vocabulary under time pressure.

| AI Tell | Stylistic Defect | Authentic Human Replacement |
| :--- | :--- | :--- |
| **"delve" / "delving"** | The primary universal marker of synthetic text generation. | *"inspect"*, *"analyze"*, *"profile"*, *"examine"*, *"trace"*. |
| **"tapestry"** | Theatrical visual metaphor ("a rich tapestry of services"). | *"architecture"*, *"subsystem"*, *"network topology"*, *"module dependency graph"*. |
| **"beacon"** | Theatrical moralizing metaphor ("a beacon of reliability"). | *"benchmark"*, *"standard reference"*, *"canonical implementation"*. |
| **"serves / stands as a testament to"** | Copular inflation; replaces active verbs with passive ceremony. | *"proves"*, *"demonstrates"*, *"shows"*, *"confirms"*. |
| **"paramount"** | Overused intensifier ("security is paramount"). | *"critical"*, *"mandatory"*, or state the consequence of failure (*"unauthenticated requests drop with 401"*). |
| **"multifaceted"** | Filler token that avoids detailing actual components. | Name the specific dimensions (*"across disk I/O, network bandwidth, and memory"*). |
| **"intertwined"** | Vague relationship descriptor. | *"tightly coupled"*, *"co-dependent"*, *"synchronously bound"*. |
| **"parsimoniously"** | Lexical register intrusion (stylistic dissonance). | *"sparingly"*, *"conservatively"*, or specify the exact bound (*"capped at 16 workers"*). |
| **"nuanced landscape"** | Generic throat-clearing preamble. | State the specific trade-offs (*"concurrency vs. memory overhead"*). |
| **"seamless / seamlessly"** | Glosses over real latency, serialization costs, and failure modes. | Specify the exact protocol and latency (*"RPC over gRPC with P99 < 5ms"*). |
| **"crucial foundation"** | Generic architectural filler. | State the prerequisite (*"prerequisite schema migration"*). |
| **Domain Laundry List** *(e.g. "In computing, architecture, math, and engineering...")* | Enumerating 3+ disciplines to manufacture unearned scope and authority. | Cut the list; state the technical fact directly in its domain context. |
| **Grandiose Conceptual Renaming** *(e.g. "formal axiomatic compression operators")* | Inflating straightforward technical practices into pseudo-philosophical doctrines. | Use standard domain terms (*"precise technical terms"*, *"exact contracts"*). |

---

## 3. Performative Winks, Keynote Banter & Meta-Padding

LLMs simulate rapport by feigning human self-awareness or theatrical cheerleading.

| Anti-Pattern | Context & Defect | Operational Fix |
| :--- | :--- | :--- |
| **"See what I did there?"** | Conversational wink; attempts to force humorous validation. | Strictly prohibited. Cut. |
| **"Here's the kicker—"** | Theatrical suspense marker before delivering a standard point. | State the finding directly. |
| **"Let's dive in!" / "Buckle up!"** | Performative keynote cheerleading. | Begin immediately with technical substance. |
| **"At the end of the day..."** | Cliché summary pivot. | State the conclusion directly. |
| **"Journey worth taking"** | Inappropriate literary melodrama in systems engineering. | Cut completely. |
| **"Let's unpack this"** | Meta-announcement of subsequent analysis. | Explain the mechanism directly without announcing it. |
| **"Ok, I'm becoming almost meta here"** | Self-referential fourth-wall breach. | Delete commentary on your own output. |

---

## 4. Sycophantic Conversational Flares (Pairing & Chat)

In pair programming and agent chats, sycophancy consumes token bandwidth and reduces communicative authority.

| Sycophantic Pattern | Why It Fails | Authentic Senior Peer Replacement |
| :--- | :--- | :--- |
| **"Certainly! I would be delighted to help!"** | Subservient customer-support opening. | Start directly with the code diff, root cause, or diagnosis. |
| **"That's a fantastic question!"** | Patronizing flattery; evaluates user's intelligence. | Answer the question directly. |
| **"You're absolutely right! Great catch!"** | Unearned cheerleading. | Confirm the finding and state the surgical fix. |
| **"I hope this helps! Happy coding!"** | Formulaic sign-off platitude. | End cleanly at the final verification step or command. |
| **"Feel free to ask if you have more questions!"** | Repetitive closing friction. | End at the period. |

---

## 5. Tailing Participial Clauses (-ing Present Participle Clauses)

Autoregressive models avoid ending sentences by appending dangling participial clauses that moralize or summarize.
- *Defect:* *"We refactored the query planner, highlighting our commitment to database efficiency and paving the way for future scalability."*
- *Defect Mechanics:* Adds 14 tokens without adding a single new empirical measurement or technical invariant.
- *Remediation:* End cleanly at the period. If the secondary action is real, state it in an independent sentence with concrete numbers.
  - *Authentic:* *"We refactored the query planner. Average query execution time dropped by 28% across all join queries."*

---

## 6. Light-Verb Nominalizations (Smothered Verbs)

Burying active verbs inside abstract nominal constructions inflated by generic helper verbs (*perform, facilitate, conduct, make, achieve*).

| Smothered Verb Construction | Direct Active Human Equivalent |
| :--- | :--- |
| *"perform an allocation of"* | **"allocate"** |
| *"facilitate the optimization of"* | **"optimize"** |
| *"make an adjustment to"* | **"adjust"** |
| *"conduct an evaluation of"* | **"evaluate"** |
| *"achieve the mitigation of"* | **"mitigate"** |
| *"provide an explanation of"* | **"explain"** |
| *"execute a termination of"* | **"terminate"** |
| *"reach a determination regarding"* | **"determine"** |

---

## 7. Mathematical Micro-Syntax Violations

Violations that cause cognitive backtrack and phonological friction when reading mathematical or technical prose.

| Violation | Defective Code / Math | Authentic Knuth Formulation |
| :--- | :--- | :--- |
| **Sentence-Initial Symbol** | "$x$ is the primary key in the table." | **"The column $x$ is the primary key in the table."** |
| **Sentence-Initial Code Token** | "`init()` initializes the thread pool." | **"The method `init()` initializes the thread pool."** |
| **Formula Clumping** | "For all $x \in S, f(x) > 0$ holds." | **"For every element $x \in S$, the condition $f(x) > 0$ holds."** |
| **Adjacent Formulas** | "Consider $S_q, q < p$." | **"Consider $S_q$, where $q < p$."** |
| **Logic Symbols in Prose** | "The algorithm terminates $\forall n \ge 1$." | **"The algorithm terminates for all integers $n \ge 1$."** |

---

## 8. Trivial Contrastive Reframes (Strawman Inversion)

Negating an absurd proposition that no competent practitioner would argue produces patronizing filler with zero technical substance.
- *Strawman Slop:* *"Programming is not about typing quickly; it is about solving complex problems."*
  - *(The negated premise is self-evident; cut the negation and state the technical objective directly).*
- *Strawman Semicolon Reveal:* *"Terms are not decorative ornamentation; they are formal axiomatic compression operators."*
  - *(The negated premise sets up an artificial foil to create a contrastive reveal; state the technical role directly).*
- *Valid Disambiguation:* *"Raft does not guarantee zero latency during partitions; it guarantees linearizability across surviving replicas."*
  - *(Corrects an active engineering misconception that causes production outages).*

