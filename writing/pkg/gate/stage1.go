package gate

import (
	"fmt"
	"regexp"
	"strings"
)

var (
	reDomainLaundry = regexp.MustCompile(`(?i)^\s*In\s+([a-zA-Z\s]{3,25}),\s+([a-zA-Z\s]{3,25}),\s+(?:[a-zA-Z\s]{3,25},\s+)*and\s+([a-zA-Z\s]{3,25}),`)
	reKnuthMath     = regexp.MustCompile(`^(\$[^\$]+\$)(?:\s+|$)`)
	reKnuthCode     = regexp.MustCompile("^(`[^`]+`)(?:\\s+|$)")
	reAdjacentCand  = regexp.MustCompile(`\$[^\$]+\$(?:,\s*|\s+)\$[^\$]+\$`)
	reAdjacentExcl  = regexp.MustCompile(`^(?:\s*,\s*(?:and|or)\b|\s+(?:and|or)\b)`)
	reLogicSymbol   = regexp.MustCompile(`(?i)(?:\\forall|\\exists|\\Rightarrow|\\therefore|\\iff|\\implies)\b|[∀∃⇒∴⇔]`)

	domainKeywords = []string{
		"computing",
		"software",
		"systems",
		"architecture",
		"engineering",
		"mathematics",
		"math",
		"computer science",
		"hardware",
		"networking",
		"data science",
		"machine learning",
		"distributed systems",
		"database systems",
	}

	listPrefixes = []string{"-", "*", "+", "1.", "2.", "3.", "4.", ">", "#", "|"}
)

func startsWithListOrQuote(s string) bool {
	trimmed := strings.TrimSpace(s)
	for _, p := range listPrefixes {
		if strings.HasPrefix(trimmed, p) {
			return true
		}
	}
	return false
}

// AuditStage1HardInvariants audits Stage 1: Fast-fail hard invariants (Claudisms, AI tells,
// performative winks, sycophancy, laundry lists, tailing clauses, light verbs, Knuth micro-syntax).
func AuditStage1HardInvariants(
	text string,
	lines []string,
	proseLines []LineInfo,
	level Level,
	violations *[]Violation,
) {
	addViolation := func(rule string, message string, line *int, snippet string, rec string) {
		sev := GetRuleSeverity(rule, 1, level)
		if sev == SeverityOff {
			return
		}
		*violations = append(*violations, Violation{
			Stage:          1,
			Severity:       sev,
			Rule:           rule,
			Message:        message,
			Line:           line,
			Snippet:        snippet,
			Recommendation: rec,
		})
	}

	for _, lineInfo := range proseLines {
		lineClean := MaskInlineCode(lineInfo.Content)
		lineClean = MaskInlineMath(lineClean)
		lineClean = MaskQuotedMentions(lineClean)
		lineClean = reURL.ReplaceAllString(lineClean, " ")

		// 1. Claudisms
		for _, rule := range Claudisms {
			matches := rule.Pattern.FindAllString(lineClean, -1)
			for _, m := range matches {
				addViolation(
					"Claudism",
					fmt.Sprintf("Detected %s: '%s'", rule.Label, m),
					intPtr(lineInfo.Line),
					strings.TrimSpace(lineInfo.Content),
					rule.Recommendation,
				)
			}
		}

		// Contextual check for 'load-bearing'
		locs := LoadBearingPattern.FindAllStringIndex(lineClean, -1)
		for _, loc := range locs {
			postText := strings.TrimSpace(lineClean[loc[1]:])
			nextWords := TokenizeWords(postText)
			firstNoun := ""
			if len(nextWords) > 0 {
				firstNoun = strings.ToLower(nextWords[0])
			}
			if !AllowedLoadBearingNouns[firstNoun] {
				addViolation(
					"Claudism (Contextual)",
					fmt.Sprintf("Abstract usage of 'load-bearing' before non-physical noun '%s'", firstNoun),
					intPtr(lineInfo.Line),
					strings.TrimSpace(lineInfo.Content),
					"Allow 'load-bearing' only before concrete systems nouns (table, column, partition, service, wire).",
				)
			}
		}

		// 2. Performative Winks
		for _, rule := range PerformativeWinks {
			matches := rule.Pattern.FindAllString(lineClean, -1)
			for _, m := range matches {
				addViolation(
					"Performative Wink",
					fmt.Sprintf("Detected %s: '%s'", rule.Label, m),
					intPtr(lineInfo.Line),
					strings.TrimSpace(lineInfo.Content),
					rule.Recommendation,
				)
			}
		}

		// 3. Sycophantic Flares
		for _, rule := range SycophancyPatterns {
			matches := rule.Pattern.FindAllString(lineClean, -1)
			for _, m := range matches {
				addViolation(
					"Sycophancy",
					fmt.Sprintf("Detected %s: '%s'", rule.Label, m),
					intPtr(lineInfo.Line),
					strings.TrimSpace(lineInfo.Content),
					rule.Recommendation,
				)
			}
		}

		// 4. AI Tells
		for _, rule := range AITells {
			matches := rule.Pattern.FindAllString(lineClean, -1)
			for _, m := range matches {
				addViolation(
					"AI Tell",
					fmt.Sprintf("Detected %s: '%s'", rule.Label, m),
					intPtr(lineInfo.Line),
					strings.TrimSpace(lineInfo.Content),
					rule.Recommendation,
				)
			}
		}

		// 4b. Domain Laundry List Throat-Clearing
		mDomain := reDomainLaundry.FindString(lineClean)
		if mDomain != "" {
			matchedLower := strings.ToLower(mDomain)
			foundDomains := 0
			for _, kw := range domainKeywords {
				if strings.Contains(matchedLower, kw) {
					foundDomains++
				}
			}
			if foundDomains >= 2 {
				addViolation(
					"Domain Laundry List (Throat-Clearing)",
					fmt.Sprintf("Domain laundry list used to manufacture scope: '%s'", strings.TrimSpace(mDomain)),
					intPtr(lineInfo.Line),
					strings.TrimSpace(lineInfo.Content),
					"Cut the domain list; state the technical fact directly in its relevant context.",
				)
			}
		}

		// 5. Tailing Clauses
		for _, rule := range TailingClauses {
			matches := rule.Pattern.FindAllString(lineClean, -1)
			for _, m := range matches {
				addViolation(
					"Tailing Participial Clause",
					fmt.Sprintf("Detected dangling %s: '%s'", rule.Label, m),
					intPtr(lineInfo.Line),
					strings.TrimSpace(lineInfo.Content),
					rule.Recommendation,
				)
			}
		}

		// 6. Light-Verb Nominals
		for _, rule := range LightVerbNominals {
			matches := rule.Pattern.FindAllString(lineClean, -1)
			for _, m := range matches {
				addViolation(
					"Light Verb Nominal",
					fmt.Sprintf("Smothered verb in %s: '%s'", rule.Label, m),
					intPtr(lineInfo.Line),
					strings.TrimSpace(lineInfo.Content),
					rule.Recommendation,
				)
			}
		}

		// 7. Knuth Micro-Syntax: Sentence-initial math/variable/code symbols
		lineSentences := ExtractSentences(lineInfo.Content)
		for sIdx, s := range lineSentences {
			st := strings.TrimSpace(s)
			if sIdx == 0 && startsWithListOrQuote(lineInfo.Content) {
				continue
			}
			mMath := reKnuthMath.FindStringSubmatch(st)
			mCode := reKnuthCode.FindStringSubmatch(st)
			sym := ""
			if len(mMath) > 1 {
				sym = mMath[1]
			} else if len(mCode) > 1 {
				sym = mCode[1]
			}
			if sym != "" {
				snippet := st
				if len(snippet) > 60 {
					snippet = snippet[:60] + "..."
				}
				addViolation(
					"Knuth Micro-Syntax (Initial Symbol)",
					fmt.Sprintf("Sentence begins with raw mathematical symbol or code token: '%s'.", sym),
					intPtr(lineInfo.Line),
					snippet,
					"Prefix with governing noun: 'The variable x...', 'The function `foo()`...'",
				)
			}
		}

		// 8. Knuth Micro-Syntax: Adjacent formulas without intervening words
		adjLocs := reAdjacentCand.FindAllStringIndex(lineInfo.Content, -1)
		for _, loc := range adjLocs {
			trailing := lineInfo.Content[loc[1]:]
			if !reAdjacentExcl.MatchString(trailing) {
				addViolation(
					"Knuth Micro-Syntax (Formula Clumping)",
					fmt.Sprintf("Adjacent mathematical formulas without intervening words: '%s'", lineInfo.Content[loc[0]:loc[1]]),
					intPtr(lineInfo.Line),
					strings.TrimSpace(lineInfo.Content),
					"Separate with English words: 'where q < p', not '$S_q, q < p$'.",
				)
				break
			}
		}

		// 9. Logic symbols in prose text
		mLogic := reLogicSymbol.FindString(lineClean)
		if mLogic != "" {
			addViolation(
				"Knuth Micro-Syntax (Logic Symbol in Prose)",
				fmt.Sprintf("Logic symbol '%s' used directly in running text.", mLogic),
				intPtr(lineInfo.Line),
				strings.TrimSpace(lineInfo.Content),
				"Use English words ('for all', 'there exists', 'implies', 'therefore').",
			)
		}
	}
}
