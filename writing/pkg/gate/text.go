package gate

import (
	"encoding/json"
	"regexp"
	"strings"
	"unicode"
	"unicode/utf8"
)

var (
	reFence            = regexp.MustCompile("^(`{3,}|~{3,})")
	reMathBegin        = regexp.MustCompile(`^\\begin\{(?:equation|align|gather|multline|displaymath)\*?\}`)
	reMathEnd          = regexp.MustCompile(`^\\end\{(?:equation|align|gather|multline|displaymath)\*?\}`)
	reHead             = regexp.MustCompile(`^(#{1,6})\s+(.*)`)
	reHeadPassed       = regexp.MustCompile(`(?i)\b(?:After|PASSED|Master|Authentic|Positive|Canonical)\b`)
	reHeadNeg          = regexp.MustCompile(`(?i)\b(?:Before|Negative|Banned|REJECTED|Slop|Anti-Pattern|Bad|Defect|Strawman|Infantilized|Prohibited|Bourbaki|Fluff)\b`)
	reBannedList       = regexp.MustCompile(`(?i)^[-*+]?\s*\*\*(?:Prohibited|Banned|Anti-Patterns?|Violation(?:\s+Example)?)[^*:]*[:*]+`)
	reNegBlockquote    = regexp.MustCompile("(?i)^\\s*(?:>\\s*)+(?:[\\*\\\"`])*(?:Bad|Defect|Negative(?:\\s+Example)?|Anti-Pattern|Banned|Strawman|Infantilized|Before|REJECTED)\\b")
	reNegBullet        = regexp.MustCompile(`(?i)^\s*[-*+]?\s*\**\s*(?:Bad|Defect|Negative(?:\s+Example)?|Anti-Pattern|Banned|Strawman[^*:]*|Infantilized|Avoid|Trivial\s+Reframe|Claudisms?\s+Detected|Violations?|Fatal\s+Defect|AI\s+Tells|Tailing\s+Clauses|Quality\s+Gate|Shannon\s+Information\s+Loss|Zombie\s+Nominals?|Human\s+Voice\s+Index|Technical\s+Precision\s+Index|Linguistic\s+Virtues|Dependency\s+Locality|Burstiness|Demonstrative\s+Anchoring)\s*[:*]+\s*`)
	reBannedListItem   = regexp.MustCompile(`^\s*[-*+]?\s*(?:\*["']|["'])`)
	reParenNeg         = regexp.MustCompile(`\(\*(?:\s*(?:e\.g\.\s*)?["'“\x60].*?["'”\x60]\s*|(?:\s*[-a-zA-Z]{3,}(?:\s+[-a-zA-Z]{3,})*\s*,\s*)+(?:and\s+|or\s+)?[-a-zA-Z]{3,}(?:\s+[-a-zA-Z]{3,})*\s*|\s*[-a-zA-Z]{4,}\s*|\s*(?:-[a-z]+,\s*)+-[a-z]+\s*)\*\)`)
	reBlockquotePrefix = regexp.MustCompile(`^(?:\s*>\s*)+`)
	reBulletPrefix     = regexp.MustCompile(`^\s*[-*+]\s+`)
	reNumberPrefix     = regexp.MustCompile(`^\s*\d+\.\s+`)
	reWord             = regexp.MustCompile(`\b[A-Za-z0-9_-]+\b`)
	reURL              = regexp.MustCompile(`https?://\S+`)
	reInlineCode       = regexp.MustCompile("`[^`]+`")
	reInlineMath       = regexp.MustCompile(`\$[^\$\n]+\$|\\\([^\)\n]+\\\)`)
	reDoubleQuotes     = regexp.MustCompile(`"[^"\n]+"|“[^”\n]+”`)
	reSingleQuotes     = regexp.MustCompile(`(^|[^\p{L}\p{N}])'([^'\n]+)'([^\p{L}\p{N}]|$)`)
	reCurlySingle      = regexp.MustCompile(`‘[^’\n]+’`)
	reGateOff          = regexp.MustCompile(`(?i)<!--\s*gate:off\s*-->`)
	reGateOn           = regexp.MustCompile(`(?i)<!--\s*gate:on\s*-->`)

	rePandocSplitComma       = regexp.MustCompile("([`\\d\\)]|\\b[a-zA-Z0-9_-]+\\b)\\s*\\$,\\$\\s*([`\\d\\(]|\\b[a-zA-Z0-9_-]+\\b)")
	reCodeSpan               = regexp.MustCompile("`[^`]+`")
	reMathSpan               = regexp.MustCompile(`\$[^\$]+\$`)
	reHTMLTag                = regexp.MustCompile(`<!--.*?-->|<[^>]+>`)
	reProseWords             = regexp.MustCompile(`\b[a-zA-Z]{2,}\b`)
	reCatalogLine            = regexp.MustCompile(`(?i)\b(?:Library of Congress|Cataloging-in-Publication|ISBN\s+[\d\-X]+|All rights reserved|Printed in\s+the|First printing|Text printed on|acid-free paper|Copyright\s+©)\b`)
	rePublisherCity          = regexp.MustCompile(`(?i)\b(?:Addison[–\-]Wesley|Longman|Pearson|trademark\s+of|About This eBook|THIRD EDITION|Second Edition|Reading,\s+Massachusetts|Menlo Park|Wokingham|Amsterdam|Sydney|Tokyo|Singapore|Madrid|Paris|San Juan|Milan|Bonn|Capetown|Upper Saddle River|informit\.com|corpsales@|pearsoned|camera-ready|retrieval system|photocopying|recording|QA\d+|dc\d+|CIP\b|Includes\s+bibliographical|Includes\s+index|Bibliography:|Computer\s+science--Mathematics|Mathematics\.)\b`)
	reCatalogCard            = regexp.MustCompile(`(?i)^\s*(?:[A-Z][a-z]+,\s+[A-Z][a-z]+|--\s*\d+[a-z]*\s+ed\.|[0-9IVXLCDM]+\.\s+[A-Za-z]|[IVXLCDM]+\.|\d+\s+p\.|\d+\s+cm\.|Title\.|[\d\s{MABCDEFGH\-}]+$)`)
	reIndexLine              = regexp.MustCompile(`(?i)(?:[,;\s]\s*(?:[ivxlcdm]+|\d+)(?:[–—\-{]\d+)?(?:\s*[.,•*]+)*\s*$|(?:\b|[\$\*])see(?:\s+also)?\b|,\s*$|[^\n:]+:\s*[^\n,]+,\s*\d+|(?:\bTable\s+\d+|\b[A-Za-z0-9_\/\\^°—\s\(\)]+=\s*[\d.]+[+\-]?)|^\s*[√=<γΓδ∆ϵλµπσϕ∑∏\$\x60\\_\-+~#&@\/\d]|\b\d+\.\d+(?:\.\d+)?\.?\s*$)`)
	reAllUpperHeader         = regexp.MustCompile(`^[A-Z0-9\s\(\)\-–—,.:]{4,}$`)
	reTrailingConnect        = regexp.MustCompile(`(?i)(?:\b(?:and|or|to|for|in|of|on|by|at|as|with|between|analogous\s+to|due)\b|[(\[{])\s*$`)
	reIndexAuthor            = regexp.MustCompile(`(?i)^\s*[A-Z][a-z]+(?:,\s+[A-Z][a-z]+|\s+\(=|\s+son\s+of|\s+\([^)]+\))`)
	reNotationRow            = regexp.MustCompile(`(?i)\b(?:arithmetic expression|pointer- valued|set or multiset|string of symbols|value of expression|nth element of|element in row|group of variables|address is P|whose field name is|contents of computer word|address of variable|value of pointer variable|to free storage|node at the top of|preorder predecessor|postorder predecessor|local symbol in MIXAL|Formal symbolism|cot\b|sin\b|cos\b)\b`)
	reTOCLine                = regexp.MustCompile(`^(?:(?:\d+(?:\.\d+)*\s+[^0-9\n]+|\bExercises\b)\s*\d*|\.{3,}\s*\d+|\d+)$`)
	reIndexHeading           = regexp.MustCompile(`(?i)^(?:(?:(?:Appendix\s+[A-Z0-9]+|\d+)\s*[:.]?\s*)?(?:Index|General Index|Symbol Index|Subject Index|Author Index|Index to Notations|Index and Glossary|Appendices\s*(?:&|and)\s*Index|Index to Algorithms and Theorems|Appendices and Index|Glossary|Tables?\s+of\s+Numerical\s+Quantities)|Index)$`)
	reTOCHeading             = regexp.MustCompile(`(?i)^(?:Table\s+of\s+Contents|Brief\s+Contents|Contents)$`)
	reFrontmatterHeading     = regexp.MustCompile(`(?i)^(?:Cover\s*(&|and)?\s*Front\s*Matter|Front\s*Matter|About\s+This\s+eBook)$`)
	reCreditHeading          = regexp.MustCompile(`(?i)^(?:(?:(?:Appendix\s+[A-Z0-9]+|\d+)\s*[:.]?\s*)?(?:Credits?(?:\s+for\s+Exercises)?|Acknowledgments?|Acknowledgements?))$`)
	reEBookHeading           = regexp.MustCompile(`(?i)^About\s+This\s+(?:eBook|Edition|EPUB)$`)
	reSubstantiveHeading     = regexp.MustCompile(`(?i)\b(?:Preface|Foreword|Introduction|Prologue|Contents|Chapter|Section|Appendix|Index)\b`)
	reCIPLine                = regexp.MustCompile(`(?i)(?:^\s*(?:Library of Congress|Cataloging-in-Publication|\d+\s+cm\.|ISBN\b|p\.\s+\d+|Includes\s+index|Bibliography:|CIP\b|QA\d+|\d+--dc\d+|\d+-\d+|[IVXLCDM]+\.|\d+\.\s+[A-Za-z]|Dedicated to\b|[A-Z][a-z]+,\s+[A-Z]|\b(?:Second|Third|First|Fourth)\s+Edition\b|\bFoundation for Computer Science\b|Concrete mathematics|The art of computer programming|--\s*\d+[a-z]*\s+ed\.|Contents:\s*v\.)|--\s*v\.\s*\d|\b[ivx]+,\s*\d+\s*p\b|I\.\s+Title|\bcm\b|\.html\b|Mathematical Sciences Publishers|Internet page\b.*contains|Electronic version by|For sales\b)`)
	rePublisherDisclaimer    = regexp.MustCompile(`(?i)\b(?:expressed or implied warranty|errors or omissions|consequential damages|special sales|bulk purposes|camera-ready|retrieval system|photocopying|recording|prior (?:written )?permission|United States of America|All rights reserved|Printed in\s+the|reproduced|warranty of any kind|marketing focus|corporate and government sales|dedicated to the Type 650|in remembrance of many pleasant evenings|DONALD E\.\s+KNUTH|Stanford University)\b`)
	reSpacedLetters          = regexp.MustCompile(`^(?:[A-Za-z]\s+){3,}[A-Za-z]$`)
	reCreditLine             = regexp.MustCompile(`(?i)(?:^\s*\d+\.\d+|^\s*#?\s*\d{4}|^\s*\[|\[\d|\][.,]?$|\b(?:midterm|final|exam|homework|class\s+notes|guest\s+lecture|personal\s+communication|edition|chapter|section|problem|part|solution|vol\.)\b|\.\*\s*$)`)
	reRosterLine             = regexp.MustCompile(`^\s*[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+(?:,\s*[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)*\s*$`)
	reShortFragment          = regexp.MustCompile(`^\s*(?:Year|Instructor|Teaching Assistant\(s\)|Credits for Exercises|[A-Z])\s*$`)
	rePageNumberHeading      = regexp.MustCompile(`^\d+$`)
	reSmallConnectors        = regexp.MustCompile(`(?i)\b(?:and|or|where|with|for|to|if)\b`)
	reAssignArrow            = regexp.MustCompile(`[←:=≡]`)
	reSpacedEllipsis         = regexp.MustCompile(`(?:\.\s+){2,}\.`)
	rePandocSplitDollarComma = regexp.MustCompile(`\$\s*\$,\s*`)
	reImageRef               = regexp.MustCompile(`\[Eq/Symbol:\s*[^\]]+\]|!\[.*?\]\(.*?\)`)
	reGlossaryDef            = regexp.MustCompile(`(?i)^\*?[A-Za-z0-9\s` + "`" + `\-/_$,.]+\*?:\s+["“'A-Za-z$]`)
	reIndexCont              = regexp.MustCompile(`(?i)\(continued\)`)
	reExerciseCitationStart  = regexp.MustCompile(`^\s*\d+\.\d+\s*$`)
	reEpigraphAttribution    = regexp.MustCompile(`(?i)^\s*(?:—\s*[A-Z]|[A-Z\s]{4,},\s+[A-Za-z\s]+\(\d{4}\))`)
	reEpigraphVerse          = regexp.MustCompile(`(?i)^\s*(?:Some Men pretend|by scouting thro|as if a Traveller|when he had seen|that is ratiocination|Numerical experimentations|to fully understand|We must not|has place only in numbers)`)
	reTerminalPunct          = regexp.MustCompile(`[.!?]["”'’]?$`)
	reCaptionLine            = regexp.MustCompile(`(?i)^\*?The names at the left\b`)
)

func isPureDisplayOrEquation(s string) bool {
	sClean := reCodeSpan.ReplaceAllString(s, "")
	sClean = reMathSpan.ReplaceAllString(sClean, "")
	sClean = reHTMLTag.ReplaceAllString(sClean, "")
	sClean = reImageRef.ReplaceAllString(sClean, "")
	if reAssignArrow.MatchString(s) {
		sClean = reSmallConnectors.ReplaceAllString(sClean, "")
	}
	return !reProseWords.MatchString(sClean)
}

// MaskInlineCode replaces inline code spans with equivalent spaces to preserve offsets.
func MaskInlineCode(s string) string {
	return reInlineCode.ReplaceAllStringFunc(s, func(m string) string {
		return strings.Repeat(" ", len(m))
	})
}

// MaskInlineMath replaces inline math formulas ($...$ and \(...\)) with equivalent spaces.
func MaskInlineMath(s string) string {
	return reInlineMath.ReplaceAllStringFunc(s, func(m string) string {
		return strings.Repeat(" ", len(m))
	})
}

// MaskQuotedMentions replaces double and single quoted spans with spaces to avoid false-positive rule triggers.
func MaskQuotedMentions(s string) string {
	s = reDoubleQuotes.ReplaceAllStringFunc(s, func(m string) string {
		return strings.Repeat(" ", len(m))
	})
	s = reCurlySingle.ReplaceAllStringFunc(s, func(m string) string {
		return strings.Repeat(" ", len(m))
	})
	s = reSingleQuotes.ReplaceAllStringFunc(s, func(m string) string {
		return strings.Repeat(" ", len(m))
	})
	return s
}

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
	inGateOff := false
	codeFenceLen := 0
	var fenceChar byte
	inNegativeContext := false
	inBannedList := false
	prevLineEmpty := true
	inIndentedCode := false
	inIndex := false
	inTOC := false
	inFrontmatterSection := false
	inCreditSection := false
	inEBookSection := false
	inCitationList := false
	inGlossaryDef := false

	for idx1, line := range lines {
		idx := idx1 + 1
		stripped := strings.TrimSpace(line)

		// Handle gate:off and gate:on comments
		if reGateOff.MatchString(stripped) {
			inGateOff = true
			continue
		}
		if reGateOn.MatchString(stripped) {
			inGateOff = false
			continue
		}
		if inGateOff {
			continue
		}

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

		// CommonMark code fences with backtick or tilde counts (including nested inside blockquotes)
		strippedWithoutQuotes := strings.TrimLeft(stripped, "> ")
		mFence := reFence.FindStringSubmatch(strippedWithoutQuotes)
		if len(mFence) > 1 {
			fStr := mFence[1]
			fl := len(fStr)
			fChar := fStr[0]
			if codeFenceLen == 0 {
				codeFenceLen = fl
				fenceChar = fChar
				continue
			} else if fChar == fenceChar && fl >= codeFenceLen {
				codeFenceLen = 0
				fenceChar = 0
				continue
			}
		}
		if codeFenceLen > 0 {
			continue
		}

		// Handle indented code blocks (4 spaces or 1 tab)
		if stripped == "" {
			prevLineEmpty = true
			inIndentedCode = false
			continue
		}
		if (strings.HasPrefix(line, "    ") || strings.HasPrefix(line, "\t")) && (prevLineEmpty || inIndentedCode) {
			if !strings.HasPrefix(stripped, "- ") && !strings.HasPrefix(stripped, "* ") && !strings.HasPrefix(stripped, "+ ") && !strings.HasPrefix(stripped, ">") && !reNumberPrefix.MatchString(stripped) {
				inIndentedCode = true
				continue
			}
		}
		prevLineEmpty = false
		inIndentedCode = false

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
			cleanHead := strings.TrimSpace(reNumberPrefix.ReplaceAllString(headText, ""))
			if rePageNumberHeading.MatchString(cleanHead) {
				continue
			}
			if reEBookHeading.MatchString(cleanHead) {
				inEBookSection = true
				inFrontmatterSection = true
				inIndex = false
				inTOC = false
				inCreditSection = false
				continue
			} else {
				inEBookSection = false
			}
			if reIndexHeading.MatchString(cleanHead) {
				inIndex = true
				inFrontmatterSection = false
				inTOC = false
				inCreditSection = false
			} else if reTOCHeading.MatchString(cleanHead) {
				inTOC = true
				inIndex = false
				inFrontmatterSection = false
				inCreditSection = false
			} else if reFrontmatterHeading.MatchString(cleanHead) {
				inFrontmatterSection = true
				inIndex = false
				inTOC = false
				inCreditSection = false
			} else if reCreditHeading.MatchString(cleanHead) {
				inCreditSection = true
				inCitationList = false
				inIndex = false
				inTOC = false
				inFrontmatterSection = false
			} else if inFrontmatterSection && !reSubstantiveHeading.MatchString(cleanHead) && !reNumberPrefix.MatchString(headText) {
				// Keep inFrontmatterSection if inside book front matter (e.g. title page heading)
			} else {
				inIndex = false
				inTOC = false
				inFrontmatterSection = false
				inCreditSection = false
				inCitationList = false
				inGlossaryDef = false
			}
			continue
		}

		if inEBookSection {
			continue
		}

		// Skip structural cataloging, index, credit, and table-of-contents lines
		if inIndex {
			if reGlossaryDef.MatchString(stripped) {
				inGlossaryDef = true
			}
			if inGlossaryDef {
				if strings.HasSuffix(stripped, ".") || strings.HasSuffix(stripped, ";") {
					inGlossaryDef = false
				}
				continue
			}
			if len(strings.Fields(stripped)) <= 4 ||
				reIndexLine.MatchString(stripped) ||
				reIndexCont.MatchString(stripped) ||
				reEpigraphAttribution.MatchString(stripped) ||
				reEpigraphVerse.MatchString(stripped) ||
				reCaptionLine.MatchString(stripped) ||
				reTOCLine.MatchString(stripped) ||
				reCatalogLine.MatchString(stripped) ||
				reAllUpperHeader.MatchString(stripped) ||
				reTrailingConnect.MatchString(stripped) ||
				reIndexAuthor.MatchString(stripped) ||
				reNotationRow.MatchString(stripped) ||
				strings.HasSuffix(stripped, ":") ||
				(!reTerminalPunct.MatchString(stripped) && len(strings.Fields(stripped)) <= 8) {
				continue
			}
		}
		if inCreditSection {
			if reExerciseCitationStart.MatchString(stripped) {
				inCitationList = true
			}
			if inCitationList {
				continue
			}
			if reCreditLine.MatchString(stripped) || reRosterLine.MatchString(stripped) || reShortFragment.MatchString(stripped) || reIndexLine.MatchString(stripped) || reCatalogLine.MatchString(stripped) || (len(strings.Fields(stripped)) <= 4 && !strings.ContainsAny(stripped, ".!?")) {
				continue
			}
		}
		if inFrontmatterSection {
			if reCatalogLine.MatchString(stripped) || reCatalogCard.MatchString(stripped) || rePublisherCity.MatchString(stripped) || reCIPLine.MatchString(stripped) || rePublisherDisclaimer.MatchString(stripped) || reSpacedLetters.MatchString(stripped) || (len(strings.Fields(stripped)) <= 5 && !strings.ContainsAny(stripped, ".!?")) {
				continue
			}
		}
		if inTOC {
			if reTOCLine.MatchString(stripped) || reIndexLine.MatchString(stripped) || reCatalogLine.MatchString(stripped) {
				continue
			}
		}
		if reCatalogLine.MatchString(stripped) {
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

		cleaned = reSpacedEllipsis.ReplaceAllString(cleaned, "...")
		cleaned = strings.ReplaceAll(cleaned, "$$,", ",")
		cleaned = strings.ReplaceAll(cleaned, "$$ ,", ",")
		cleaned = strings.ReplaceAll(cleaned, "$,$", ",")
		cleaned = rePandocSplitComma.ReplaceAllString(cleaned, "$1, $2")
		cleaned = rePandocSplitDollarComma.ReplaceAllString(cleaned, ", $")
		cleaned = reImageRef.ReplaceAllString(cleaned, "")
		if isPureDisplayOrEquation(cleaned) || !reProseWords.MatchString(cleaned) {
			continue
		}

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
			var r1 rune
			if start > 0 {
				r1, _ = utf8.DecodeLastRuneInString(prose[:start])
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

			if leftOk {
				trimmedBefore := strings.TrimRight(prose[:start], " \"'”’)]}")
				if strings.HasSuffix(trimmedBefore, "..") || strings.HasSuffix(trimmedBefore, "…") {
					leftOk = false
				}
				if r1 == '!' && len(prose[:start]) > 1 && strings.HasSuffix(strings.TrimSpace(prose[:start-1]), "$") {
					leftOk = false
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

var reAlgoAnchor = regexp.MustCompile(`(?i)(?:^|\s)(?:\*\*)?(?:Algorithm\s+[A-Z0-9]+|[A-Z][0-9]+\.\s*\[)`)

// ComputeAnchorLag computes words from start of document or first header until first code block,
// table, display equation, or formal algorithm environment. Returns nil if no anchor is found.
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
		if strings.HasPrefix(stripped, "$$") || reMathBegin.MatchString(stripped) || reAlgoAnchor.MatchString(stripped) {
			return &wordCount
		}

		words := TokenizeWords(line)
		wordCount += len(words)
	}

	return nil
}

var reMarkdownHeading = regexp.MustCompile(`(?m)^#{1,6}\s+`)

// DetectRawStructuredData checks whether the input text appears to be raw JSON, XML, or HTML
// rather than a Markdown document.
func DetectRawStructuredData(text string) (bool, string) {
	trimmed := strings.TrimSpace(text)
	if trimmed == "" {
		return false, ""
	}
	// Markdown headings explicitly signal markdown documentation
	if reMarkdownHeading.MatchString(trimmed) {
		return false, ""
	}

	// Raw JSON object or array
	if (strings.HasPrefix(trimmed, "{") && strings.HasSuffix(trimmed, "}")) ||
		(strings.HasPrefix(trimmed, "[") && strings.HasSuffix(trimmed, "]")) {
		var js json.RawMessage
		if json.Unmarshal([]byte(trimmed), &js) == nil {
			return true, "JSON"
		}
	}

	// Raw XML or HTML document (excluding markdown HTML comments like <!-- gate:off -->)
	if strings.HasPrefix(trimmed, "<") && !strings.HasPrefix(trimmed, "<!--") {
		if strings.HasPrefix(trimmed, "<?xml") ||
			strings.HasPrefix(trimmed, "<!DOCTYPE") ||
			strings.HasPrefix(trimmed, "<!doctype") ||
			strings.HasPrefix(trimmed, "<html") {
			return true, "XML/HTML"
		}
		if strings.HasSuffix(trimmed, ">") && strings.Contains(trimmed, "</") {
			return true, "XML/HTML"
		}
	}

	return false, ""
}
