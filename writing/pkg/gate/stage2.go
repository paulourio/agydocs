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

	reContrastiveReframe = regexp.MustCompile(`(?i)\b(?:it(?:'s|\s+is)?\s+not\s+(?:just|merely|simply|only|about)?|are\s+not\s+(?:just|merely|simply|only|about)?|is\s+not\s+(?:just|merely|simply|only|about)?|not\s+(?:just|merely|simply|only|about)|does\s+not\s+guarantee|doesn't\s+guarantee)\b(.*?)\b(?:but\s+(?:also|rather|instead)?|rather|instead|it(?:'s|\s+is)\s+about|it\s+guarantees|;\s*(?:they\s+are|it\s+is|rather|instead))\b(.*?)(?:[.;\n]|$)`)

	trivialPatterns = []*regexp.Regexp{
		regexp.MustCompile(`(?i)\btyping\b`),
		regexp.MustCompile(`(?i)\bstaring\b`),
		regexp.MustCompile(`(?i)\bsimple\b`),
		regexp.MustCompile(`(?i)\bjust\b`),
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
	if strings.Contains(wLower, "-") {
		parts := strings.Split(wLower, "-")
		return IsZombieNominal(parts[len(parts)-1])
	}
	if strings.Contains(wLower, "_") {
		parts := strings.Split(wLower, "_")
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

func countEmDashes(prose string) (int, int) {
	unicodeEm := strings.Count(prose, "—")
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
		} else if lp >= 0 && rp < n {
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
	metrics *QualityMetrics,
	violations *[]Violation,
) {
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

	if len(sentences) >= 4 {
		if metrics.BurstinessCV < profile.TargetBurstinessMin {
			*violations = append(*violations, Violation{
				Stage:          2,
				Rule:           "Low Burstiness (Metronomic Uniformity)",
				Message:        fmt.Sprintf("Sentence length CV (%.3f) is below minimum %.2f.", metrics.BurstinessCV, profile.TargetBurstinessMin),
				Line:           nil,
				Snippet:        fmt.Sprintf("Mean sentence length: %.1f words (std: %.1f)", metrics.MeanSentenceLength, metrics.SentenceLengthStd),
				Recommendation: "Vary sentence length aggressively. Mix short punchy statements (3-6 words) with compound sentences.",
			})
		} else if metrics.BurstinessCV > profile.TargetBurstinessMax {
			*violations = append(*violations, Violation{
				Stage:          2,
				Rule:           "Excessive Burstiness (Fragmented / Run-On)",
				Message:        fmt.Sprintf("Sentence length CV (%.3f) exceeds maximum %.2f.", metrics.BurstinessCV, profile.TargetBurstinessMax),
				Line:           nil,
				Snippet:        fmt.Sprintf("Mean sentence length: %.1f words (std: %.1f)", metrics.MeanSentenceLength, metrics.SentenceLengthStd),
				Recommendation: "Rebalance sentences; break run-on sentences and unify fragmented dependent clauses.",
			})
		}
	}

	// 2. Syntactic Overhead (Subject-Verb Distance & Prepositional Depth)
	svdEstimates := make([]float64, 0, len(sentences))
	ppdMax := 0
	for _, s := range sentences {
		prepMatches := rePrep.FindAllString(s, -1)
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
	cappedPPD := float64(ppdMax)
	if cappedPPD > 6.0 {
		cappedPPD = 6.0
	}
	metrics.SyntacticOverhead = round2(0.6*meanSVD + 0.8*cappedPPD + 1.0)

	if metrics.SyntacticOverhead > profile.MaxSyntacticOverhead && len(sentences) >= 3 {
		*violations = append(*violations, Violation{
			Stage:          2,
			Rule:           "Syntactic Memory Overhead (DLT Violation)",
			Message:        fmt.Sprintf("Syntactic overhead (%.2f) exceeds profile limit (%.1f).", metrics.SyntacticOverhead, profile.MaxSyntacticOverhead),
			Line:           nil,
			Snippet:        fmt.Sprintf("Mean SVD: %.1f, Max PPD: %d", meanSVD, ppdMax),
			Recommendation: "Shorten distance between grammatical subject and finite verb. Eliminate prepositional chains.",
		})
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

	if metrics.ZombieNominalsPct > profile.MaxZombieNominalsPct {
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
		*violations = append(*violations, Violation{
			Stage:          2,
			Rule:           "Excessive Zombie Nominals",
			Message:        fmt.Sprintf("Zombie nominal density (%.2f%%) exceeds profile limit (%.1f%%). Found: %v", metrics.ZombieNominalsPct, profile.MaxZombieNominalsPct, sampleNoms),
			Line:           nil,
			Snippet:        fmt.Sprintf("%d nominals across %d words", len(nominals), metrics.TotalWords),
			Recommendation: "Convert bureaucratic nouns into active verbs and concrete actors.",
		})
	}

	// 4. Em-Dash Overuse & Punctuation Balance
	cleanedProse := reURL.ReplaceAllString(prose, " ")
	cleanedProse = reInlineCode.ReplaceAllString(cleanedProse, " ")
	unicodeEm, asciiEm := countEmDashes(prose)
	emDashes := unicodeEm + asciiEm
	colons := countColons(cleanedProse)
	semicolons := strings.Count(cleanedProse, ";")

	metrics.EmDashesCount = emDashes
	metrics.ColonsCount = colons
	metrics.SemicolonsCount = semicolons
	metrics.EmDashesPer100w = round2((float64(emDashes) / float64(metrics.TotalWords)) * 100.0)
	metrics.PunctuationBalanceRatio = round2(float64(colons+semicolons) / float64(emDashes+1))

	if metrics.EmDashesPer100w > profile.MaxEmDashesPer100w && (metrics.TotalWords >= 50 || emDashes >= 2) {
		*violations = append(*violations, Violation{
			Stage:          2,
			Rule:           "Em-Dash Saturation",
			Message:        fmt.Sprintf("Em-dash rate (%.2f/100w) exceeds limit (%.2f/100w).", metrics.EmDashesPer100w, profile.MaxEmDashesPer100w),
			Line:           nil,
			Snippet:        fmt.Sprintf("%d em-dashes found", emDashes),
			Recommendation: "Replace em-dashes with semicolons, parentheses, or periods.",
		})
	}

	if metrics.PunctuationBalanceRatio < profile.MinPunctuationBalance && emDashes >= 3 {
		*violations = append(*violations, Violation{
			Stage:          2,
			Rule:           "Punctuation Imbalance",
			Message:        fmt.Sprintf("Punctuation balance ratio (%.2f) is below minimum (%.1f).", metrics.PunctuationBalanceRatio, profile.MinPunctuationBalance),
			Line:           nil,
			Snippet:        fmt.Sprintf("%d colons, %d semicolons vs %d em-dashes", colons, semicolons, emDashes),
			Recommendation: "Meter complex clauses with colons and semicolons rather than breathy em-dashes.",
		})
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
		*violations = append(*violations, Violation{
			Stage:          2,
			Rule:           "Unanchored Demonstrative Pronouns",
			Message:        fmt.Sprintf("Demonstrative Anchoring Index (%.2f) is below target (%.2f).", metrics.DemonstrativeAnchoringIndex, profile.MinDemonstrativeAnchoring),
			Line:           nil,
			Snippet:        fmt.Sprintf("%d/%d sentence-initial 'This/These' are anchored to explicit nouns.", thisAnchored, thisTotal),
			Recommendation: "Always attach a concrete governing noun: 'This invariant...', 'This latency...', 'This result...'",
		})
	}

	// 6. Contrastive Reframes Analysis (Information Gain)
	proseClean := reInlineCode.ReplaceAllString(prose, " ")
	reframeMatches := reContrastiveReframe.FindAllStringSubmatch(proseClean, -1)
	metrics.ContrastiveReframesCount = len(reframeMatches)
	for _, m := range reframeMatches {
		if len(m) > 2 {
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
				*violations = append(*violations, Violation{
					Stage:          2,
					Rule:           "Low-Information Contrastive Strawman",
					Message:        "Detected trivial contrastive reframe ('Not X, but Y') with zero information gain.",
					Line:           nil,
					Snippet:        fmt.Sprintf("Clause X: '%s' -> Clause Y: '%s'", strings.TrimSpace(xClause), strings.TrimSpace(yClause)),
					Recommendation: "Cut the 'Not X' strawman and state assertion Y directly.",
				})
			}
		}
	}

	// 7. Concrete Anchor Lag
	if profile.MaxConcreteAnchorLagWords != nil {
		metrics.ConcreteAnchorLagWords = ComputeAnchorLag(SplitLines(text))
		if metrics.ConcreteAnchorLagWords != nil && *metrics.ConcreteAnchorLagWords > *profile.MaxConcreteAnchorLagWords {
			*violations = append(*violations, Violation{
				Stage:          2,
				Rule:           "Delayed Concrete Anchor",
				Message:        fmt.Sprintf("Concrete anchor lag (%d words) exceeds profile limit (%d words).", *metrics.ConcreteAnchorLagWords, *profile.MaxConcreteAnchorLagWords),
				Line:           nil,
				Snippet:        "Preamble length before first code fence or table",
				Recommendation: fmt.Sprintf("Introduce a concrete code example or data schema within the first %d words.", *profile.MaxConcreteAnchorLagWords),
			})
		}
	}
}
