# Technical Systems Documentation: RFCs, ADRs, Invariants, and Runbooks

This reference establishes writing standards for software architecture proposals (RFCs), Architecture Decision Records (ADRs), system specifications, protocol designs, and operational runbooks. It enforces an **invariant-first**, high-density engineering style that eliminates corporate posturing and focuses on operational reality.

---

## 1. Register Profile & Target Metrics

Systems documentation communicates high-stakes operational constraints where ambiguity causes outages, data loss, or wasted engineering cycles.

| Metric | Profile Target | Rule / Rationale |
| :--- | :--- | :--- |
| **Burstiness ($CV = \frac{\sigma}{\mu}$)** | $0.32 - 0.65$ | Balances crisp invariant declarations with technical exposition. |
| **Syntactic Overhead ($M_{\text{ov}}$)** | $\le 6.5$ | Enforces direct syntactic paths from subjects to operational verbs. |
| **Zombie Nominals ($Z_{\text{nom}}$)** | $\le 1.5\%$ | Keeps system state actions active and accountable. |
| **Demonstrative Anchoring ($DAI$)** | $\ge 0.80$ | Ensures demonstratives point to concrete components or invariants. |
| **Punctuation Balance Ratio ($PBR$)** | $\ge 1.5$ | Prioritizes structural punctuation over parenthetical dashes. |
| **Em-Dashes per 100 words** | $\le 0.20$ | Eliminates breathless narrative cadence. |
| **Max Concrete Anchor Lag** | $\le 200$ words | Delivers schema, CLI invocation, or code within 200 words of a header. |
| **Composite Indices** | $HVI \ge 80.0$, $TPI \ge 85.0$ | Enforces concrete systems grounding and direct engineer voice. |
| *Author Agency (Advisory)* | Imperative / "We" | Authors take direct ownership of operational trade-offs and choices. |

---

## 2. Invariant-First Architecture (The Inverted Pyramid)

### The First-Line Rule
In architecture documents, RFCs, and incident reports, **never begin with background fluff or corporate throat-clearing** (e.g. avoid vague platitudes about modern cloud environments).
- **Line 1 MUST state the core invariant, operational decision, or failure condition.**
- *Example (ADR):* "We migrate session storage from Redis to local NVMe-backed LMDB to eliminate cross-rack network hops under 50,000 req/sec load."
- *Example (RFC):* "This specification defines an append-only write-ahead log format that guarantees monotonic recovery across ungraceful host power termination."
- *Example (Incident Postmortem):* "At 14:02 UTC, the primary PostgreSQL node deadlocked due to unindexed foreign key cascading deletes during the user purge batch."

---

## 3. The Core Specification vs. Verification Appendix Model

To eliminate corporate fluff and solve the enterprise compliance dilemma (CYA vs. engineering readability), partition every major systems document into two explicit sections:

```markdown
# [SYSTEM SPEC / RFC / ADR TITLE]

## SECTION 1: THE CORE SPECIFICATION (Gated for Human Systems Engineers)
- Length: Strictly <= 300 words.
- Invariants & Guarantees: Exact safety and liveness properties.
- Architectural Decision & Rationale: Why approach A was chosen over B.
- Concrete Hardware/OS Constraints: Target CPU, memory limits, network topology.
- Explicit Failure Modes: What breaks when nodes crash or partitions occur.
- Negative Controls & Discarded Alternatives: What failed during benchmarking.

---

## SECTION 2: FORMAL VERIFICATION & COMPLIANCE APPENDIX (Auditors & Machines)
- Complete interface schemas (Protobuf, OpenAPI, FlatBuffers, GraphQL).
- Raw reproduction commands, terminal outputs, and flamegraphs.
- Comprehensive failure-mode and recovery matrix.
- Regulatory, SOC2, and data-retention audit checklists.
```

---

## 4. Concrete Hardware Metrics and Negative Controls

AI-generated systems documentation often presents an idealized scenario where components scale without friction and failure modes are ignored. Authentic systems engineering documents operational reality:

### Concrete System Metrics and Failure Primitives
Technical specifications must cite concrete physical and operating system entities:
- **Exact Linux Errno Codes & Syscalls:** Cite `epoll_wait(2)`, `ECONNRESET`, `ETIMEDOUT`, `O_DIRECT`, `MAP_SHARED`.
- **Concrete Memory & Cache Bounds:** Caching layers must specify cache line alignment (64 bytes), L1/L2 sizes (32 KB, 1 MB), or NUMA nodes.
- **Explicit Timeout & Quorum Metrics:** Never say *"The system waits a short time before retrying."* State: *"The client initiates exponential backoff starting at 50 ms (jitter $\pm 15$ ms) with a maximum threshold of 2,000 ms before aborting with `Status::DeadlineExceeded`."*

### Explicit Negative Controls & Discarded Dead Ends
Authentic engineering documentation records what was tried and rejected:
> *"We initially implemented the inter-thread messaging queue using lock-free CAS on a circular ring buffer (`std::atomic`). However, sustained profiling revealed high cross-core cache line bouncing across dual-socket AMD EPYC nodes, degrading throughput by 38% compared to a partitioned single-producer single-consumer (SPSC) design. We adopted the partitioned SPSC architecture."*

---

## 5. Ousterhout’s Principle: Deep Modules over Shallow Interfaces

When specifying system components and API contracts, follow John Ousterhout’s *Philosophy of Software Design*:
- **Deep Modules:** An interface must be simple relative to the complexity it conceals. A deep module provides powerful functionality through a tiny API surface.
- **Reject Shallow Abstractions:** Do not document or create 1:1 pass-through interfaces, wrapper classes that simply forward calls, or configurations fragmented across dozens of micro-classes.
- **Document Failure Modes, Not Just Happy Paths:**
  - What happens when disk space is 100% full?
  - What happens when a TCP RST is received mid-transaction?
  - Is the recovery path automated or manual?

---

## 6. Authoritative Technical Stance in Decision Records

Architecture Decision Records (ADRs) must take an explicit, authoritative technical stance:
- An ADR that provides an equidistant, non-committal summary of three options without choosing an option and defending that choice forces downstream engineers to guess architectural intent.
- Take a definitive architectural stand. Detail the trade-offs honestly, explain why the chosen approach wins for your specific constraints, and record the explicit risks accepted.

---

## 7. Operational Runbooks & Step-by-Step Procedures

Operational runbooks and troubleshooting guides must be executable under emergency outage pressure:
1. **Imperative Mood Only:** Begin every operational step with an active verb (*"Verify"*, *"Execute"*, *"Check"*, *"Restart"*).
2. **Every Command Must Have Expected Output:**
   ```bash
   # Check primary replication status
   pg_isready -h pg-primary.internal -p 5432
   # Expected output: pg-primary.internal:5432 - accepting connections
   ```
3. **Explicit Rollback / Abort Criteria:**
   - *"If step 3 does not complete within 120 seconds, immediately execute the rollback script: `./scripts/abort_migration.sh`."*
4. **Zero Fluff:** Do not include theoretical dissertations in a disaster recovery runbook.
