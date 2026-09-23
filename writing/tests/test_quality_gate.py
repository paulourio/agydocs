"""Unit and integration test suite for quality_gate.py.

Tests Stage 1 invariants, Stage 2 tolerance bands, Stage 3 scoring,
contextual exceptions, and CLI integration.
"""

import json
import subprocess
import sys
import unittest
from pathlib import Path

# Add scripts directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from quality_gate import (
    audit_document,
    compute_anchor_lag,
    extract_sentences,
    split_into_lines_and_prose,
)


class TestTextProcessing(unittest.TestCase):
    """Verifies low-level text parsing and sanitization."""

    def test_split_into_lines_and_prose_strips_code(self):
        sample = (
            "# Header\n"
            "This is a prose sentence.\n"
            "```python\n"
            "def foo():\n"
            "    # not prose\n"
            "    return True\n"
            "```\n"
            "This is another prose sentence.\n"
        )
        lines, prose, _prose_lines = split_into_lines_and_prose(sample)
        self.assertEqual(len(lines), 8)
        self.assertIn("This is a prose sentence.", prose)
        self.assertIn("This is another prose sentence.", prose)
        self.assertNotIn("def foo():", prose)

    def test_extract_sentences(self):
        prose = "Raft guarantees linearizability. The leader writes to disk. Does it survive?"
        sentences = extract_sentences(prose)
        self.assertEqual(len(sentences), 3)
        self.assertEqual(sentences[0], "Raft guarantees linearizability.")
        self.assertEqual(sentences[1], "The leader writes to disk.")
        self.assertEqual(sentences[2], "Does it survive?")

    def test_compute_anchor_lag(self):
        text_lines = [
            "# Title",
            "This is introductory text.",
            "It has ten words in total here.",
            "```python",
            "x = 1",
            "```",
        ]
        lag = compute_anchor_lag(text_lines)
        self.assertIsNotNone(lag)
        self.assertGreater(lag, 0)
        self.assertLess(lag, 20)


class TestStage1Invariants(unittest.TestCase):
    """Verifies Stage 1 Fast-Fail detection of Claudisms, AI tells, and winks."""

    def test_detects_claudisms(self):
        bad_texts = [
            "We must sit with this realization before proceeding.",
            "The physics of software dictates that latency increases.",
            "That assumption is doing real work in our thesis.",
            "Here is the honest take on this architecture.",
            "We must analyze the exact grain of the data.",
            "Technical debt compounds over time in this module.",
        ]
        for text in bad_texts:
            report = audit_document(text, profile_name="essay")
            self.assertFalse(report.passed, f"Expected failure for: {text}")
            rules = [v.rule for v in report.violations]
            self.assertTrue(
                any("Claudism" in r for r in rules),
                f"Missing Claudism rule in: {rules}",
            )

    def test_contextual_load_bearing(self):
        # Concrete systems nouns should PASS Stage 1 Claudism check
        valid_load_bearing = (
            "The users table is a load-bearing table in our schema. "
            "Partitioning this table requires careful migration. "
            "We ran load tests yesterday."
        )
        report_valid = audit_document(valid_load_bearing, profile_name="rfc")
        claudism_violations = [
            v for v in report_valid.violations if v.rule == "Claudism (Contextual)"
        ]
        self.assertEqual(
            len(claudism_violations),
            0,
            "Valid 'load-bearing table' was falsely rejected",
        )

        # Abstract nouns should FAIL
        invalid_load_bearing = (
            "This is a load-bearing assumption in our cognitive model. "
            "We must reconsider our premise."
        )
        report_invalid = audit_document(invalid_load_bearing, profile_name="essay")
        self.assertTrue(
            any(v.rule == "Claudism (Contextual)" for v in report_invalid.violations)
        )

    def test_detects_ai_tells(self):
        tells = [
            ("Let us delve into the compiler passes.", "delve"),
            ("A rich tapestry of microservices unfolds.", "tapestry"),
            (
                "The codebase stands as a testament to engineering excellence.",
                "testament",
            ),
            ("Low latency remains paramount in financial trading.", "paramount"),
            ("We allocate heap buffers parsimoniously.", "parsimoniously"),
            ("The system operates seamlessly across regions.", "seamlessly"),
        ]
        for text, word in tells:
            report = audit_document(text, profile_name="rfc")
            self.assertFalse(report.passed, f"Expected failure for AI tell '{word}'")
            self.assertTrue(
                any(
                    v.rule == "AI Tell" or "Inflation" in v.rule
                    for v in report.violations
                )
            )

    def test_detects_performative_winks_and_sycophancy(self):
        samples = [
            "See what I did there?",
            "Here's the kicker: the database crashed.",
            "Let's dive in and inspect the code.",
            "Buckle up, because things get wild.",
            "You're completely right about this race condition.",
            "That's a great question regarding Raft.",
            "I'd be delighted to help you refactor.",
            "I hope this helps! Happy coding!",
        ]
        for sample in samples:
            report = audit_document(sample, profile_name="chat")
            self.assertFalse(report.passed, f"Expected failure for: {sample}")
            self.assertTrue(
                any(
                    v.rule in ("Performative Wink", "Sycophancy")
                    for v in report.violations
                ),
                f"No wink or sycophancy violation in {report.violations}",
            )

    def test_detects_tailing_clauses(self):
        text = "We added index caching, highlighting our focus on operational latency."
        report = audit_document(text, profile_name="rfc")
        self.assertFalse(report.passed)
        self.assertTrue(any("Tailing" in v.rule for v in report.violations))

    def test_detects_knuth_microsyntax_violations(self):
        # Sentence initial symbol
        text_initial = "$x$ is the primary key in the relation."
        report_initial = audit_document(text_initial, profile_name="paper")
        self.assertTrue(
            any("Initial Symbol" in v.rule for v in report_initial.violations)
        )

        # Adjacent formulas
        text_adjacent = "Consider $S_q$, $q < p$ as defined previously."
        report_adjacent = audit_document(text_adjacent, profile_name="paper")
        self.assertTrue(
            any("Formula Clumping" in v.rule for v in report_adjacent.violations)
        )

        # Logic symbols in prose
        text_logic = "The algorithm terminates ∀ n > 0."
        report_logic = audit_document(text_logic, profile_name="paper")
        self.assertTrue(any("Logic Symbol" in v.rule for v in report_logic.violations))

    def test_inline_code_spans_ignored_by_stage1(self):
        # When a keyword or pattern is inside backticks (code span), Stage 1 must ignore it
        code_prose = (
            "The function `delve()` is defined in the parser module. "
            "We inspect the generated syntax tree. "
            "This tree preserves node hierarchy."
        )
        report = audit_document(code_prose, profile_name="rfc")
        self.assertTrue(
            report.passed,
            f"Expected code span `delve()` to be ignored, got violations: {report.violations}",
        )


class TestStage2ToleranceBands(unittest.TestCase):
    """Verifies Stage 2 tolerance checks across burstiness, nominals, and anchoring."""

    def test_burstiness_evaluation(self):
        # Metronomic uniformity: all sentences exactly 10 words
        uniform_prose = (
            "The primary server receives every single incoming request from clients. "
            "The secondary server replicates every single state change across network. "
            "The tertiary server monitors every single heartbeat signal for failures. "
            "The quaternary server records every single telemetry metric to disk."
        )
        report_uniform = audit_document(uniform_prose, profile_name="essay")
        self.assertLess(report_uniform.metrics.burstiness_cv, 0.20)
        self.assertTrue(any("Burstiness" in v.rule for v in report_uniform.violations))

        # Human dynamic burstiness: mixture of short (4w) and long (25w)
        bursty_prose = (
            "Raft preserves state machine safety. "
            "When the leader receives a client mutation, it appends the entry to the write-ahead log "
            "and dispatches append RPCs to all surviving followers across the cluster. "
            "Progress halts during network partitions. "
            "Safety remains intact."
        )
        report_bursty = audit_document(bursty_prose, profile_name="rfc")
        self.assertGreater(report_bursty.metrics.burstiness_cv, 0.35)

    def test_zombie_nominal_filtering(self):
        # Technical domain nouns should NOT be counted as zombie nominals
        domain_prose = (
            "The configuration file specifies initialization parameters for database replication. "
            "The transaction manager executes the algorithm for encryption and partition management."
        )
        report_domain = audit_document(domain_prose, profile_name="rfc")
        self.assertEqual(report_domain.metrics.zombie_nominals_count, 0)
        self.assertEqual(report_domain.metrics.zombie_nominals_pct, 0.0)

        # Corporate zombie nouns should be flagged
        bureaucratic_prose = (
            "The orchestration of operational resilience across cloud topologies "
            "facilitates the mitigation of architectural vulnerabilities through "
            "contextualization of governance mechanisms and institutional alignment."
        )
        report_bureaucracy = audit_document(bureaucratic_prose, profile_name="essay")
        self.assertGreater(report_bureaucracy.metrics.zombie_nominals_pct, 2.0)

    def test_demonstrative_anchoring_index(self):
        # Unanchored "This"
        unanchored_prose = (
            "This is because the cache expired prematurely. "
            "This means the query planner selected a sequential scan. "
            "We fixed the index definition."
        )
        report_unanchored = audit_document(unanchored_prose, profile_name="essay")
        self.assertEqual(report_unanchored.metrics.sentence_initial_this_anchored, 0)
        self.assertTrue(
            any("Demonstrative" in v.rule for v in report_unanchored.violations)
        )

        # Anchored "This"
        anchored_prose = (
            "This expiration occurs because the TTL was misconfigured. "
            "This sequential scan degraded throughput under peak load. "
            "We fixed the index definition."
        )
        report_anchored = audit_document(anchored_prose, profile_name="essay")
        self.assertEqual(report_anchored.metrics.sentence_initial_this_anchored, 2)
        self.assertFalse(
            any("Demonstrative" in v.rule for v in report_anchored.violations)
        )

    def test_em_dash_saturation(self):
        em_dash_heavy = (
            "Distributed consensus requires coordination—and that changes everything in our design. "
            "The write-ahead log—which persists entries to non-volatile storage—must flush synchronously. "
            "The secondary replicas—which receive messages over the network—acknowledge each commit. "
            "This architecture—tested extensively under simulated partitions—survives leader failure."
        )
        report = audit_document(em_dash_heavy, profile_name="rfc")
        self.assertGreater(report.metrics.em_dashes_per_100w, 0.20)
        self.assertTrue(any("Em-Dash" in v.rule for v in report.violations))


class TestGoldenTransformations(unittest.TestCase):
    """Verifies that golden human master samples pass while synthetic slop fails."""

    def test_distributed_consensus_master_passes(self):
        master_text = (
            "State machine replication requires an immutable sequence of state transitions across all operational nodes. "
            "In an asynchronous network with crash-recovery failures, consensus requires a majority quorum. "
            "Raft does not guarantee zero latency; it guarantees linearizability across surviving honest replicas. "
            "The leader serializes client mutations to an append-only log, persisting entries to non-volatile disk before dispatching RPC acknowledgments. "
            "If the network partitions, progress halts on the minority partition. "
            "This invariant preserves safety. "
            "Liveness resumes once a quorum reconnects."
        )
        report = audit_document(master_text, profile_name="rfc")
        self.assertTrue(
            report.passed, f"Golden master failed with violations: {report.violations}"
        )
        self.assertGreaterEqual(report.metrics.human_voice_index, 80.0)
        self.assertGreaterEqual(report.metrics.technical_precision_index, 80.0)

    def test_kernel_memory_master_passes(self):
        master_text = (
            "The Linux memory management subsystem handles virtual memory allocation through multi-level page tables and buddy allocator algorithms. "
            "When physical RAM is exhausted, the kernel invokes the out-of-memory killer to terminate rogue processes. "
            "Slab allocators cache frequently requested kernel objects, pre-allocating struct instances to eliminate heap fragmentation and reduce lock contention on multiprocessor systems. "
            "TLB shootdowns incur significant cross-core interrupt overhead. "
            "Minimizing page table remapping directly preserves CPU cache locality. "
            "This design bounds lock acquisition latency."
        )
        report = audit_document(master_text, profile_name="rfc")
        self.assertTrue(
            report.passed, f"Kernel master failed with violations: {report.violations}"
        )

    def test_claude_ese_slop_fails_decisively(self):
        slop_text = (
            "The intentional orchestration of distributed consensus across cloud topologies serves as a crucial foundation for resilience. "
            "It is not about raw speed; it is about fostering architectural alignment across failure boundaries. "
            "The deliberate contextualization of quorum protocols facilitates the mitigation of state divergence, highlighting the ongoing need for systemic visibility. "
            "This load-bearing paradigm compounds over time—ensuring that the physics of the cluster remains robust. "
            "Let's sit with this as we unpack the nuanced landscape of replication."
        )
        report = audit_document(slop_text, profile_name="rfc")
        self.assertFalse(report.passed)
        self.assertGreaterEqual(len(report.violations), 4)
        self.assertLess(report.metrics.human_voice_index, 50.0)


class TestCLIExecution(unittest.TestCase):
    """Verifies CLI execution, exit codes, and JSON serialization."""

    def test_cli_exit_code_zero_on_pass(self):
        script_path = (
            Path(__file__).resolve().parent.parent / "scripts" / "quality_gate.py"
        )
        clean_text = (
            "Raft serializes mutations to an append-only log. "
            "The leader flushes entries to disk before responding. "
            "This invariant prevents split-brain scenarios."
        )
        proc = subprocess.run(
            [sys.executable, str(script_path), "--profile", "rfc"],
            input=clean_text,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, f"CLI stderr: {proc.stderr}")

    def test_cli_exit_code_one_on_fail(self):
        script_path = (
            Path(__file__).resolve().parent.parent / "scripts" / "quality_gate.py"
        )
        slop_text = "Let us delve into this rich tapestry of cloud microservices."
        proc = subprocess.run(
            [sys.executable, str(script_path), "--profile", "rfc"],
            input=slop_text,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 1)
        self.assertIn("VIOLATIONS DETECTED", proc.stdout)

    def test_cli_json_output(self):
        script_path = (
            Path(__file__).resolve().parent.parent / "scripts" / "quality_gate.py"
        )
        clean_text = "The leader writes to disk. This write ensures persistence."
        proc = subprocess.run(
            [sys.executable, str(script_path), "--profile", "rfc", "--json"],
            input=clean_text,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(proc.returncode, 0)
        data = json.loads(proc.stdout)
        self.assertIn("metrics", data)
        self.assertIn("violations", data)
        self.assertEqual(data["profile"], "rfc")
        self.assertTrue(data["passed"])


class TestEdgeCasesAndRegression(unittest.TestCase):
    """Verifies adversarial edge cases, math block handling, and syntax fixes."""

    def test_display_math_environments_ignored_as_prose(self):
        sample = (
            "# Complexity Analysis\n"
            "We establish the lower bound for adversary games.\n"
            "$$\n"
            "\\forall x \\in S, \\quad f(x) \\ge 0\n"
            "$$\n"
            "\\begin{equation}\n"
            "E = mc^2 \\implies \\Delta m > 0\n"
            "\\end{equation}\n"
            "This bound holds under all unitary transformations.\n"
        )
        report = audit_document(sample, profile_name="paper")
        stage1_violations = [v for v in report.violations if v.stage == 1]
        self.assertEqual(
            len(stage1_violations),
            0,
            f"Unexpected Stage 1 violations in display math: {stage1_violations}",
        )

    def test_detects_ascii_latex_logic_symbols_in_prose(self):
        bad_prose = "The theorem implies that \\forall x \\in S, the result holds."
        report = audit_document(bad_prose, profile_name="paper")
        self.assertTrue(
            any(
                v.rule == "Knuth Micro-Syntax (Logic Symbol in Prose)"
                for v in report.violations
            )
        )

    def test_detects_knuth_initial_formulas_with_exponents_and_subscripts(self):
        bad_power = "$x^n - a$ has n distinct zeroes in the complex plane."
        report_power = audit_document(bad_power, profile_name="paper")
        self.assertTrue(
            any("Initial Symbol" in v.rule for v in report_power.violations)
        )

        bad_asymptotic = "$O(N \\log N)$ is the upper bound on comparison sorts."
        report_asymp = audit_document(bad_asymptotic, profile_name="paper")
        self.assertTrue(
            any("Initial Symbol" in v.rule for v in report_asymp.violations)
        )

    def test_detects_knuth_initial_code_tokens_with_camelcase_and_scopes(self):
        bad_camel = "`CachePool` handles all active database connections."
        report_camel = audit_document(bad_camel, profile_name="rfc")
        self.assertTrue(
            any("Initial Symbol" in v.rule for v in report_camel.violations)
        )

        bad_scope = "`ThreadPool::init()` starts background worker threads."
        report_scope = audit_document(bad_scope, profile_name="rfc")
        self.assertTrue(
            any("Initial Symbol" in v.rule for v in report_scope.violations)
        )

    def test_detects_knuth_initial_symbol_mid_paragraph(self):
        bad_mid = "We establish the bound. $x$ denotes the parameter vector."
        report_mid = audit_document(bad_mid, profile_name="paper")
        self.assertTrue(any("Initial Symbol" in v.rule for v in report_mid.violations))

    def test_detects_space_separated_adjacent_formulas(self):
        bad_adj = "We multiply $f(x)$ $g(x)$ together to obtain the product."
        report_adj = audit_document(bad_adj, profile_name="paper")
        self.assertTrue(
            any("Formula Clumping" in v.rule for v in report_adj.violations)
        )

    def test_detects_plural_zombie_nominals(self):
        bad_nominals = (
            "The orchestrations and operationalizations of these contextualizations "
            "facilitate institutional alignments across departments."
        )
        report = audit_document(bad_nominals, profile_name="essay")
        self.assertGreater(report.metrics.zombie_nominals_count, 1)
        self.assertTrue(any("Zombie Nominals" in v.rule for v in report.violations))

    def test_recognizes_plural_domain_nouns_as_valid(self):
        valid_domain = (
            "The configurations specify transactions and allocations across partitions. "
            "These specifications ensure deterministic mutations."
        )
        report = audit_document(valid_domain, profile_name="rfc")
        self.assertEqual(report.metrics.zombie_nominals_count, 0)

    def test_recognizes_mathematical_and_systems_primitives(self):
        math_text = (
            "We establish the inequality for compact sets. "
            "This continuity preserves convexity and ensures reliability."
        )
        report = audit_document(math_text, profile_name="paper")
        self.assertEqual(report.metrics.zombie_nominals_count, 0)

    def test_demonstrative_anchoring_unanchored_verbs(self):
        unanchored = (
            "This does not guarantee linearizability. "
            "This ensures the system deadlocks under partition. "
            "This provides zero benefit to the caller."
        )
        report = audit_document(unanchored, profile_name="essay")
        self.assertEqual(report.metrics.sentence_initial_this_anchored, 0)
        self.assertEqual(report.metrics.demonstrative_anchoring_index, 0.0)
        self.assertTrue(any("Demonstrative" in v.rule for v in report.violations))

    def test_contrastive_reframes_with_contractions_and_connectors(self):
        reframe_text = (
            "Writing code is not about typing fast; it's about solving problems."
        )
        report = audit_document(reframe_text, profile_name="essay")
        self.assertGreaterEqual(report.metrics.contrastive_reframes_count, 1)
        self.assertTrue(
            any("Contrastive Strawman" in v.rule for v in report.violations)
        )

    def test_contrastive_reframe_semicolon_and_ornamentation(self):
        sample = (
            "These terms are not decorative ornamentation; they are compression tools."
        )
        report = audit_document(sample, profile_name="essay")
        self.assertGreaterEqual(report.metrics.contrastive_reframes_count, 1)
        self.assertTrue(
            any("Contrastive Strawman" in v.rule for v in report.violations)
        )

    def test_domain_laundry_list_detected(self):
        sample = "In computing, systems architecture, mathematics, and engineering, counters prevent replay."
        report = audit_document(sample, profile_name="essay")
        self.assertFalse(report.passed)
        self.assertTrue(any("Domain Laundry List" in v.rule for v in report.violations))

    def test_pseudo_intellectual_tell_detected(self):
        sample = "These primitives act as formal axiomatic compression operators in our system."
        report = audit_document(sample, profile_name="essay")
        self.assertFalse(report.passed)
        self.assertTrue(
            any("Pseudo-Intellectual" in v.message for v in report.violations)
        )

    def test_compute_anchor_lag_without_header(self):
        lines = [
            "This introductory text explains the client setup in detail.",
            "It has twelve words in total before the code block.",
            "```python",
            "x = 1",
            "```",
        ]
        lag = compute_anchor_lag(lines)
        self.assertIsNotNone(lag)
        self.assertGreater(lag, 0)

    def test_ai_tell_inflections(self):
        inflections = [
            ("We are delving into the kernel sources.", "delve"),
            ("The system provides seamless integration.", "seamless"),
            ("This architecture is a testament to disciplined design.", "testament"),
        ]
        for text, word in inflections:
            report = audit_document(text, profile_name="rfc")
            self.assertFalse(
                report.passed, f"Expected failure for inflected tell: {word}"
            )

    def test_standalone_sycophancy(self):
        sycophancies = [
            "Great question! We need to inspect the mutex.",
            "Good catch! The socket timeout was omitted.",
            "Certainly, here is the corrected implementation.",
        ]
        for text in sycophancies:
            report = audit_document(text, profile_name="chat")
            self.assertFalse(report.passed, f"Expected failure for sycophancy: {text}")
            self.assertTrue(any(v.rule == "Sycophancy" for v in report.violations))

    def test_commonmark_nested_code_fences_excluded_from_prose(self):
        nested = (
            "# Guide\n"
            "This is prose introducing a nested code example.\n"
            "````markdown\n"
            "### Example\n"
            "```python\n"
            "def run_cache():\n"
            "    return True\n"
            "```\n"
            "````\n"
            "This is following prose after the nested code block.\n"
        )
        _, prose, _ = split_into_lines_and_prose(nested)
        self.assertNotIn("def run_cache():", prose)
        self.assertIn("This is prose introducing a nested code example.", prose)
        self.assertIn("This is following prose after the nested code block.", prose)

    def test_educational_negative_quotes_excluded_from_prose(self):
        doc = (
            "# Anti-Patterns\n"
            "### Banned Examples (Slop)\n"
            '> *"We must sit with this realization as we unpack the nuanced landscape."*\n'
            '- *Bad:* "Delve into the rich tapestry of services."\n'
            "- **Prohibited Openings:**\n"
            '  - *"Certainly! I\'d be glad to help!"*\n'
            "### Authentic Human Master (PASSED)\n"
            "State machine replication preserves linearizability across surviving honest replicas.\n"
            "The leader serializes client mutations to an append-only log.\n"
            "This invariant bounds lock contention."
        )
        report = audit_document(doc, profile_name="rfc")
        self.assertTrue(
            report.passed, f"Expected clean pass, got violations: {report.violations}"
        )

    def test_hyphenated_compound_domain_nouns_not_flagged(self):
        sample = (
            "We maintain high-density telemetry across all nodes. "
            "This single-sentence assertion establishes system safety."
        )
        report = audit_document(sample, profile_name="rfc")
        self.assertEqual(report.metrics.zombie_nominals_count, 0)

    def test_unanchored_action_verbs_detected_in_demonstratives(self):
        unanchored_samples = [
            "This triggers the thread starvation under heavy load.",
            "This initiates a cascade failure across the cluster.",
            "This forces the connection to terminate abruptly.",
        ]
        for s in unanchored_samples:
            report = audit_document(
                s + " This invariant preserves safety.", profile_name="essay"
            )
            self.assertEqual(
                report.metrics.sentence_initial_this_anchored,
                1,
                f"Failed to detect unanchored verb follower in: '{s}'",
            )

    def test_positive_blockquotes_retained_in_prose(self):
        doc = (
            "# RFC Walkthrough\n"
            "### Variant A: AI Slop (REJECTED)\n"
            '> *"We must sit with this realization as we unpack the nuanced landscape."*\n'
            "### Variant B: Authentic Human Master (PASSED)\n"
            '> *"The leader serializes client mutations to an append-only log. '
            'This invariant preserves safety across partitions."*\n'
        )
        _, prose, _ = split_into_lines_and_prose(doc)
        self.assertIn("The leader serializes client mutations", prose)
        self.assertNotIn("We must sit with this realization", prose)

    def test_nested_blockquotes_positive_and_negative(self):
        nested_doc = (
            "# RFC Comparison\n"
            "### Analysis Section\n"
            '>> *Bad:* "We must delve into this rich tapestry of cloud services."\n'
            '>> *Good:* "The leader serializes client mutations to an append-only log."\n'
        )
        _, prose, _ = split_into_lines_and_prose(nested_doc)
        self.assertNotIn("delve", prose)
        self.assertNotIn("tapestry", prose)
        self.assertIn("The leader serializes client mutations", prose)
        self.assertNotIn(">>", prose)

    def test_motion_recognized_as_valid_domain_noun(self):
        text = "Loop-invariant code motion hoists invariant expressions outside loop headers."
        report = audit_document(
            text + " This optimization improves throughput.", profile_name="rfc"
        )
        self.assertEqual(report.metrics.zombie_nominals_count, 0)

    def test_all_repository_documents_pass_assigned_profiles(self):
        doc_configs = [
            ("references/scientific_papers.md", "paper"),
            ("references/technical_systems.md", "rfc"),
            ("references/guides_tutorials.md", "tutorial"),
            ("references/conversational_pairing.md", "chat"),
            ("SKILL.md", "essay"),
            ("references/global_guidance.md", "essay"),
            ("resources/anti_patterns_catalog.md", "essay"),
            ("resources/metric_cheat_sheet.md", "rfc"),
            ("examples/before_after_transformations.md", "essay"),
        ]
        base_dir = Path(__file__).resolve().parent.parent
        for rel_path, profile in doc_configs:
            file_path = base_dir / rel_path
            self.assertTrue(file_path.exists(), f"File not found: {file_path}")
            text = file_path.read_text(encoding="utf-8")
            report = audit_document(text, profile_name=profile)
            self.assertTrue(
                report.passed,
                f"Document failed quality gate: {rel_path} under profile {profile}. Violations: {[v.message for v in report.violations]}",
            )

        # Verify scientific_papers.md passes under both paper and default essay profiles
        report_paper_essay = audit_document(
            (base_dir / "references/scientific_papers.md").read_text(encoding="utf-8"),
            profile_name="essay",
        )
        self.assertTrue(
            report_paper_essay.passed,
            f"scientific_papers.md failed under default essay profile: {[v.message for v in report_paper_essay.violations]}",
        )

    def test_briefing_profile_validation(self):
        sample = (
            "We migrated cache servers to NVMe drives across three regions to eliminate cross-rack round trips. "
            "This change dropped read latency to 12 microseconds. "
            "CPU load decreased by 18 percent during peak traffic. "
            "Failover tests verified zero data loss."
        )
        report = audit_document(sample, profile_name="briefing")
        self.assertTrue(
            report.passed, f"Briefing failed with violations: {report.violations}"
        )


if __name__ == "__main__":
    unittest.main()
