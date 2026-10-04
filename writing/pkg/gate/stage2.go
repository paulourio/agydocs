package gate

import (
	"fmt"
	"math"
	"regexp"
	"strings"
	"unicode"
)

var (
	reZombieSuffix = regexp.MustCompile(`(?i)(?:tions?|ments?|ances?|ences?|ities|ity|izations?|olog(?:y|ies))$`)

	rePrep    = regexp.MustCompile(`(?i)\b(?:of|in|to|for|with|on|at|by|from)\s+[a-z0-9_-]+(?:\s+[a-z0-9_-]+){0,3}`)
	reSubVerb = regexp.MustCompile(`^[A-Z][a-z0-9_-]+\s+(?:(?:of|in|for|with)\s+[a-z0-9_-]+\s+)*([a-z0-9_-]+)\s+(?:is|are|was|were|has|have|had|[a-z]+s)\b`)

	reThisInitial = regexp.MustCompile(`^\s*([Tt]his|[Tt]hese)\b(?:\s+([a-zA-Z0-9_-]+)|([,\.;:—–-]))?`)

	reContrastiveReframe = regexp.MustCompile(`(?i)\b(?:it(?:'s|\s+is)?\s+not(?:\s+(?:just|merely|simply|only|about))?|are\s+not(?:\s+(?:just|merely|simply|only|about))?|is\s+not(?:\s+(?:just|merely|simply|only|about))?|not\s+(?:just|merely|simply|only|about)|does\s+not\s+guarantee|doesn't\s+guarantee)\s+([^.?!;\n]{1,80}?)\s*(?:\b(?:but\s+(?:also|rather|instead)?|rather|instead|it(?:'s|\s+is)\s+about|it\s+guarantees)\b|;\s*(?:they\s+are|it(?:'s|\s+is)\s+about|it\s+is|rather|instead))\s+([^.?!;\n]{1,80}?)(?:[.;\n]|$)`)

	trivialPatterns = []*regexp.Regexp{
		regexp.MustCompile(`(?i)\btyping\b`),
		regexp.MustCompile(`(?i)\bstaring\b`),
		regexp.MustCompile(`(?i)\bsimple\s+(?:matter|task|detail|trick|magic)\b`),
		regexp.MustCompile(`(?i)\bjust\s+(?:about|a\s+matter|an?\s+exercise|a\s+tool)\b`),
		regexp.MustCompile(`(?i)\braw speed\b`),
		regexp.MustCompile(`(?i)\bluck\b`),
		regexp.MustCompile(`(?i)\bmagic\b`),
		regexp.MustCompile(`(?i)\bdrawing boxes\b`),
		regexp.MustCompile(`(?i)\bmemorizing\b`),
		regexp.MustCompile(`(?i)\bwriting lines of code\b`),
		regexp.MustCompile(`(?i)\bdecorative\b`),
		regexp.MustCompile(`(?i)\bornament(?:ation)?\b`),
		regexp.MustCompile(`(?i)\bdecoration\b`),
		regexp.MustCompile(`(?i)\bfancy\b`),
		regexp.MustCompile(`(?i)\bfluff\b`),
	}
)

func round2(val float64) float64 {
	return math.Round(val*100.0) / 100.0
}

func round1(val float64) float64 {
	return math.Round(val*10.0) / 10.0
}

// IsValidDomainNoun checks if a word or its singular form is an accepted domain technical primitive.
func IsValidDomainNoun(word string) bool {
	wLower := strings.ToLower(word)
	if ValidDomainTechnicalNouns[wLower] {
		return true
	}
	if strings.HasSuffix(wLower, "ities") && ValidDomainTechnicalNouns[wLower[:len(wLower)-5]+"ity"] {
		return true
	}
	if strings.HasSuffix(wLower, "s") && ValidDomainTechnicalNouns[wLower[:len(wLower)-1]] {
		return true
	}
	return strings.HasSuffix(wLower, "es") && ValidDomainTechnicalNouns[wLower[:len(wLower)-2]]
}

// IsZombieNominal detects bureaucratic action-obscuring nominalizations in singular and plural forms.
func IsZombieNominal(word string) bool {
	wLower := strings.ToLower(word)
	if strings.Contains(wLower, "_") {
		return false
	}
	if strings.Contains(wLower, "-") {
		parts := strings.Split(wLower, "-")
		return IsZombieNominal(parts[len(parts)-1])
	}
	if len(wLower) < 6 || IsValidDomainNoun(wLower) {
		return false
	}
	return reZombieSuffix.MatchString(wLower)
}

func countColons(cleanedProse string) int {
	count := 0
	n := len(cleanedProse)
	for i := 0; i < n; i++ {
		if cleanedProse[i] == ':' {
			prevIsColon := (i > 0 && cleanedProse[i-1] == ':')
			nextIsColon := (i+1 < n && cleanedProse[i+1] == ':')
			if !prevIsColon && !nextIsColon {
				count++
			}
		}
	}
	return count
}

var reMathDash = regexp.MustCompile(`(?mi)(?:(?:^|\s+)—\s*[A-Za-z]|\b(?:Chapter|Appendix|Section|Part)\s+[A-Za-z0-9.]+\s*—|—\s*(?:\d+[a-z]*\s+ed\.|dc\d+|programming)|4\s*—|—\s*>|[|«]\s*—|—\s*[|»]|—\s*—|\b\d+\s*—\s*\d+\b|\b\d+\s*—|(?:^|[\s=<>(+\-*/\[\]])—\s*(?:\d+|\\[a-zA-Z]+)|[=+\-*/<>≤≥≠]\s*—|—\s*[=+\-*/<>≤≥≠]|[\[\(]\s*—|—\s*[\]\)]|\)\s*—|—\s*[\(\[]|\b[a-zA-Z0-9\x27_]{1,3}\b\s*—\s*\b[a-zA-Z0-9\x27_]{1,3}\b)`)

func countEmDashes(prose string) (int, int) {
	cleanForEm := reMathDash.ReplaceAllString(prose, " - ")
	unicodeEm := strings.Count(cleanForEm, "—")
	asciiEm := 0
	n := len(prose)
	i := 0
	for i < n {
		pos := strings.Index(prose[i:], "--")
		if pos == -1 {
			break
		}
		actualPos := i + pos

		hasLeftSpace := actualPos > 0 && unicode.IsSpace(rune(prose[actualPos-1]))
		hasRightSpace := actualPos+2 < n && unicode.IsSpace(rune(prose[actualPos+2]))

		lp := actualPos - 1
		for lp >= 0 && unicode.IsSpace(rune(prose[lp])) {
			lp--
		}
		rp := actualPos + 2
		for rp < n && unicode.IsSpace(rune(prose[rp])) {
			rp++
		}

		if hasLeftSpace && hasRightSpace {
			asciiEm++
		} else if !hasLeftSpace && !hasRightSpace && lp == actualPos-1 && rp == actualPos+2 {
			lc := rune(prose[lp])
			rc := rune(prose[rp])
			leftOk := unicode.IsLetter(lc) || unicode.IsDigit(lc) || strings.ContainsRune(",;\"'", lc)
			rightOk := unicode.IsLetter(rc) || unicode.IsDigit(rc) || strings.ContainsRune("\"'", rc)
			if leftOk && rightOk {
				asciiEm++
			}
		}
		i = actualPos + 2
	}
	return unicodeEm, asciiEm
}

// AuditStage2ToleranceBands audits Stage 2: Multi-metric tolerance bands (burstiness, overhead, nominals, anchoring).
func AuditStage2ToleranceBands(
	text string,
	prose string,
	sentences []string,
	words []string,
	profile ProfileConfig,
	level Level,
	metrics *QualityMetrics,
	violations *[]Violation,
) {
	addViolation := func(rule string, message string, line *int, snippet string, rec string) {
		sev := GetRuleSeverity(rule, 2, level)
		if sev == SeverityOff {
			return
		}
		*violations = append(*violations, Violation{
			Stage:          2,
			Severity:       sev,
			Rule:           rule,
			Message:        message,
			Line:           line,
			Snippet:        snippet,
			Recommendation: rec,
		})
	}
	metrics.TotalWords = len(words)
	metrics.TotalSentences = len(sentences)

	if metrics.TotalWords == 0 || metrics.TotalSentences == 0 {
		return
	}

	// 1. Burstiness (Sentence Length Coefficient of Variation)
	sentenceLens := make([]int, 0, len(sentences))
	for _, s := range sentences {
		wCount := len(TokenizeWords(s))
		if wCount > 0 {
			sentenceLens = append(sentenceLens, wCount)
		}
	}

	if len(sentenceLens) > 0 {
		var sum float64
		for _, l := range sentenceLens {
			sum += float64(l)
		}
		metrics.MeanSentenceLength = sum / float64(len(sentenceLens))

		if len(sentenceLens) > 1 {
			var variance float64
			for _, l := range sentenceLens {
				diff := float64(l) - metrics.MeanSentenceLength
				variance += diff * diff
			}
			metrics.SentenceLengthStd = math.Sqrt(variance / float64(len(sentenceLens)-1))
		} else {
			metrics.SentenceLengthStd = 0.0
		}

		if metrics.MeanSentenceLength > 0 {
			metrics.BurstinessCV = metrics.SentenceLengthStd / metrics.MeanSentenceLength
		}
	}

	if len(sentences) >= 8 {
		if metrics.BurstinessCV < profile.TargetBurstinessMin {
			addViolation(
				"Low Burstiness (Metronomic Uniformity)",
				fmt.Sprintf("Sentence length CV (%.3f) is below minimum %.2f.", metrics.BurstinessCV, profile.TargetBurstinessMin),
				nil,
				fmt.Sprintf("Mean sentence length: %.1f words (std: %.1f)", metrics.MeanSentenceLength, metrics.SentenceLengthStd),
				"Vary sentence length aggressively. Mix short punchy statements (3-6 words) with compound sentences.",
			)
		} else if metrics.BurstinessCV > profile.TargetBurstinessMax {
			addViolation(
				"Excessive Burstiness (Fragmented / Run-On)",
				fmt.Sprintf("Sentence length CV (%.3f) exceeds maximum %.2f.", metrics.BurstinessCV, profile.TargetBurstinessMax),
				nil,
				fmt.Sprintf("Mean sentence length: %.1f words (std: %.1f)", metrics.MeanSentenceLength, metrics.SentenceLengthStd),
				"Rebalance sentences; break run-on sentences and unify fragmented dependent clauses.",
			)
		}
	}

	// 2. Syntactic Overhead (Subject-Verb Distance & Prepositional Depth)
	svdEstimates := make([]float64, 0, len(sentences))
	ppdMax := 0
	ppdSum := 0
	for _, s := range sentences {
		prepMatches := rePrep.FindAllString(s, -1)
		ppdSum += len(prepMatches)
		if len(prepMatches) > ppdMax {
			ppdMax = len(prepMatches)
		}
		subVerb := reSubVerb.FindString(s)
		if subVerb != "" {
			svdEstimates = append(svdEstimates, float64(len(strings.Fields(subVerb))))
		} else {
			svdEstimates = append(svdEstimates, 2.0)
		}
	}

	meanSVD := 2.0
	if len(svdEstimates) > 0 {
		var sum float64
		for _, v := range svdEstimates {
			sum += v
		}
		meanSVD = sum / float64(len(svdEstimates))
	}
	meanPPD := 0.0
	if len(sentences) > 0 {
		meanPPD = float64(ppdSum) / float64(len(sentences))
	}
	metrics.SyntacticOverhead = round2(0.6*meanSVD + 0.8*meanPPD + 1.0)

	if len(sentences) >= 3 && metrics.SyntacticOverhead > profile.MaxSyntacticOverhead {
		addViolation(
			"Syntactic Memory Overhead (DLT Violation)",
			fmt.Sprintf("Syntactic overhead (%.2f) exceeds profile limit (%.1f).", metrics.SyntacticOverhead, profile.MaxSyntacticOverhead),
			nil,
			fmt.Sprintf("Mean SVD: %.1f, Mean PPD: %.1f (Max PPD: %d)", meanSVD, meanPPD, ppdMax),
			"Shorten distance between grammatical subject and finite verb. Eliminate prepositional chains.",
		)
	}

	// 3. Zombie Nominalizations (excluding valid domain nouns)
	nominals := make([]string, 0)
	for _, w := range words {
		if IsZombieNominal(w) {
			nominals = append(nominals, w)
		}
	}

	metrics.ZombieNominalsCount = len(nominals)
	metrics.ZombieNominalsPct = round2((float64(len(nominals)) / float64(metrics.TotalWords)) * 100.0)

	if metrics.ZombieNominalsCount >= 2 && metrics.ZombieNominalsPct > profile.MaxZombieNominalsPct {
		seen := make(map[string]bool)
		sampleNoms := make([]string, 0, 5)
		for _, w := range nominals {
			if !seen[w] {
				seen[w] = true
				sampleNoms = append(sampleNoms, w)
				if len(sampleNoms) == 5 {
					break
				}
			}
		}
		addViolation(
			"Excessive Zombie Nominals",
			fmt.Sprintf("Zombie nominal density (%.2f%%) exceeds profile limit (%.1f%%). Found: %v", metrics.ZombieNominalsPct, profile.MaxZombieNominalsPct, sampleNoms),
			nil,
			fmt.Sprintf("%d nominals across %d words", len(nominals), metrics.TotalWords),
			"Convert bureaucratic nouns into active verbs and concrete actors.",
		)
	}

	// 4. Em-Dash Overuse & Punctuation Balance
	cleanedProse := reURL.ReplaceAllString(prose, " ")
	cleanedProse = MaskInlineCode(cleanedProse)
	cleanedProse = MaskInlineMath(cleanedProse)
	unicodeEm, asciiEm := countEmDashes(cleanedProse)
	emDashes := unicodeEm + asciiEm
	colons := countColons(cleanedProse)
	semicolons := strings.Count(cleanedProse, ";")

	metrics.EmDashesCount = emDashes
	metrics.ColonsCount = colons
	metrics.SemicolonsCount = semicolons
	metrics.EmDashesPer100w = round2((float64(emDashes) / float64(metrics.TotalWords)) * 100.0)
	metrics.PunctuationBalanceRatio = round2(float64(colons+semicolons) / float64(emDashes+1))

	if emDashes >= 2 && metrics.EmDashesPer100w > profile.MaxEmDashesPer100w {
		addViolation(
			"Em-Dash Saturation",
			fmt.Sprintf("Em-dash rate (%.2f/100w) exceeds limit (%.2f/100w).", metrics.EmDashesPer100w, profile.MaxEmDashesPer100w),
			nil,
			fmt.Sprintf("%d em-dashes found", emDashes),
			"Replace em-dashes with semicolons, parentheses, or periods.",
		)
	}

	if emDashes >= 3 && metrics.PunctuationBalanceRatio < profile.MinPunctuationBalance {
		addViolation(
			"Punctuation Imbalance",
			fmt.Sprintf("Punctuation balance ratio (%.2f) is below minimum (%.1f).", metrics.PunctuationBalanceRatio, profile.MinPunctuationBalance),
			nil,
			fmt.Sprintf("%d colons, %d semicolons vs %d em-dashes", colons, semicolons, emDashes),
			"Meter complex clauses with colons and semicolons rather than breathy em-dashes.",
		)
	}

	// 5. Demonstrative Anchoring Index (DAI)
	thisTotal := 0
	thisAnchored := 0
	for _, s := range sentences {
		m := reThisInitial.FindStringSubmatch(s)
		if len(m) > 1 && m[1] != "" {
			thisTotal++
			follower := m[2]
			punct := m[3]
			if punct != "" {
				// unanchored punctuation immediately follows
			} else if follower != "" && !UnanchoredThisFollowers[strings.ToLower(follower)] {
				thisAnchored++
			}
		}
	}

	metrics.SentenceInitialThisTotal = thisTotal
	metrics.SentenceInitialThisAnchored = thisAnchored
	if thisTotal > 0 {
		metrics.DemonstrativeAnchoringIndex = round2(float64(thisAnchored) / float64(thisTotal))
	} else {
		metrics.DemonstrativeAnchoringIndex = 1.0
	}

	if thisTotal >= 2 && metrics.DemonstrativeAnchoringIndex < profile.MinDemonstrativeAnchoring {
		addViolation(
			"Unanchored Demonstrative Pronouns",
			fmt.Sprintf("Demonstrative Anchoring Index (%.2f) is below target (%.2f).", metrics.DemonstrativeAnchoringIndex, profile.MinDemonstrativeAnchoring),
			nil,
			fmt.Sprintf("%d/%d sentence-initial 'This/These' are anchored to explicit nouns.", thisAnchored, thisTotal),
			"Always attach a concrete governing noun: 'This invariant...', 'This latency...', 'This result...'",
		)
	}

	// 6. Contrastive Reframes Analysis (Information Gain)
	totalReframes := 0
	for _, s := range sentences {
		sClean := reInlineCode.ReplaceAllString(s, " ")
		reframeMatches := reContrastiveReframe.FindAllStringSubmatch(sClean, -1)
		totalReframes += len(reframeMatches)
		for _, m := range reframeMatches {
			if len(m) > 2 {
				// Correlative conjunction check: "not only ... but also ..." is additive, not a contrastive strawman
				lowerM := strings.ToLower(m[0])
				if strings.Contains(lowerM, "not only") && strings.Contains(lowerM, "but also") {
					continue
				}
				xClause := m[1]
				yClause := m[2]
				isTrivial := false
				for _, pat := range trivialPatterns {
					if pat.MatchString(xClause) {
						isTrivial = true
						break
					}
				}
				if isTrivial {
					addViolation(
						"Low-Information Contrastive Strawman",
						"Detected trivial contrastive reframe ('Not X, but Y') with zero information gain.",
						nil,
						fmt.Sprintf("Clause X: '%s' -> Clause Y: '%s'", strings.TrimSpace(xClause), strings.TrimSpace(yClause)),
						"Cut the 'Not X' strawman and state assertion Y directly.",
					)
				}
			}
		}
	}
	metrics.ContrastiveReframesCount = totalReframes

	// 7. Concrete Anchor Lag
	if profile.MaxConcreteAnchorLagWords != nil {
		metrics.ConcreteAnchorLagWords = ComputeAnchorLag(SplitLines(text))
		if metrics.TotalWords >= 150 && metrics.ConcreteAnchorLagWords != nil && *metrics.ConcreteAnchorLagWords > *profile.MaxConcreteAnchorLagWords {
			addViolation(
				"Delayed Concrete Anchor",
				fmt.Sprintf("Concrete anchor lag (%d words) exceeds profile limit (%d words).", *metrics.ConcreteAnchorLagWords, *profile.MaxConcreteAnchorLagWords),
				nil,
				"Preamble length before first code fence or table",
				fmt.Sprintf("Introduce a concrete code example or data schema within the first %d words.", *profile.MaxConcreteAnchorLagWords),
			)
		}
	}
}
