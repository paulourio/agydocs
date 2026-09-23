package gate

import (
	"regexp"
	"strings"
	"unicode"
	"unicode/utf8"
)

var (
	reFence            = regexp.MustCompile("^(`{3,})")
	reMathBegin        = regexp.MustCompile(`^\\begin\{(?:equation|align|gather|multline|displaymath)\*?\}`)
	reMathEnd          = regexp.MustCompile(`^\\end\{(?:equation|align|gather|multline|displaymath)\*?\}`)
	reHead             = regexp.MustCompile(`^(#{1,6})\s+(.*)`)
	reHeadPassed       = regexp.MustCompile(`(?i)\b(?:After|PASSED|Master|Authentic|Positive|Canonical)\b`)
	reHeadNeg          = regexp.MustCompile(`(?i)\b(?:Before|Negative|Banned|REJECTED|Slop|Anti-Pattern|Bad|Defect|Strawman|Infantilized|Prohibited|Bourbaki|Fluff)\b`)
	reBannedList       = regexp.MustCompile(`(?i)^[-*+]?\s*\*\*(?:Prohibited|Banned|Anti-Patterns?|Violation(?:\s+Example)?)[^*:]*[:*]+`)
	reNegBlockquote    = regexp.MustCompile("(?i)^\\s*(?:>\\s*)+(?:[\\*\\\"`])*(?:Bad|Defect|Negative(?:\\s+Example)?|Anti-Pattern|Banned|Strawman|Infantilized|Before|REJECTED)\\b")
	reNegBullet        = regexp.MustCompile(`(?i)^\s*[-*+]?\s*\**\s*(?:Bad|Defect|Negative(?:\s+Example)?|Anti-Pattern|Banned|Strawman[^*:]*|Infantilized|Avoid|Trivial\s+Reframe|Claudisms?\s+Detected|Violations?|Fatal\s+Defect|AI\s+Tells|Tailing\s+Clauses|Quality\s+Gate|Shannon\s+Information\s+Loss|Zombie\s+Nominals?|Human\s+Voice\s+Index|Technical\s+Precision\s+Index|Linguistic\s+Virtues|Dependency\s+Locality|Burstiness|Demonstrative\s+Anchoring|Status|Root\s+Cause|Action|Result)\s*[:*]+\s*`)
	reBannedListItem   = regexp.MustCompile(`^\s*[-*+]?\s*(?:\*["']|["'])`)
	reParenNeg         = regexp.MustCompile(`\(\*.*?\*\)`)
	reBlockquotePrefix = regexp.MustCompile(`^(?:\s*>\s*)+`)
	reBulletPrefix     = regexp.MustCompile(`^\s*[-*+]\s+`)
	reNumberPrefix     = regexp.MustCompile(`^\s*\d+\.\s+`)
	reWord             = regexp.MustCompile(`\b[A-Za-z0-9_-]+\b`)
	reURL              = regexp.MustCompile(`https?://\S+`)
	reInlineCode       = regexp.MustCompile("`[^`]+`")
)

// LineInfo pairs a 1-based source line index with its cleaned narrative prose text.
type LineInfo struct {
	Line    int
	Content string
}

// SplitLines splits a string into lines matching Python's str.splitlines() semantics.
func SplitLines(s string) []string {
	s = strings.ReplaceAll(s, "\r\n", "\n")
	s = strings.ReplaceAll(s, "\r", "\n")
	if strings.HasSuffix(s, "\n") {
		s = s[:len(s)-1]
	}
	if len(s) == 0 {
		return []string{}
	}
	return strings.Split(s, "\n")
}

// SplitIntoLinesAndProse separates raw text into lines and prose blocks, removing code fences,
// math blocks, frontmatter, and tables. Excludes educational negative example quotes,
// rejected variants, and list headers from narrative prose evaluation.
func SplitIntoLinesAndProse(text string) ([]string, string, []LineInfo) {
	lines := SplitLines(text)
	proseLines := make([]LineInfo, 0, len(lines))
	bodyLines := make([]string, 0, len(lines))

	inMathBlock := false
	inFrontmatter := false
	codeFenceLen := 0
	inNegativeContext := false
	inBannedList := false

	for idx1, line := range lines {
		idx := idx1 + 1
		stripped := strings.TrimSpace(line)

		// Handle YAML frontmatter at start of file
		if idx == 1 && stripped == "---" {
			inFrontmatter = true
			continue
		}
		if inFrontmatter {
			if stripped == "---" {
				inFrontmatter = false
			}
			continue
		}

		// CommonMark code fences with backtick counts (including nested inside blockquotes)
		strippedWithoutQuotes := strings.TrimLeft(stripped, "> ")
		mFence := reFence.FindStringSubmatch(strippedWithoutQuotes)
		if len(mFence) > 1 {
			fl := len(mFence[1])
			if codeFenceLen == 0 {
				codeFenceLen = fl
				continue
			} else if fl >= codeFenceLen {
				codeFenceLen = 0
				continue
			}
		}
		if codeFenceLen > 0 {
			continue
		}

		// Handle LaTeX display math blocks ($$ ... $$ and \begin{equation} ... \end{equation})
		if strings.HasPrefix(stripped, "$$") {
			if strings.HasSuffix(stripped, "$$") && len(stripped) > 2 {
				continue
			}
			inMathBlock = !inMathBlock
			continue
		}
		if reMathBegin.MatchString(stripped) {
			inMathBlock = true
			continue
		}
		if reMathEnd.MatchString(stripped) {
			inMathBlock = false
			continue
		}
		if inMathBlock {
			continue
		}

		// Skip horizontal rules
		if stripped == "---" || stripped == "___" || stripped == "***" {
			inNegativeContext = false
			inBannedList = false
			continue
		}

		// Skip markdown table rows
		if strings.HasPrefix(stripped, "|") && strings.HasSuffix(stripped, "|") {
			continue
		}

		// Heading detection
		mHead := reHead.FindStringSubmatch(line)
		if len(mHead) > 2 {
			headHashes := mHead[1]
			headText := strings.TrimSpace(mHead[2])
			if reHeadPassed.MatchString(headText) {
				inNegativeContext = false
			} else if reHeadNeg.MatchString(headText) {
				inNegativeContext = true
			} else if len(headHashes) <= 2 {
				inNegativeContext = false
			}
			inBannedList = false
			continue
		}

		// Check for list heading introducing banned / negative items
		if reBannedList.MatchString(stripped) {
			inBannedList = true
			continue
		} else if (strings.HasPrefix(stripped, "- **") && !reBannedList.MatchString(stripped)) ||
			(!strings.HasPrefix(stripped, "-") && !strings.HasPrefix(stripped, "*") && !strings.HasPrefix(stripped, "+") && !strings.HasPrefix(stripped, " ")) {
			inBannedList = false
		}

		// Educational quote / Negative example detection
		isNegExample := false

		// 1. Blockquotes demonstrating negative examples under negative context or explicit markers
		if strings.HasPrefix(stripped, ">") && (inNegativeContext || reNegBlockquote.MatchString(line)) {
			isNegExample = true
		}

		// 2. Bullet lines explicitly marked as Bad / Defect / Negative Example / Avoid / Strawman or diagnostic metadata
		if reNegBullet.MatchString(line) {
			isNegExample = true
		}

		// 3. Sub-items under banned/prohibited lists quoting bad phrases
		if inBannedList && reBannedListItem.MatchString(line) {
			isNegExample = true
		}

		if isNegExample {
			continue
		}

		// Clean line of parenthetical negative quotes and annotations like (*"..."*) or (*e.g. "..."*)
		cleaned := reParenNeg.ReplaceAllString(line, " ")

		// Strip blockquote prefix (including multi-level nested blockquotes)
		cleaned = reBlockquotePrefix.ReplaceAllString(cleaned, "")

		// Remove list markers
		cleaned = reBulletPrefix.ReplaceAllString(cleaned, "")
		cleaned = reNumberPrefix.ReplaceAllString(cleaned, "")
		if strings.TrimSpace(cleaned) != "" {
			proseLines = append(proseLines, LineInfo{Line: idx, Content: cleaned})
			bodyLines = append(bodyLines, cleaned)
		}
	}

	fullProse := strings.Join(bodyLines, " ")
	return lines, fullProse, proseLines
}

const (
	punctChars  = "\"'”’*_.)"
	termChars   = ".!?"
	followChars = "\"'‘“`$*[(-"
)

// ExtractSentences splits prose into distinct sentences, respecting abbreviations,
// inline math, and markdown formatting.
func ExtractSentences(prose string) []string {
	splits := make([][2]int, 0, 32)
	n := len(prose)
	i := 0

	for i < n {
		r, size := utf8.DecodeRuneInString(prose[i:])
		if unicode.IsSpace(r) {
			start := i
			for i < n {
				rNext, sNext := utf8.DecodeRuneInString(prose[i:])
				if !unicode.IsSpace(rNext) {
					break
				}
				i += sNext
			}
			end := i

			leftOk := false
			if start > 0 {
				r1, _ := utf8.DecodeLastRuneInString(prose[:start])
				if strings.ContainsRune(termChars, r1) {
					leftOk = true
				} else if strings.ContainsRune(punctChars, r1) {
					prefix1 := prose[:start-utf8.RuneLen(r1)]
					if len(prefix1) > 0 {
						r2, _ := utf8.DecodeLastRuneInString(prefix1)
						if strings.ContainsRune(termChars, r2) {
							leftOk = true
						} else if strings.ContainsRune(punctChars, r2) {
							prefix2 := prefix1[:len(prefix1)-utf8.RuneLen(r2)]
							if len(prefix2) > 0 {
								r3, _ := utf8.DecodeLastRuneInString(prefix2)
								if strings.ContainsRune(termChars, r3) {
									leftOk = true
								}
							}
						}
					}
				}
			}

			rightOk := false
			if end < n {
				rf, _ := utf8.DecodeRuneInString(prose[end:])
				if unicode.IsLetter(rf) || unicode.IsDigit(rf) || strings.ContainsRune(followChars, rf) {
					rightOk = true
				}
			}

			if leftOk && rightOk {
				splits = append(splits, [2]int{start, end})
			}
		} else {
			i += size
		}
	}

	parts := make([]string, 0, len(splits)+1)
	lastEnd := 0
	for _, sp := range splits {
		parts = append(parts, prose[lastEnd:sp[0]])
		lastEnd = sp[1]
	}
	parts = append(parts, prose[lastEnd:])

	cleaned := make([]string, 0, len(parts))
	for _, s := range parts {
		st := strings.TrimSpace(s)
		if len(st) > 2 {
			cleaned = append(cleaned, st)
		}
	}
	return cleaned
}

var reWordCandidate = regexp.MustCompile(`[A-Za-z0-9_](?:[A-Za-z0-9_-]*[A-Za-z0-9_])?`)

func isWordRune(r rune) bool {
	return unicode.IsLetter(r) || unicode.IsDigit(r) || r == '_'
}

// TokenizeWords extracts words from text, preserving alphanumeric tokens matching Python's \b[A-Za-z0-9_-]+\b.
func TokenizeWords(text string) []string {
	matches := reWordCandidate.FindAllStringIndex(text, -1)
	if len(matches) == 0 {
		return []string{}
	}
	words := make([]string, 0, len(matches))
	for _, m := range matches {
		start, end := m[0], m[1]
		if start > 0 {
			rBefore, _ := utf8.DecodeLastRuneInString(text[:start])
			if isWordRune(rBefore) {
				continue
			}
		}
		if end < len(text) {
			rAfter, _ := utf8.DecodeRuneInString(text[end:])
			if isWordRune(rAfter) {
				continue
			}
		}
		words = append(words, text[start:end])
	}
	return words
}

// ComputeAnchorLag computes words from start of document or first header until first code block,
// table, or display equation.
func ComputeAnchorLag(lines []string) *int {
	wordCount := 0
	inFrontmatter := false

	for idx1, line := range lines {
		idx := idx1 + 1
		stripped := strings.TrimSpace(line)
		if idx == 1 && stripped == "---" {
			inFrontmatter = true
			continue
		}
		if inFrontmatter {
			if stripped == "---" {
				inFrontmatter = false
			}
			continue
		}
		if strings.HasPrefix(stripped, "#") {
			continue
		}
		if strings.HasPrefix(stripped, "```") {
			return &wordCount
		}
		if strings.HasPrefix(stripped, "|") && strings.HasSuffix(stripped, "|") && strings.Contains(stripped, "-") {
			return &wordCount
		}
		if strings.HasPrefix(stripped, "$$") || reMathBegin.MatchString(stripped) {
			return &wordCount
		}

		words := TokenizeWords(line)
		wordCount += len(words)
	}

	if wordCount > 0 {
		return &wordCount
	}
	return nil
}
