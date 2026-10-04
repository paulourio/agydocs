package gate

import (
	"fmt"
	"sort"
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

	AuditStage1HardInvariants(text, lines, proseLines, level, &violations)
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
