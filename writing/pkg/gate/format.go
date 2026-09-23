package gate

import (
	"fmt"
	"strings"
)

// FormatTerminalReport formats the audit report for human terminal inspection matching Python's output.
func FormatTerminalReport(report *AuditReport, showFixHints bool, verbose bool) string {
	var lines []string
	statusIcon := "🟢"
	statusText := "PASSED"
	if !report.Passed {
		statusIcon = "🔴"
		statusText = "FAILED"
	}

	lines = append(lines, strings.Repeat("=", 76))
	lines = append(lines, fmt.Sprintf("  NLP QUALITY GATE: %s %s (Profile: %s)", statusIcon, statusText, strings.ToUpper(report.Profile)))
	lines = append(lines, strings.Repeat("=", 76))

	m := report.Metrics
	lines = append(lines, fmt.Sprintf("• Words: %d | Sentences: %d | Mean Sentence Length: %.1fw", m.TotalWords, m.TotalSentences, m.MeanSentenceLength))
	lines = append(lines, fmt.Sprintf("• Burstiness CV: %.3f | Syntactic Overhead: %.2f", m.BurstinessCV, m.SyntacticOverhead))
	lines = append(lines, fmt.Sprintf("• Zombie Nominals: %.2f%% (%d words)", m.ZombieNominalsPct, m.ZombieNominalsCount))
	lines = append(lines, fmt.Sprintf("• Demonstrative Anchoring (DAI): %.2f (%d/%d)", m.DemonstrativeAnchoringIndex, m.SentenceInitialThisAnchored, m.SentenceInitialThisTotal))
	lines = append(lines, fmt.Sprintf("• Em-Dashes: %.2f/100w | Punctuation Balance (PBR): %.2f", m.EmDashesPer100w, m.PunctuationBalanceRatio))
	if m.ConcreteAnchorLagWords != nil {
		lines = append(lines, fmt.Sprintf("• Concrete Anchor Lag: %d words", *m.ConcreteAnchorLagWords))
	}
	lines = append(lines, fmt.Sprintf("• Composite Scores: Human Voice Index (HVI) = %.1f | Technical Precision (TPI) = %.1f", m.HumanVoiceIndex, m.TechnicalPrecisionIndex))
	lines = append(lines, strings.Repeat("-", 76))

	if len(report.Violations) > 0 {
		lines = append(lines, fmt.Sprintf("VIOLATIONS DETECTED (%d):", len(report.Violations)))
		for idx, v := range report.Violations {
			loc := "Document Scope"
			if v.Line != nil {
				loc = fmt.Sprintf("Line %d", *v.Line)
			}
			lines = append(lines, fmt.Sprintf("\n[%d] Stage %d - %s (%s)", idx+1, v.Stage, v.Rule, loc))
			lines = append(lines, fmt.Sprintf("    Message: %s", v.Message))
			if v.Snippet != "" {
				lines = append(lines, fmt.Sprintf("    Context: \"%s\"", v.Snippet))
			}
			if showFixHints && v.Recommendation != "" {
				lines = append(lines, fmt.Sprintf("    💡 Fix:  %s", v.Recommendation))
			}
		}
	} else {
		lines = append(lines, "✨ All Stage 1, Stage 2, and Stage 3 quality gates satisfied cleanly.")
	}

	lines = append(lines, strings.Repeat("=", 76))
	return strings.Join(lines, "\n")
}
