package gate

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// --- TestTextProcessing ---

func TestSplitIntoLinesAndProseStripsCode(t *testing.T) {
	sample := "# Header\n" +
		"This is a prose sentence.\n" +
		"```python\n" +
		"def foo():\n" +
		"    # not prose\n" +
		"    return True\n" +
		"```\n" +
		"This is another prose sentence.\n"

	lines, prose, _ := SplitIntoLinesAndProse(sample)
	if len(lines) != 8 {
		t.Errorf("len(lines) = %d, want 8", len(lines))
	}
	if !strings.Contains(prose, "This is a prose sentence.") {
		t.Errorf("missing first prose sentence in %q", prose)
	}
	if !strings.Contains(prose, "This is another prose sentence.") {
		t.Errorf("missing second prose sentence in %q", prose)
	}
	if strings.Contains(prose, "def foo():") {
		t.Errorf("code fence content was not stripped: %q", prose)
	}
}

func TestExtractSentences(t *testing.T) {
	prose := "Raft guarantees linearizability. The leader writes to disk. Does it survive?"
	sentences := ExtractSentences(prose)
	if len(sentences) != 3 {
		t.Fatalf("len(sentences) = %d, want 3", len(sentences))
	}
	if sentences[0] != "Raft guarantees linearizability." {
		t.Errorf("s[0] = %q", sentences[0])
	}
	if sentences[1] != "The leader writes to disk." {
		t.Errorf("s[1] = %q", sentences[1])
	}
	if sentences[2] != "Does it survive?" {
		t.Errorf("s[2] = %q", sentences[2])
	}
}

func TestComputeAnchorLag(t *testing.T) {
	textLines := []string{
		"# Title",
		"This is introductory text.",
		"It has ten words in total here.",
		"```python",
		"x = 1",
		"```",
	}
	lag := ComputeAnchorLag(textLines)
	if lag == nil {
		t.Fatalf("lag is nil, expected integer")
	}
	if *lag <= 0 || *lag >= 20 {
		t.Errorf("lag = %d, expected between 0 and 20", *lag)
	}
}

// --- TestStage1Invariants ---

func TestDetectsClaudisms(t *testing.T) {
	badTexts := []string{
		"We must sit with this realization before proceeding.",
		"The physics of software dictates that latency increases.",
		"That assumption is doing real work in our thesis.",
		"Here is the honest take on this architecture.",
		"We must analyze the exact grain of the data.",
		"Technical debt compounds over time in this module.",
	}
	for _, text := range badTexts {
		rep, err := AuditDocument(text, "essay")
		if err != nil {
			t.Fatalf("AuditDocument err: %v", err)
		}
		if rep.Passed {
			t.Errorf("Expected failure for: %s", text)
		}
		found := false
		for _, v := range rep.Violations {
			if strings.Contains(v.Rule, "Claudism") {
				found = true
				break
			}
		}
		if !found {
			t.Errorf("Missing Claudism rule in violations for %s: %v", text, rep.Violations)
		}
	}
}

func TestContextualLoadBearing(t *testing.T) {
	validLoadBearing := "The users table is a load-bearing table in our schema. " +
		"Partitioning this table requires careful migration. " +
		"We ran load tests yesterday."
	repValid, err := AuditDocument(validLoadBearing, "rfc")
	if err != nil {
		t.Fatalf("AuditDocument err: %v", err)
	}
	for _, v := range repValid.Violations {
		if v.Rule == "Claudism (Contextual)" {
			t.Errorf("Valid 'load-bearing table' was falsely rejected: %v", v)
		}
	}

	invalidLoadBearing := "This is a load-bearing assumption in our cognitive model. " +
		"We must reconsider our premise."
	repInvalid, err := AuditDocument(invalidLoadBearing, "essay")
	if err != nil {
		t.Fatalf("AuditDocument err: %v", err)
	}
	found := false
	for _, v := range repInvalid.Violations {
		if v.Rule == "Claudism (Contextual)" {
			found = true
			break
		}
	}
	if !found {
		t.Errorf("Expected contextual load-bearing violation for abstract usage")
	}
}

func TestDetectsAITells(t *testing.T) {
	tells := []struct {
		text string
		word string
	}{
		{"Let us delve into the compiler passes.", "delve"},
		{"A rich tapestry of microservices unfolds.", "tapestry"},
		{"The codebase stands as a testament to engineering excellence.", "testament"},
		{"Low latency remains paramount in financial trading.", "paramount"},
		{"We allocate heap buffers parsimoniously.", "parsimoniously"},
		{"The system operates seamlessly across regions.", "seamlessly"},
	}

	for _, tt := range tells {
		rep, err := AuditDocument(tt.text, "rfc")
		if err != nil {
			t.Fatalf("AuditDocument err: %v", err)
		}
		if rep.Passed {
			t.Errorf("Expected failure for AI tell %q", tt.word)
		}
		found := false
		for _, v := range rep.Violations {
			if v.Rule == "AI Tell" || strings.Contains(v.Rule, "Inflation") {
				found = true
				break
			}
		}
		if !found {
			t.Errorf("Missing AI tell violation for %s: %v", tt.word, rep.Violations)
		}
	}
}

func TestDetectsPerformativeWinksAndSycophancy(t *testing.T) {
	samples := []string{
		"See what I did there?",
		"Here's the kicker: the database crashed.",
		"Let's dive in and inspect the code.",
		"Buckle up, because things get wild.",
		"You're completely right about this race condition.",
		"That's a great question regarding Raft.",
		"I'd be delighted to help you refactor.",
		"I hope this helps! Happy coding!",
	}

	for _, sample := range samples {
		rep, err := AuditDocument(sample, "chat")
		if err != nil {
			t.Fatalf("AuditDocument err: %v", err)
		}
		if rep.Passed {
			t.Errorf("Expected failure for: %s", sample)
		}
		found := false
		for _, v := range rep.Violations {
			if v.Rule == "Performative Wink" || v.Rule == "Sycophancy" {
				found = true
				break
			}
		}
		if !found {
			t.Errorf("No wink or sycophancy violation in %v for %s", rep.Violations, sample)
		}
	}
}

func TestDetectsTailingClauses(t *testing.T) {
	text := "We added index caching, highlighting our focus on operational latency."
	rep, err := AuditDocument(text, "rfc")
	if err != nil {
		t.Fatalf("AuditDocument err: %v", err)
	}
	if rep.Passed {
		t.Errorf("Expected failure for tailing clause")
	}
	found := false
	for _, v := range rep.Violations {
		if strings.Contains(v.Rule, "Tailing") {
			found = true
			break
		}
	}
	if !found {
		t.Errorf("Missing tailing clause violation in %v", rep.Violations)
	}
}

func TestDetectsKnuthMicrosyntaxViolations(t *testing.T) {
	// Sentence initial symbol
	textInitial := "$x$ is the primary key in the relation."
	repInitial, err := AuditDocument(textInitial, "paper")
	if err != nil {
		t.Fatalf("AuditDocument err: %v", err)
	}
	foundInitial := false
	for _, v := range repInitial.Violations {
		if strings.Contains(v.Rule, "Initial Symbol") {
			foundInitial = true
			break
		}
	}
	if !foundInitial {
		t.Errorf("Missing Initial Symbol violation in %v", repInitial.Violations)
	}

	// Adjacent formulas
	textAdjacent := "Consider $S_q$, $q < p$ as defined previously."
	repAdjacent, err := AuditDocument(textAdjacent, "paper")
	if err != nil {
		t.Fatalf("AuditDocument err: %v", err)
	}
	foundAdj := false
	for _, v := range repAdjacent.Violations {
		if strings.Contains(v.Rule, "Formula Clumping") {
			foundAdj = true
			break
		}
	}
	if !foundAdj {
		t.Errorf("Missing Formula Clumping violation in %v", repAdjacent.Violations)
	}

	// Logic symbols in prose
	textLogic := "The algorithm terminates ∀ n > 0."
	repLogic, err := AuditDocument(textLogic, "paper")
	if err != nil {
		t.Fatalf("AuditDocument err: %v", err)
	}
	foundLogic := false
	for _, v := range repLogic.Violations {
		if strings.Contains(v.Rule, "Logic Symbol") {
			foundLogic = true
			break
		}
	}
	if !foundLogic {
		t.Errorf("Missing Logic Symbol violation in %v", repLogic.Violations)
	}
}

func TestInlineCodeSpansIgnoredByStage1(t *testing.T) {
	codeProse := "The function `delve()` is defined in the parser module. " +
		"We inspect the generated syntax tree. " +
		"This tree preserves node hierarchy."
	rep, err := AuditDocument(codeProse, "rfc")
	if err != nil {
		t.Fatalf("AuditDocument err: %v", err)
	}
	if !rep.Passed {
		t.Errorf("Expected code span `delve()` to be ignored, got violations: %v", rep.Violations)
	}
}

// --- TestStage2ToleranceBands ---

func TestBurstinessEvaluation(t *testing.T) {
	// Metronomic uniformity: all sentences exactly 10 words
	uniformProse := "The primary server receives every single incoming request from clients. " +
		"The secondary server replicates every single state change across network. " +
		"The tertiary server monitors every single heartbeat signal for failures. " +
		"The quaternary server records every single telemetry metric to disk."
	repUniform, err := AuditDocument(uniformProse, "essay")
	if err != nil {
		t.Fatalf("AuditDocument err: %v", err)
	}
	if repUniform.Metrics.BurstinessCV >= 0.20 {
		t.Errorf("Expected burstiness CV < 0.20, got %.3f", repUniform.Metrics.BurstinessCV)
	}
	foundBurst := false
	for _, v := range repUniform.Violations {
		if strings.Contains(v.Rule, "Burstiness") {
			foundBurst = true
			break
		}
	}
	if !foundBurst {
		t.Errorf("Expected Low Burstiness violation in %v", repUniform.Violations)
	}

	// Human dynamic burstiness: mixture of short (4w) and long (25w)
	burstyProse := "Raft preserves state machine safety. " +
		"When the leader receives a client mutation, it appends the entry to the write-ahead log " +
		"and dispatches append RPCs to all surviving followers across the cluster. " +
		"Progress halts during network partitions. " +
		"Safety remains intact."
	repBursty, err := AuditDocument(burstyProse, "rfc")
	if err != nil {
		t.Fatalf("AuditDocument err: %v", err)
	}
	if repBursty.Metrics.BurstinessCV <= 0.35 {
		t.Errorf("Expected burstiness CV > 0.35, got %.3f", repBursty.Metrics.BurstinessCV)
	}
}

func TestZombieNominalFiltering(t *testing.T) {
	// Technical domain nouns should NOT be counted as zombie nominals
	domainProse := "The configuration file specifies initialization parameters for database replication. " +
		"The transaction manager executes the algorithm for encryption and partition management."
	repDomain, err := AuditDocument(domainProse, "rfc")
	if err != nil {
		t.Fatalf("AuditDocument err: %v", err)
	}
	if repDomain.Metrics.ZombieNominalsCount != 0 {
		t.Errorf("Expected 0 zombie nominals, got %d", repDomain.Metrics.ZombieNominalsCount)
	}
	if repDomain.Metrics.ZombieNominalsPct != 0.0 {
		t.Errorf("Expected 0.0%% zombie nominals, got %.2f%%", repDomain.Metrics.ZombieNominalsPct)
	}

	// Corporate zombie nouns should be flagged
	bureaucraticProse := "The orchestration of operational resilience across cloud topologies " +
		"facilitates the mitigation of architectural vulnerabilities through " +
		"contextualization of governance mechanisms and institutional alignment."
	repBureaucracy, err := AuditDocument(bureaucraticProse, "essay")
	if err != nil {
		t.Fatalf("AuditDocument err: %v", err)
	}
	if repBureaucracy.Metrics.ZombieNominalsPct <= 2.0 {
		t.Errorf("Expected zombie nominals pct > 2.0%%, got %.2f%%", repBureaucracy.Metrics.ZombieNominalsPct)
	}
}

func TestDemonstrativeAnchoringIndex(t *testing.T) {
	// Unanchored "This"
	unanchoredProse := "This is because the cache expired prematurely. " +
		"This means the query planner selected a sequential scan. " +
		"We fixed the index definition."
	repUnanchored, err := AuditDocument(unanchoredProse, "essay")
	if err != nil {
		t.Fatalf("AuditDocument err: %v", err)
	}
	if repUnanchored.Metrics.SentenceInitialThisAnchored != 0 {
		t.Errorf("Expected 0 anchored, got %d", repUnanchored.Metrics.SentenceInitialThisAnchored)
	}
	foundDai := false
	for _, v := range repUnanchored.Violations {
		if strings.Contains(v.Rule, "Demonstrative") {
			foundDai = true
			break
		}
	}
	if !foundDai {
		t.Errorf("Expected Demonstrative violation in %v", repUnanchored.Violations)
	}

	// Anchored "This"
	anchoredProse := "This expiration occurs because the TTL was misconfigured. " +
		"This sequential scan degraded throughput under peak load. " +
		"We fixed the index definition."
	repAnchored, err := AuditDocument(anchoredProse, "essay")
	if err != nil {
		t.Fatalf("AuditDocument err: %v", err)
	}
	if repAnchored.Metrics.SentenceInitialThisAnchored != 2 {
		t.Errorf("Expected 2 anchored, got %d", repAnchored.Metrics.SentenceInitialThisAnchored)
	}
	for _, v := range repAnchored.Violations {
		if strings.Contains(v.Rule, "Demonstrative") {
			t.Errorf("Unexpected Demonstrative violation in %v", v)
		}
	}
}

func TestEmDashSaturation(t *testing.T) {
	emDashHeavy := "Distributed consensus requires coordination—and that changes everything in our design. " +
		"The write-ahead log—which persists entries to non-volatile storage—must flush synchronously. " +
		"The secondary replicas—which receive messages over the network—acknowledge each commit. " +
		"This architecture—tested extensively under simulated partitions—survives leader failure."
	rep, err := AuditDocument(emDashHeavy, "rfc")
	if err != nil {
		t.Fatalf("AuditDocument err: %v", err)
	}
	if rep.Metrics.EmDashesPer100w <= 0.20 {
		t.Errorf("Expected em-dashes per 100w > 0.20, got %.2f", rep.Metrics.EmDashesPer100w)
	}
	foundEm := false
	for _, v := range rep.Violations {
		if strings.Contains(v.Rule, "Em-Dash") {
			foundEm = true
			break
		}
	}
	if !foundEm {
		t.Errorf("Expected Em-Dash violation in %v", rep.Violations)
	}
}

// --- TestGoldenTransformations ---

func TestDistributedConsensusMasterPasses(t *testing.T) {
	masterText := "State machine replication requires an immutable sequence of state transitions across all operational nodes. " +
		"In an asynchronous network with crash-recovery failures, consensus requires a majority quorum. " +
		"Raft does not guarantee zero latency; it guarantees linearizability across surviving honest replicas. " +
		"The leader serializes client mutations to an append-only log, persisting entries to non-volatile disk before dispatching RPC acknowledgments. " +
		"If the network partitions, progress halts on the minority partition. " +
		"This invariant preserves safety. " +
		"Liveness resumes once a quorum reconnects."
	rep, err := AuditDocument(masterText, "rfc")
	if err != nil {
		t.Fatalf("AuditDocument err: %v", err)
	}
	if !rep.Passed {
		t.Errorf("Golden master failed with violations: %v", rep.Violations)
	}
	if rep.Metrics.HumanVoiceIndex < 80.0 {
		t.Errorf("HVI = %.1f, want >= 80.0", rep.Metrics.HumanVoiceIndex)
	}
	if rep.Metrics.TechnicalPrecisionIndex < 80.0 {
		t.Errorf("TPI = %.1f, want >= 80.0", rep.Metrics.TechnicalPrecisionIndex)
	}
}

func TestKernelMemoryMasterPasses(t *testing.T) {
	masterText := "The Linux memory management subsystem handles virtual memory allocation through multi-level page tables and buddy allocator algorithms. " +
		"When physical RAM is exhausted, the kernel invokes the out-of-memory killer to terminate rogue processes. " +
		"Slab allocators cache frequently requested kernel objects, pre-allocating struct instances to eliminate heap fragmentation and reduce lock contention on multiprocessor systems. " +
		"TLB shootdowns incur significant cross-core interrupt overhead. " +
		"Minimizing page table remapping directly preserves CPU cache locality. " +
		"This design bounds lock acquisition latency."
	rep, err := AuditDocument(masterText, "rfc")
	if err != nil {
		t.Fatalf("AuditDocument err: %v", err)
	}
	if !rep.Passed {
		t.Errorf("Kernel master failed with violations: %v", rep.Violations)
	}
}

func TestClaudeEseSlopFailsDecisively(t *testing.T) {
	slopText := "The intentional orchestration of distributed consensus across cloud topologies serves as a crucial foundation for resilience. " +
		"It is not about raw speed; it is about fostering architectural alignment across failure boundaries. " +
		"The deliberate contextualization of quorum protocols facilitates the mitigation of state divergence, highlighting the ongoing need for systemic visibility. " +
		"This load-bearing paradigm compounds over time—ensuring that the physics of the cluster remains robust. " +
		"Let's sit with this as we unpack the nuanced landscape of replication."
	rep, err := AuditDocument(slopText, "rfc")
	if err != nil {
		t.Fatalf("AuditDocument err: %v", err)
	}
	if rep.Passed {
		t.Errorf("Expected slop text to fail")
	}
	if len(rep.Violations) < 4 {
		t.Errorf("Expected >= 4 violations, got %d", len(rep.Violations))
	}
	if rep.Metrics.HumanVoiceIndex >= 50.0 {
		t.Errorf("Expected HVI < 50.0, got %.1f", rep.Metrics.HumanVoiceIndex)
	}
}

// --- TestEdgeCasesAndRegression ---

func TestDisplayMathEnvironmentsIgnoredAsProse(t *testing.T) {
	sample := "# Complexity Analysis\n" +
		"We establish the lower bound for adversary games.\n" +
		"$$\n" +
		"\\forall x \\in S, \\quad f(x) \\ge 0\n" +
		"$$\n" +
		"\\begin{equation}\n" +
		"E = mc^2 \\implies \\Delta m > 0\n" +
		"\\end{equation}\n" +
		"This bound holds under all unitary transformations.\n"

	rep, err := AuditDocument(sample, "paper")
	if err != nil {
		t.Fatalf("AuditDocument err: %v", err)
	}
	stage1Count := 0
	for _, v := range rep.Violations {
		if v.Stage == 1 {
			stage1Count++
		}
	}
	if stage1Count != 0 {
		t.Errorf("Unexpected Stage 1 violations in display math: %v", rep.Violations)
	}
}

func TestDetectsAsciiLatexLogicSymbolsInProse(t *testing.T) {
	badProse := "The theorem implies that \\forall x \\in S, the result holds."
	rep, err := AuditDocument(badProse, "paper")
	if err != nil {
		t.Fatalf("AuditDocument err: %v", err)
	}
	found := false
	for _, v := range rep.Violations {
		if v.Rule == "Knuth Micro-Syntax (Logic Symbol in Prose)" {
			found = true
			break
		}
	}
	if !found {
		t.Errorf("Missing Knuth logic symbol violation in %v", rep.Violations)
	}
}

func TestDetectsKnuthInitialFormulasWithExponentsAndSubscripts(t *testing.T) {
	badPower := "$x^n - a$ has n distinct zeroes in the complex plane."
	repPower, err := AuditDocument(badPower, "paper")
	if err != nil {
		t.Fatalf("AuditDocument err: %v", err)
	}
	foundPower := false
	for _, v := range repPower.Violations {
		if strings.Contains(v.Rule, "Initial Symbol") {
			foundPower = true
			break
		}
	}
	if !foundPower {
		t.Errorf("Missing Initial Symbol in %v", repPower.Violations)
	}

	badAsymptotic := "$O(N \\log N)$ is the upper bound on comparison sorts."
	repAsymp, err := AuditDocument(badAsymptotic, "paper")
	if err != nil {
		t.Fatalf("AuditDocument err: %v", err)
	}
	foundAsymp := false
	for _, v := range repAsymp.Violations {
		if strings.Contains(v.Rule, "Initial Symbol") {
			foundAsymp = true
			break
		}
	}
	if !foundAsymp {
		t.Errorf("Missing Initial Symbol in %v", repAsymp.Violations)
	}
}

func TestDetectsKnuthInitialCodeTokensWithCamelCaseAndScopes(t *testing.T) {
	badCamel := "`CachePool` handles all active database connections."
	repCamel, err := AuditDocument(badCamel, "rfc")
	if err != nil {
		t.Fatalf("AuditDocument err: %v", err)
	}
	foundCamel := false
	for _, v := range repCamel.Violations {
		if strings.Contains(v.Rule, "Initial Symbol") {
			foundCamel = true
			break
		}
	}
	if !foundCamel {
		t.Errorf("Missing Initial Symbol in %v", repCamel.Violations)
	}

	badScope := "`ThreadPool::init()` starts background worker threads."
	repScope, err := AuditDocument(badScope, "rfc")
	if err != nil {
		t.Fatalf("AuditDocument err: %v", err)
	}
	foundScope := false
	for _, v := range repScope.Violations {
		if strings.Contains(v.Rule, "Initial Symbol") {
			foundScope = true
			break
		}
	}
	if !foundScope {
		t.Errorf("Missing Initial Symbol in %v", repScope.Violations)
	}
}

func TestDetectsKnuthInitialSymbolMidParagraph(t *testing.T) {
	badMid := "We establish the bound. $x$ denotes the parameter vector."
	repMid, err := AuditDocument(badMid, "paper")
	if err != nil {
		t.Fatalf("AuditDocument err: %v", err)
	}
	foundMid := false
	for _, v := range repMid.Violations {
		if strings.Contains(v.Rule, "Initial Symbol") {
			foundMid = true
			break
		}
	}
	if !foundMid {
		t.Errorf("Missing Initial Symbol mid-paragraph in %v", repMid.Violations)
	}
}

func TestDetectsSpaceSeparatedAdjacentFormulas(t *testing.T) {
	badAdj := "We multiply $f(x)$ $g(x)$ together to obtain the product."
	repAdj, err := AuditDocument(badAdj, "paper")
	if err != nil {
		t.Fatalf("AuditDocument err: %v", err)
	}
	foundAdj := false
	for _, v := range repAdj.Violations {
		if strings.Contains(v.Rule, "Formula Clumping") {
			foundAdj = true
			break
		}
	}
	if !foundAdj {
		t.Errorf("Missing Formula Clumping in %v", repAdj.Violations)
	}
}

func TestDetectsPluralZombieNominals(t *testing.T) {
	badNominals := "The orchestrations and operationalizations of these contextualizations " +
		"facilitate institutional alignments across departments."
	rep, err := AuditDocument(badNominals, "essay")
	if err != nil {
		t.Fatalf("AuditDocument err: %v", err)
	}
	if rep.Metrics.ZombieNominalsCount <= 1 {
		t.Errorf("Expected zombie nominals count > 1, got %d", rep.Metrics.ZombieNominalsCount)
	}
	found := false
	for _, v := range rep.Violations {
		if strings.Contains(v.Rule, "Zombie Nominals") {
			found = true
			break
		}
	}
	if !found {
		t.Errorf("Expected Zombie Nominals violation in %v", rep.Violations)
	}
}

func TestRecognizesPluralDomainNounsAsValid(t *testing.T) {
	validDomain := "The configurations specify transactions and allocations across partitions. " +
		"These specifications ensure deterministic mutations."
	rep, err := AuditDocument(validDomain, "rfc")
	if err != nil {
		t.Fatalf("AuditDocument err: %v", err)
	}
	if rep.Metrics.ZombieNominalsCount != 0 {
		t.Errorf("Expected 0 zombie nominals, got %d", rep.Metrics.ZombieNominalsCount)
	}
}

func TestRecognizesMathematicalAndSystemsPrimitives(t *testing.T) {
	mathText := "We establish the inequality for compact sets. " +
		"This continuity preserves convexity and ensures reliability."
	rep, err := AuditDocument(mathText, "paper")
	if err != nil {
		t.Fatalf("AuditDocument err: %v", err)
	}
	if rep.Metrics.ZombieNominalsCount != 0 {
		t.Errorf("Expected 0 zombie nominals, got %d", rep.Metrics.ZombieNominalsCount)
	}
}

func TestDemonstrativeAnchoringUnanchoredVerbs(t *testing.T) {
	unanchored := "This does not guarantee linearizability. " +
		"This ensures the system deadlocks under partition. " +
		"This provides zero benefit to the caller."
	rep, err := AuditDocument(unanchored, "essay")
	if err != nil {
		t.Fatalf("AuditDocument err: %v", err)
	}
	if rep.Metrics.SentenceInitialThisAnchored != 0 {
		t.Errorf("Expected 0 anchored, got %d", rep.Metrics.SentenceInitialThisAnchored)
	}
	if rep.Metrics.DemonstrativeAnchoringIndex != 0.0 {
		t.Errorf("Expected DAI 0.0, got %.2f", rep.Metrics.DemonstrativeAnchoringIndex)
	}
	found := false
	for _, v := range rep.Violations {
		if strings.Contains(v.Rule, "Demonstrative") {
			found = true
			break
		}
	}
	if !found {
		t.Errorf("Missing Demonstrative violation in %v", rep.Violations)
	}
}

func TestContrastiveReframesWithContractionsAndConnectors(t *testing.T) {
	reframeText := "Writing code is not about typing fast; it's about solving problems."
	rep, err := AuditDocument(reframeText, "essay")
	if err != nil {
		t.Fatalf("AuditDocument err: %v", err)
	}
	if rep.Metrics.ContrastiveReframesCount < 1 {
		t.Errorf("Expected >= 1 contrastive reframes, got %d", rep.Metrics.ContrastiveReframesCount)
	}
	found := false
	for _, v := range rep.Violations {
		if strings.Contains(v.Rule, "Contrastive Strawman") {
			found = true
			break
		}
	}
	if !found {
		t.Errorf("Missing Contrastive Strawman violation in %v", rep.Violations)
	}
}

func TestContrastiveReframeSemicolonAndOrnamentation(t *testing.T) {
	sample := "These terms are not decorative ornamentation; they are compression tools."
	rep, err := AuditDocument(sample, "essay")
	if err != nil {
		t.Fatalf("AuditDocument err: %v", err)
	}
	if rep.Metrics.ContrastiveReframesCount < 1 {
		t.Errorf("Expected >= 1 contrastive reframes, got %d", rep.Metrics.ContrastiveReframesCount)
	}
	found := false
	for _, v := range rep.Violations {
		if strings.Contains(v.Rule, "Contrastive Strawman") {
			found = true
			break
		}
	}
	if !found {
		t.Errorf("Missing Contrastive Strawman in %v", rep.Violations)
	}
}

func TestDomainLaundryListDetected(t *testing.T) {
	sample := "In computing, systems architecture, mathematics, and engineering, counters prevent replay."
	rep, err := AuditDocument(sample, "essay")
	if err != nil {
		t.Fatalf("AuditDocument err: %v", err)
	}
	if rep.Passed {
		t.Errorf("Expected failure for domain laundry list")
	}
	found := false
	for _, v := range rep.Violations {
		if strings.Contains(v.Rule, "Domain Laundry List") {
			found = true
			break
		}
	}
	if !found {
		t.Errorf("Missing Domain Laundry List violation in %v", rep.Violations)
	}
}

func TestPseudoIntellectualTellDetected(t *testing.T) {
	sample := "These primitives act as formal axiomatic compression operators in our system."
	rep, err := AuditDocument(sample, "essay")
	if err != nil {
		t.Fatalf("AuditDocument err: %v", err)
	}
	if rep.Passed {
		t.Errorf("Expected failure for pseudo-intellectual tell")
	}
	found := false
	for _, v := range rep.Violations {
		if strings.Contains(v.Message, "Pseudo-Intellectual") {
			found = true
			break
		}
	}
	if !found {
		t.Errorf("Missing Pseudo-Intellectual in %v", rep.Violations)
	}
}

func TestComputeAnchorLagWithoutHeader(t *testing.T) {
	lines := []string{
		"This introductory text explains the client setup in detail.",
		"It has twelve words in total before the code block.",
		"```python",
		"x = 1",
		"```",
	}
	lag := ComputeAnchorLag(lines)
	if lag == nil {
		t.Fatalf("Expected non-nil lag")
	}
	if *lag <= 0 {
		t.Errorf("Expected lag > 0, got %d", *lag)
	}
}

func TestAITellInflections(t *testing.T) {
	inflections := []struct {
		text string
		word string
	}{
		{"We are delving into the kernel sources.", "delve"},
		{"The system provides seamless integration.", "seamless"},
		{"This architecture is a testament to disciplined design.", "testament"},
	}
	for _, item := range inflections {
		rep, err := AuditDocument(item.text, "rfc")
		if err != nil {
			t.Fatalf("AuditDocument err: %v", err)
		}
		if rep.Passed {
			t.Errorf("Expected failure for inflected tell: %s", item.word)
		}
	}
}

func TestStandaloneSycophancy(t *testing.T) {
	sycophancies := []string{
		"Great question! We need to inspect the mutex.",
		"Good catch! The socket timeout was omitted.",
		"Certainly, here is the corrected implementation.",
	}
	for _, text := range sycophancies {
		rep, err := AuditDocument(text, "chat")
		if err != nil {
			t.Fatalf("AuditDocument err: %v", err)
		}
		if rep.Passed {
			t.Errorf("Expected failure for sycophancy: %s", text)
		}
		found := false
		for _, v := range rep.Violations {
			if v.Rule == "Sycophancy" {
				found = true
				break
			}
		}
		if !found {
			t.Errorf("Expected Sycophancy rule violation for %s", text)
		}
	}
}

func TestCommonmarkNestedCodeFencesExcludedFromProse(t *testing.T) {
	nested := "# Guide\n" +
		"This is prose introducing a nested code example.\n" +
		"````markdown\n" +
		"### Example\n" +
		"```python\n" +
		"def run_cache():\n" +
		"    return True\n" +
		"```\n" +
		"````\n" +
		"This is following prose after the nested code block.\n"

	_, prose, _ := SplitIntoLinesAndProse(nested)
	if strings.Contains(prose, "def run_cache():") {
		t.Errorf("Nested code fence was not stripped: %s", prose)
	}
	if !strings.Contains(prose, "This is prose introducing a nested code example.") {
		t.Errorf("Missing preceding prose: %s", prose)
	}
	if !strings.Contains(prose, "This is following prose after the nested code block.") {
		t.Errorf("Missing following prose: %s", prose)
	}
}

func TestEducationalNegativeQuotesExcludedFromProse(t *testing.T) {
	doc := "# Anti-Patterns\n" +
		"### Banned Examples (Slop)\n" +
		"> *\"We must sit with this realization as we unpack the nuanced landscape.\"*\n" +
		"- *Bad:* \"Delve into the rich tapestry of services.\"\n" +
		"- **Prohibited Openings:**\n" +
		"  - *\"Certainly! I'd be glad to help!\"*\n" +
		"### Authentic Human Master (PASSED)\n" +
		"State machine replication preserves linearizability across surviving honest replicas.\n" +
		"The leader serializes client mutations to an append-only log.\n" +
		"This invariant bounds lock contention."

	rep, err := AuditDocument(doc, "rfc")
	if err != nil {
		t.Fatalf("AuditDocument err: %v", err)
	}
	if !rep.Passed {
		t.Errorf("Expected clean pass, got violations: %v", rep.Violations)
	}
}

func TestHyphenatedCompoundDomainNounsNotFlagged(t *testing.T) {
	sample := "We maintain high-density telemetry across all nodes. " +
		"This single-sentence assertion establishes system safety."
	rep, err := AuditDocument(sample, "rfc")
	if err != nil {
		t.Fatalf("AuditDocument err: %v", err)
	}
	if rep.Metrics.ZombieNominalsCount != 0 {
		t.Errorf("Expected 0 zombie nominals, got %d", rep.Metrics.ZombieNominalsCount)
	}
}

func TestUnanchoredActionVerbsDetectedInDemonstratives(t *testing.T) {
	unanchoredSamples := []string{
		"This triggers the thread starvation under heavy load.",
		"This initiates a cascade failure across the cluster.",
		"This forces the connection to terminate abruptly.",
	}
	for _, s := range unanchoredSamples {
		rep, err := AuditDocument(s+" This invariant preserves safety.", "essay")
		if err != nil {
			t.Fatalf("AuditDocument err: %v", err)
		}
		if rep.Metrics.SentenceInitialThisAnchored != 1 {
			t.Errorf("Failed to detect unanchored verb follower in %q, got anchored = %d", s, rep.Metrics.SentenceInitialThisAnchored)
		}
	}
}

func TestPositiveBlockquotesRetainedInProse(t *testing.T) {
	doc := "# RFC Walkthrough\n" +
		"### Variant A: AI Slop (REJECTED)\n" +
		"> *\"We must sit with this realization as we unpack the nuanced landscape.\"*\n" +
		"### Variant B: Authentic Human Master (PASSED)\n" +
		"> *\"The leader serializes client mutations to an append-only log. " +
		"This invariant preserves safety across partitions.\"*\n"

	_, prose, _ := SplitIntoLinesAndProse(doc)
	if !strings.Contains(prose, "The leader serializes client mutations") {
		t.Errorf("Expected master blockquote in prose: %s", prose)
	}
	if strings.Contains(prose, "We must sit with this realization") {
		t.Errorf("Expected rejected quote to be excluded: %s", prose)
	}
}

func TestNestedBlockquotesPositiveAndNegative(t *testing.T) {
	nestedDoc := "# RFC Comparison\n" +
		"### Analysis Section\n" +
		">> *Bad:* \"We must delve into this rich tapestry of cloud services.\"\n" +
		">> *Good:* \"The leader serializes client mutations to an append-only log.\"\n"

	_, prose, _ := SplitIntoLinesAndProse(nestedDoc)
	if strings.Contains(prose, "delve") {
		t.Errorf("delve should not be in prose: %s", prose)
	}
	if strings.Contains(prose, "tapestry") {
		t.Errorf("tapestry should not be in prose: %s", prose)
	}
	if !strings.Contains(prose, "The leader serializes client mutations") {
		t.Errorf("Good quote should be retained: %s", prose)
	}
	if strings.Contains(prose, ">>") {
		t.Errorf("Blockquote angle brackets should be stripped: %s", prose)
	}
}

func TestMotionRecognizedAsValidDomainNoun(t *testing.T) {
	text := "Loop-invariant code motion hoists invariant expressions outside loop headers."
	rep, err := AuditDocument(text+" This optimization improves throughput.", "rfc")
	if err != nil {
		t.Fatalf("AuditDocument err: %v", err)
	}
	if rep.Metrics.ZombieNominalsCount != 0 {
		t.Errorf("Expected 0 zombie nominals, got %d", rep.Metrics.ZombieNominalsCount)
	}
}

func TestAllRepositoryDocumentsPassAssignedProfiles(t *testing.T) {
	docConfigs := []struct {
		relPath string
		profile string
	}{
		{"references/scientific_papers.md", "paper"},
		{"references/technical_systems.md", "rfc"},
		{"references/guides_tutorials.md", "tutorial"},
		{"references/conversational_pairing.md", "chat"},
		{"SKILL.md", "essay"},
		{"references/global_guidance.md", "essay"},
		{"resources/anti_patterns_catalog.md", "essay"},
		{"resources/metric_cheat_sheet.md", "rfc"},
		{"examples/before_after_transformations.md", "essay"},
	}

	for _, cfg := range docConfigs {
		path := filepath.Join("../..", cfg.relPath)
		content, err := os.ReadFile(path)
		if err != nil {
			t.Fatalf("Failed to read %s: %v", path, err)
		}
		rep, err := AuditDocument(string(content), cfg.profile)
		if err != nil {
			t.Fatalf("AuditDocument failed for %s: %v", cfg.relPath, err)
		}
		if !rep.Passed {
			t.Errorf("Document failed quality gate: %s under profile %s. Violations: %v", cfg.relPath, cfg.profile, rep.Violations)
		}
	}

	// Verify scientific_papers.md also passes under default essay profile
	pathPaper := filepath.Join("../..", "references/scientific_papers.md")
	contentPaper, err := os.ReadFile(pathPaper)
	if err != nil {
		t.Fatalf("Failed to read %s: %v", pathPaper, err)
	}
	repEssay, err := AuditDocument(string(contentPaper), "essay")
	if err != nil {
		t.Fatalf("AuditDocument failed: %v", err)
	}
	if !repEssay.Passed {
		t.Errorf("scientific_papers.md failed under default essay profile: %v", repEssay.Violations)
	}
}

func TestBriefingProfileValidation(t *testing.T) {
	sample := "We migrated cache servers to NVMe drives across three regions to eliminate cross-rack round trips. " +
		"This change dropped read latency to 12 microseconds. " +
		"CPU load decreased by 18 percent during peak traffic. " +
		"Failover tests verified zero data loss."

	rep, err := AuditDocument(sample, "briefing")
	if err != nil {
		t.Fatalf("AuditDocument err: %v", err)
	}
	if !rep.Passed {
		t.Errorf("Briefing failed with violations: %v", rep.Violations)
	}
}
