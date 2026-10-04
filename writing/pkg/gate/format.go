package gate

import (
	"fmt"
	"strings"
)

// FormatTerminalReport formats the audit report for human terminal inspection matching standard output.
func FormatTerminalReport(report *AuditReport, showFixHints bool, verbose bool) string {
	return FormatReport(report, "full", showFixHints, verbose, 0)
}

// FormatReport formats the audit report as either 'full' or 'compact'.
func FormatReport(report *AuditReport, format string, showFixHints bool, verbose bool, maxViolations int) string {
	if format == "compact" {
		return formatCompactReport(report, maxViolations)
	}
	return formatFullReport(report, showFixHints, verbose, maxViolations)
}

func formatCompactReport(report *AuditReport, maxViolations int) string {
	var lines []string
	statusIcon := "🟢"
	statusText := "PASSED"
	if !report.Passed {
		statusIcon = "🔴"
		statusText = "FAILED"
	}

	lvl := report.Level
	if lvl == "" {
		lvl = LevelStandard
	}

	lines = append(lines, fmt.Sprintf("%s NLP QUALITY GATE: %s [Profile: %s, Level: %s] (%d words, %d sents) - %d errors, %d warnings, %d info",
		statusIcon, statusText, strings.ToUpper(report.Profile), strings.ToUpper(string(lvl)),
		report.Metrics.TotalWords, report.Metrics.TotalSentences,
		report.ErrorCount, report.WarningCount, report.InfoCount))

	if len(report.Violations) == 0 {
		lines = append(lines, "✨ All quality gates satisfied cleanly.")
		return strings.Join(lines, "\n")
	}

	limit := len(report.Violations)
	if maxViolations > 0 && limit > maxViolations {
		limit = maxViolations
	}

	for i := 0; i < limit; i++ {
		v := report.Violations[i]
		loc := "doc"
		if v.Line != nil {
			loc = fmt.Sprintf("L%d", *v.Line)
		}
		sev := strings.ToUpper(string(v.Severity))
		if sev == "" {
			sev = "WARN"
		}

		snip := v.Snippet
		if len(snip) > 80 {
			snip = snip[:77] + "..."
		}
		snip = strings.ReplaceAll(snip, "\n", " ")

		if v.Message != "" && v.Line != nil {
			msg := strings.ReplaceAll(v.Message, "\n", " ")
			lines = append(lines, fmt.Sprintf("  %s %-5s %s: %s -> %s", loc, sev, v.Rule, msg, v.Recommendation))
		} else if snip != "" {
			lines = append(lines, fmt.Sprintf("  %s %-5s %s: \"%s\" -> %s", loc, sev, v.Rule, snip, v.Recommendation))
		} else {
			lines = append(lines, fmt.Sprintf("  %s %-5s %s: %s -> %s", loc, sev, v.Rule, v.Message, v.Recommendation))
		}
	}

	if maxViolations > 0 && len(report.Violations) > maxViolations {
		lines = append(lines, fmt.Sprintf("  ... and %d more findings omitted (use --max-violations 0 to show all)", len(report.Violations)-maxViolations))
	}

	lines = append(lines, fmt.Sprintf("Result: %d errors, %d warnings across %d words.", report.ErrorCount, report.WarningCount, report.Metrics.TotalWords))
	return strings.Join(lines, "\n")
}

func formatFullReport(report *AuditReport, showFixHints bool, verbose bool, maxViolations int) string {
	var lines []string
	statusIcon := "🟢"
	statusText := "PASSED"
	if !report.Passed {
		statusIcon = "🔴"
		statusText = "FAILED"
	}

	lvl := report.Level
	if lvl == "" {
		lvl = LevelStandard
	}

	lines = append(lines, strings.Repeat("=", 76))
	lines = append(lines, fmt.Sprintf("  NLP QUALITY GATE: %s %s (Profile: %s, Level: %s)", statusIcon, statusText, strings.ToUpper(report.Profile), strings.ToUpper(string(lvl))))
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
	lines = append(lines, fmt.Sprintf("• Severity Summary: %d errors, %d warnings, %d info", report.ErrorCount, report.WarningCount, report.InfoCount))
	lines = append(lines, strings.Repeat("-", 76))

	if len(report.Violations) > 0 {
		lines = append(lines, fmt.Sprintf("VIOLATIONS DETECTED (%d):", len(report.Violations)))
		limit := len(report.Violations)
		if maxViolations > 0 && limit > maxViolations {
			limit = maxViolations
		}

		for idx := 0; idx < limit; idx++ {
			v := report.Violations[idx]
			loc := "Document Scope"
			if v.Line != nil {
				loc = fmt.Sprintf("Line %d", *v.Line)
			}
			sev := strings.ToUpper(string(v.Severity))
			if sev == "" {
				sev = "WARN"
			}
			lines = append(lines, fmt.Sprintf("\n[%d] Stage %d [%s] - %s (%s)", idx+1, v.Stage, sev, v.Rule, loc))
			lines = append(lines, fmt.Sprintf("    Message: %s", v.Message))
			if v.Snippet != "" {
				lines = append(lines, fmt.Sprintf("    Context: \"%s\"", v.Snippet))
			}
			if showFixHints && v.Recommendation != "" {
				lines = append(lines, fmt.Sprintf("    💡 Fix:  %s", v.Recommendation))
			}
		}

		if maxViolations > 0 && len(report.Violations) > maxViolations {
			lines = append(lines, fmt.Sprintf("\n... and %d more findings omitted (use --max-violations 0 to show all)", len(report.Violations)-maxViolations))
		}
	} else {
		lines = append(lines, "✨ All Stage 1, Stage 2, and Stage 3 quality gates satisfied cleanly.")
	}

	lines = append(lines, strings.Repeat("=", 76))
	return strings.Join(lines, "\n")
}
