package gate

import (
	"fmt"
	"regexp"
	"strings"
	"unicode"
)

var (
	reDomainLaundry        = regexp.MustCompile(`(?i)^\s*In\s+([a-zA-Z\s]{3,25}),\s+([a-zA-Z\s]{3,25}),\s+(?:[a-zA-Z\s]{3,25},\s+)*and\s+([a-zA-Z\s]{3,25}),`)
	reKnuthMath            = regexp.MustCompile(`^(\$[^\$]+\$)(?:\s+|$)`)
	reKnuthCode            = regexp.MustCompile("^(`[^`]+`)(?:\\s+|$)")
	reAdjacentCand         = regexp.MustCompile(`\$[^\$]+\$(?:,\s*|\s+)\$[^\$]+\$`)
	reAdjacentExcl         = regexp.MustCompile(`^(?:\s*,\s*(?:and|or|etc\.)\b|\s+(?:and|or|etc\.)\b|\s*[\)\]\}”"]|\s*,\s*(?:\$|\\dots|\.\.\.|[\x{0370}-\x{03FF}\x{2100}-\x{214F}])|\s+(?:times|in|be|agree)\b|\s*[=><≤≥≠≡∈∉⊆⊇⊂⊃~≈←→↔⇒⇐⇔])`)
	reLogicSymbol          = regexp.MustCompile(`(?i)(?:\\forall|\\exists|\\Rightarrow|\\therefore|\\iff|\\implies)\b|[∀∃⇒∴⇔]`)
	reAsciiLogicInProse    = regexp.MustCompile(`(?i)(?:\\forall|\\exists|\\Rightarrow|\\therefore|\\iff|\\implies)\b`)
	reUnicodeLogicInProse  = regexp.MustCompile(`(?i)(?:[a-z]{3,}\s+[∀∃⇒∴⇔]|[∀∃⇒∴⇔]\s+[a-z]{3,})`)
	reStandaloneDerivation = regexp.MustCompile(`^[=\-<>:\s\p{P}\p{S}⇐⇒⇒∴⇔∀∃]+$`)
	reAlgAssign            = regexp.MustCompile(`(?i)(?:\b(?:set|sets|setting|exchange|exchanging|replace|replacing|put|putting|becomes|is\s+renamed)\b|[←:=])`)
	reExerciseOrStep       = regexp.MustCompile(`^(?:▶\s*)?(?:\*\*)?(?:(?:Law|Theorem|Lemma|Proposition|Corollary|Definition|Case|Rule|Property|Conjecture|Algorithm|Method|Step)\s+[A-Z0-9\.\-]+|[A-Z0-9]+|\d+)\.\s*(?:\*\*)?`)
	reIndexDef             = regexp.MustCompile(`^(?:(?:\$[^\$]+\$|` + "`[^`]+`" + `)\s*[=:]|.+?,\s*\d+(?:-\d+)?$)`)
	reMetaMention          = regexp.MustCompile(`(?i)\b(?:means|denotes?|stands for|symbol|macro|write|written)\s+(?:'[^']+'|"[^"]+"|\\[a-zA-Z]+|[∀∃⇒∴⇔])`)
	rePluralNounGovernor   = regexp.MustCompile(`(?i)\b(?:variables|integers|numbers|sets|elements|assertions|functions|values|powers|digits|letters|indices|constants|strings|symbols|pairs|coefficients|quantities|objects|words|terms|arguments|series|notation|ranges|arcs|vertices|nodes|trees|slots|terminals|inputs|relations|sequences|divisible\s+by|divides|for\s+(?:all|any|each|every|some)(?:\s+fixed)?|specifying|defining|setting|letting|listing|taking|denoting|between|among|connect|connecting|let)\b[^.;:?!)\n]*$`)
	reRelationalOp         = regexp.MustCompile(`[=><≤≥≠≡∈∉⊆⊇⊂⊃~≈←→↔⇒⇐⇔]`)
	reEnglishWordMath      = regexp.MustCompile(`^\$[a-zA-Z]{2,}\$$`)
	reNamedLabel           = regexp.MustCompile(`^\$[A-Z][0-9]+\$$`)
	reSingleFactor         = regexp.MustCompile(`^\$[a-zA-Z]{1,3}(?:_\{?[a-zA-Z0-9]+\}?|\^\{?[a-zA-Z0-9]+\}?)*\$$`)
	reMathOperatorToken    = regexp.MustCompile(`^\$[+\-*/=<>≤≥≠±×·÷/]\$$`)

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

func isInsideParensOrBrackets(s string, start, end int) bool {
	openCount := 0
	inMath := false
	for i := 0; i < start; i++ {
		if s[i] == '$' {
			inMath = !inMath
			continue
		}
		if inMath {
			continue
		}
		if s[i] == '(' || s[i] == '[' || s[i] == '{' {
			openCount++
		} else if s[i] == ')' || s[i] == ']' || s[i] == '}' {
			if openCount > 0 {
				openCount--
			}
		}
	}
	if openCount > 0 {
		inMath = false
		for i := end; i < len(s); i++ {
			if s[i] == '$' {
				inMath = !inMath
				continue
			}
			if inMath {
				continue
			}
			if s[i] == ')' || s[i] == ']' || s[i] == '}' {
				return true
			}
		}
	}
	return false
}

func isAllCapsOpcode(tok string) bool {
	tok = strings.Trim(tok, "`")
	if len(tok) < 2 {
		return false
	}
	for _, r := range tok {
		if !unicode.IsUpper(r) && !unicode.IsDigit(r) && r != '_' && r != '\'' && r != '’' && r != ' ' && r != '-' && r != '(' && r != ')' {
			return false
		}
	}
	return true
}

func isAlgebraicProduct(cand string) bool {
	parts := strings.Fields(cand)
	if len(parts) != 2 {
		return false
	}
	if reMathOperatorToken.MatchString(parts[0]) || reMathOperatorToken.MatchString(parts[1]) {
		return true
	}
	return reSingleFactor.MatchString(parts[0]) && reSingleFactor.MatchString(parts[1])
}

// AuditStage1HardInvariants audits Stage 1: Fast-fail hard invariants (Claudisms, AI tells,
// performative winks, sycophancy, laundry lists, tailing clauses, light verbs, Knuth micro-syntax).
func AuditStage1HardInvariants(
	text string,
	lines []string,
	proseLines []LineInfo,
	level Level,
	profileName string,
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

	var prevLine *LineInfo
	for _, lineInfo := range proseLines {
		isContinuation := false
		if prevLine != nil && lineInfo.Line == prevLine.Line+1 {
			prevTrimmed := strings.TrimSpace(prevLine.Content)
			if !strings.HasSuffix(prevTrimmed, ".") &&
				!strings.HasSuffix(prevTrimmed, "?") &&
				!strings.HasSuffix(prevTrimmed, "!") &&
				!strings.HasSuffix(prevTrimmed, ":") &&
				!strings.HasSuffix(prevTrimmed, ";") &&
				!strings.HasSuffix(prevTrimmed, "---") {
				isContinuation = true
			}
		}

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
		trimmedContent := strings.TrimSpace(lineInfo.Content)
		if (profileName == "" || profileName == "paper" || profileName == "rfc" || profileName == "essay") && !reExerciseOrStep.MatchString(trimmedContent) && !reIndexDef.MatchString(trimmedContent) {
			lineSentences := ExtractSentences(lineInfo.Content)
			for sIdx, s := range lineSentences {
				st := strings.TrimSpace(s)
				if sIdx == 0 {
					if startsWithListOrQuote(lineInfo.Content) {
						continue
					}
					if isContinuation {
						continue
					}
				}
				mMath := reKnuthMath.FindStringSubmatch(st)
				mCode := reKnuthCode.FindStringSubmatch(st)
				sym := ""
				if len(mMath) > 1 {
					if !reEnglishWordMath.MatchString(mMath[1]) && !reNamedLabel.MatchString(mMath[1]) {
						sym = mMath[1]
					}
				} else if len(mCode) > 1 {
					if isAllCapsOpcode(mCode[1]) {
						continue
					}
					if isPureDisplayOrEquation(lineInfo.Content) {
						continue
					}
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
		}

		// 8. Knuth Micro-Syntax: Adjacent formulas without intervening words
		if profileName == "" || profileName == "paper" || profileName == "rfc" || profileName == "essay" {
			adjLocs := reAdjacentCand.FindAllStringIndex(lineInfo.Content, -1)
			for _, loc := range adjLocs {
				cand := lineInfo.Content[loc[0]:loc[1]]
				if !strings.Contains(cand, ",") {
					if isAlgebraicProduct(cand) {
						continue
					}
					if reRelationalOp.MatchString(cand) {
						continue
					}
				}
				if strings.Contains(cand, "...") || strings.Contains(cand, "…") || strings.Contains(cand, `\dots`) {
					continue
				}
				if strings.ContainsAny(cand, "↔⊆∩∪≼") {
					continue
				}
				trailing := lineInfo.Content[loc[1]:]
				if reAdjacentExcl.MatchString(trailing) {
					continue
				}
				if isInsideParensOrBrackets(lineInfo.Content, loc[0], loc[1]) {
					continue
				}
				prefix := strings.TrimSpace(lineInfo.Content[:loc[0]])
				if prefix != "" {
					r := []rune(prefix)
					if reRelationalOp.MatchString(string(r[len(r)-1])) {
						continue
					}
				}
				if reAlgAssign.MatchString(lineInfo.Content[:loc[0]]) {
					continue
				}
				if rePluralNounGovernor.MatchString(lineInfo.Content[:loc[0]]) {
					continue
				}
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
		trimmedClean := strings.TrimSpace(lineClean)
		if (profileName == "" || profileName == "paper" || profileName == "rfc" || profileName == "essay") &&
			!reStandaloneDerivation.MatchString(trimmedClean) && !reIndexDef.MatchString(trimmedClean) && !reMetaMention.MatchString(lineClean) {
			mLogic := ""
			if m := reAsciiLogicInProse.FindString(lineClean); m != "" {
				mLogic = m
			} else if m := reUnicodeLogicInProse.FindString(lineClean); m != "" {
				mLogic = strings.TrimSpace(m)
			}
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

		currentLine := lineInfo
		prevLine = &currentLine
	}
}
