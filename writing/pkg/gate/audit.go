package gate

import (
	"fmt"
	"sort"
	"strings"
)

// AuditDocument executes the complete 3-stage audit on the target text using LevelStandard.
func AuditDocument(text string, profileName string) (*AuditReport, error) {
	return AuditDocumentWithLevel(text, profileName, LevelStandard)
}

// AuditDocumentWithLevel executes the complete 3-stage audit on the target text with the specified strictness level.
func AuditDocumentWithLevel(text string, profileName string, level Level) (*AuditReport, error) {
	if level == "" {
		level = LevelStandard
	}
	profile, exists := Profiles[profileName]
	if !exists {
		keys := make([]string, 0, len(Profiles))
		for k := range Profiles {
			keys = append(keys, k)
		}
		sort.Strings(keys)
		return nil, fmt.Errorf("unknown profile '%s'. Available: %v", profileName, keys)
	}

	lines, prose, proseLines := SplitIntoLinesAndProse(text)
	words := TokenizeWords(prose)
	sentences := ExtractSentences(prose)

	violations := make([]Violation, 0)
	metrics := QualityMetrics{
		HumanVoiceIndex:             100.0,
		TechnicalPrecisionIndex:     100.0,
		DemonstrativeAnchoringIndex: 1.0,
	}

	// Check for zero narrative prose content or raw structured data
	if len(words) == 0 {
		sev := GetRuleSeverity("Zero Prose Content", 0, level)
		violations = append(violations, Violation{
			Rule:           "Zero Prose Content",
			Severity:       sev,
			Message:        "Document contains 0 narrative prose words. The quality gate validates natural language prose in technical Markdown documents; code fences, tables, and equations are excluded.",
			Recommendation: "Ensure narrative prose is present outside code fences (```) and math blocks.",
		})
	} else if isRaw, formatName := DetectRawStructuredData(text); isRaw {
		sev := GetRuleSeverity("Raw Non-Prose Content", 0, level)
		violations = append(violations, Violation{
			Rule:           "Raw Non-Prose Content",
			Severity:       sev,
			Message:        fmt.Sprintf("Input appears to be raw %s rather than Markdown prose.", formatName),
			Recommendation: fmt.Sprintf("Quality gate expects natural language prose in Markdown format. Wrap raw %s in code fences (```%s) or use <!-- gate:off --> escapes.", formatName, strings.ToLower(strings.Split(formatName, "/")[0])),
		})
	}

	AuditStage1HardInvariants(text, lines, proseLines, level, profileName, &violations)
	AuditStage2ToleranceBands(text, prose, sentences, words, profile, level, &metrics, &violations)
	AuditStage3CompositeScoring(profile, level, &metrics, &violations)

	errCount := 0
	warnCount := 0
	infoCount := 0
	for _, v := range violations {
		switch v.Severity {
		case SeverityError:
			errCount++
		case SeverityWarn:
			warnCount++
		case SeverityInfo:
			infoCount++
		}
	}

	return &AuditReport{
		Profile:      profileName,
		Level:        level,
		Passed:       errCount == 0,
		ErrorCount:   errCount,
		WarningCount: warnCount,
		InfoCount:    infoCount,
		Metrics:      metrics,
		Violations:   violations,
	}, nil
}
