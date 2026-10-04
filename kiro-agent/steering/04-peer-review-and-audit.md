---
inclusion: auto
description: Independent peer-review protocol across Layer 0, Layer 1, and Layer 2, adversarial algorithmic verification, benchmark profiling, and meta-audit reconciliation.
---

# Independent Peer-Review and Meta-Audit Protocol

This document establishes the mandatory protocol for conducting and reconciling technical reviews across codebases, scientific algorithms, and technical manuscripts.

| Review Tier | Audit Boundary | Enforcement Focus |
| :--- | :--- | :--- |
| **Layer 0: Code Audit** | Syntax checks and verifiable execution | Match cited metrics character-for-character against raw terminal stdout |
| **Layer 1: Adversarial Checks** | Algorithm robustness and measurement validity | Profile crossover points against compiled baselines and prevent data leakage |
| **Layer 2: Triage & Consensus** | Severity tiers and interface defense | Group findings strictly by severity and defend deep module boundaries |

---

## 1. Layer 0: Broad Code Audit and Verifiable Traces

Reviews must proceed beyond surface syntax:
1. **Beyond Static Gates**: Static type checkers and linters check syntax rather than mathematical or algorithmic correctness. Reviewers must inspect code logic line by line.
2. **Character-Matched Metrics**: Every reported count, mean, sample variance, confidence interval, and execution duration must match terminal standard output character-for-character from automated test scripts.
3. **Hardware Truth**: Never cite unverified CPU models or memory bounds. System attributes must derive from system commands such as `lscpu` and `uname -m`.
4. **Synthetic Boundary**: Explicitly distinguish toy test fixtures, simulated runs, and proof-of-concept benchmarks from production data. Never present synthetic results as real-world findings.
5. **Systematic Scope**: Systematically inspect method validity, code correctness, benchmark existence, error handling, edge cases, didactic quality, and conclusions.

---

## 2. Layer 1: Adversarial Verification and Profiling

Reviewers must challenge claims under adversarial conditions:
1. **Benchmark Stability**: Never report single-run speedups. Profile runs across repeated trials with and without cache warmup to separate cold-start overhead from true algorithmic speedups. Locate empirical crossover points against vectorized or native baselines.
2. **Metric Soundness**: Verify that mathematical formulas measure the target phenomenon rather than arbitrary coordinate distances. Verify that spatial or directional symmetries do not induce vector cancellation.
3. **Entity Boundaries**: In spatial, temporal, or graph algorithms, isolate entity, sequence, and locus bounds. Prohibit cross-boundary data leakage from flattened array indexing.
4. **Equation Symmetry**: Ensure published mathematical formulas match accompanying code listings and APIs in parameter choices, normalization factors, and correction terms.
5. **Scale Generalization**: Never extrapolate toy dataset properties to production scale without empirical tests across both small and large inputs.

---

## 3. Layer 2: Severity Triage and Consensus

Review findings must follow rigorous standards:
1. **Language Verification**: Verify claims against official language specs and runtime behavior before accepting reported bugs.
2. **Ousterhout Defense**: Defend interfaces that hide complexity. Reject proposals to add shallow pass-through abstractions or fragment coherent configurations.
3. **Severity Levels**:
   - `Critical`: Fabricated metrics, hardware mismatches, broken invariants, or math errors that contradict code.
   - `Major`: Algorithmic data leakage, unstandardized features, or mixing trial counts with sample sizes.
   - `Minor`: Stale comments, leftover print calls, or parameter docstring ambiguities.
   - `Proposed / Refuted`: Constructive enhancements versus refuted findings backed by technical rationale.
4. **Consensus Protocol**: Anchor truth in reproducible deep inspections. Target source verification on points of explicit disagreement. Structure fixes into Priority 1 (Blocking), Priority 2 (Major Fixes), and Priority 3 (Polish and Refutations).
