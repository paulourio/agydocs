package gate

import (
	"fmt"
	"sort"
)

// AuditDocument executes the complete 3-stage audit on the target text.
func AuditDocument(text string, profileName string) (*AuditReport, error) {
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

	AuditStage1HardInvariants(text, lines, proseLines, &violations)
	AuditStage2ToleranceBands(text, prose, sentences, words, profile, &metrics, &violations)
	AuditStage3CompositeScoring(profile, &metrics, &violations)

	return &AuditReport{
		Profile:    profileName,
		Passed:     len(violations) == 0,
		Metrics:    metrics,
		Violations: violations,
	}, nil
}
