# Developer Guides & Tutorials: Progressive Disclosure and Pedagogical Clarity

This reference establishes writing standards for developer onboarding tutorials, API guides, architecture walkthroughs, and design documentation. It provides a cognitive framework for transforming developer confusion into operational mastery without patronizing over-simplification or abstract verbosity.

---

## 1. Register Profile & Target Metrics

Developer guides reduce cognitive friction through early executable examples and direct explanation of underlying mechanisms.

| Metric | Profile Target | Rule / Rationale |
| :--- | :--- | :--- |
| **Burstiness ($CV = \frac{\sigma}{\mu}$)** | $0.30 - 0.60$ | Keeps instructional steps clear and rhythmically varied. |
| **Syntactic Overhead ($M_{\text{ov}}$)** | $\le 4.5$ | Minimizes cognitive load during task execution. |
| **Zombie Nominals ($Z_{\text{nom}}$)** | $\le 0.8\%$ | Emphasizes direct actions and concrete tools. |
| **Concrete Anchor Lag** | $\le 150$ words | Delivers working code or schema within 150 words of a header. |
| **Demonstrative Anchoring ($DAI$)** | $\ge 0.75$ | Grounds pronouns in immediate code or concepts. |
| **Em-Dashes per 100 words** | $\le 0.15$ | Prevents meandering side notes in tutorial steps. |
| **Punctuation Balance Ratio ($PBR$)** | $\ge 1.0$ | Prioritizes structured explanation over casual pauses. |
| **Composite Indices** | $HVI \ge 80.0$, $TPI \ge 75.0$ | Enforces executable examples and direct pedagogical voice. |
| *Developer Address (Advisory)* | Directed ("you" / imperative) | Guides the developer through direct actions and verified observations. |

---

## 2. The Concrete Anchor Lag Rule ($\le 150$ Words)

### The Problem of Delayed Code
The most common failure mode in technical tutorials is **delayed instantiation**. An author begins a chapter with abstract commentary before showing working code. Readers skim or abandon the page before finding the implementation.

### The Rule
- The token distance between the introductory section header and the first concrete, executable code fence or data schema must **never exceed 150 words**.
- **Execution:** Give the reader a working code sample immediately. Once the reader has a concrete mental peg in working memory, explain how it works and explore edge cases.

````markdown
<!-- BAD: 350 words of abstract preamble before any code -->
# Getting Started with the Cache Client
Caching is a critical component of modern distributed systems, allowing
applications to achieve low latencies and high throughput by storing frequently
accessed data in fast memory... [continues for 3 paragraphs]

<!-- GOOD: Concrete Anchor Lag = 42 words -->
# Getting Started with the Cache Client
This guide shows you how to initialize a connection pool, write a key with an
explicit TTL, and read it back using the async client.

```python
import asyncio
from storage.cache import CachePool

async def main():
    pool = await CachePool.connect("redis://localhost:6379", max_size=10)
    await pool.set("user:1001", {"name": "Alice"}, ttl_seconds=300)
    user = await pool.get("user:1001")
    print(user)

asyncio.run(main())
```
````

---

## 3. The 4-Stage Progressive Disclosure Flow

Organize tutorial sections according to the **Progressive Disclosure Flow**:

```
[1. Minimal Executable Snippet]
    - Self-contained, copy-pasteable, zero extra dependencies.
    - Demonstrates the happy path in <= 15 lines of code.
       │
       ▼
[2. Intuitive Mental Model]
    - Grounded analogy or physical ASCII flow diagram.
    - Explains what physically happens under the hood.
       │
       ▼
[3. Formal Configuration & API Parameters]
    - Markdown table specifying types, defaults, and constraints.
    - Eliminates guesswork for production deployment.
       │
       ▼
[4. Concrete Edge Cases & Recovery Paths]
    - What happens on timeout, network disconnect, or malformed data.
    - Side-by-side error vs. fix code blocks.
```

---

## 4. Explain Failure Mechanics, Not Just Happy Paths

Developer tutorials fail when they show only happy paths and omit configuration rationale:
- If a setting specifies `max_retries=3`, state why 3 was chosen and document the exception raised when retries are exhausted.
- Explain the mechanism behind configuration parameters so engineers can troubleshoot failures under production anomalies.

---

## 5. Cognitive Ergonomics: Active Scaffolding

Developers troubleshooting code or onboarding onto a platform have limited working memory. Effective guides reduce cognitive overhead:
- **Second-Person Direct Address ("You"):** Address the developer directly as an active operator (*"Inspect the generated query by setting `DEBUG=1`"*).
- **Side-by-Side Error and Fix Blocks:** When demonstrating common pitfalls, show the exact error message alongside the corrected snippet:

````markdown
### Common Pitfall: Unbuffered Channel Deadlock

```go
// BROKEN: Deadlocks if reader is not already listening
ch := make(chan int)
ch <- 42 // Blocks forever!
```

**The Fix:** Use a buffered channel or launch the sender in a goroutine:

```go
// FIXED: Pre-allocates buffer space for 1 item
ch := make(chan int, 1)
ch <- 42 // Completes immediately
```
````

---

## 6. Mandatory Structured Markdown Tables ($N \ge 3$)

Whenever comparing three or more configuration parameters, environment variables, algorithmic choices, or API methods, **never write a wall of prose paragraphs**. 

Use a structured Markdown table:
- Reuses compiled visual scanning templates in human working memory.
- Enables instant lookup of types, defaults, and operational semantics.

| Parameter | Type | Default | Operational Impact |
| :--- | :--- | :--- | :--- |
| `max_connections` | `int` | `100` | Caps thread pool size; prevents socket exhaustion under traffic spikes. |
| `idle_timeout_ms` | `int` | `30000` | Closes idle connections after 30 seconds to reclaim file descriptors. |
| `connect_timeout_ms` | `int` | `2000` | Aborts fast on network partitions; raises `ConnectionTimeoutError`. |
