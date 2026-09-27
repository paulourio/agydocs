---
inclusion: always
---

# Anti-Cheating and Verification Integrity Specification

This document defines absolute invariants against speculative shortcuts, test tampering, and unverified execution claims.

| Integrity Boundary | Behavioral Requirement |
| :--- | :--- |
| **Test Assertions** | Zero weakening, commenting out, or deleting of failing tests |
| **Commit Bypasses** | Mandatory rejection of `--no-verify` and `-n` flags |
| **Execution Claims** | Character-for-character match against raw terminal stdout |
| **Data Provenance** | Clear, explicit labeling of synthetic fixtures versus production data |

---

## 1. Test Assertion Preservation

Software verification requires honest test execution.
1. **Zero Test Tampering**: The agent must never comment out, delete, or modify existing test assertions to bypass a failure. If an assertion fails, the defect resides in the implementation under test.
2. **No Artificial Skips**: Never insert test-skipping decorators, directives, or flags (`@pytest.mark.skip`, `t.Skip()`, `xit`, `it.skip`) to force a test run to report success.
3. **Negative Controls**: Maintain explicit negative controls alongside positive benchmarks to prove real fault detection.

---

## 2. Pre-Commit Hook Integrity

Git hooks enforce repository invariants deterministically.
1. **No Flag Bypasses**: Never invoke `git commit` with the `--no-verify` or `-n` flags. Bypassing hooks violates repository integrity policies.
2. **Hook Failure Diagnosis**: If a pre-commit hook rejects a change, analyze the hook output, locate the underlying defect, and correct the files.

---

## 3. Mandatory Verifiable Execution Traces

Never evaluate quantitative claims by reading code alone.
1. **Raw Terminal Match**: Every reported metric, memory measurement, latency count, and test summary must match raw terminal standard output character-for-character.
2. **Exit Code Introspection**: Check exit status codes on every command run. Never report that a test passed without empirical evidence.
3. **Authentic Environment Truth**: Never report fictional CPU models, cluster configurations, or memory limits. All hardware context must derive directly from system tools (`lscpu`, `uname -m`).
