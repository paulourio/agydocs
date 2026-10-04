package gate

import (
	"fmt"
	"math"
)

// AuditStage3CompositeScoring audits Stage 3: Composite Index (HVI & TPI) and overall pass/fail determination.
func AuditStage3CompositeScoring(profile ProfileConfig, level Level, metrics *QualityMetrics, violations *[]Violation) {
	hvi := 100.0
	tpi := 100.0

	addViolation := func(rule string, message string, line *int, snippet string, rec string) {
		sev := GetRuleSeverity(rule, 3, level)
		if sev == SeverityOff {
			return
		}
		*violations = append(*violations, Violation{
			Stage:          3,
			Severity:       sev,
			Rule:           rule,
			Message:        message,
			Line:           line,
			Snippet:        snippet,
			Recommendation: rec,
		})
	}

	// Stage 1 penalty
	stage1Count := 0
	for _, v := range *violations {
		if v.Stage == 1 {
			stage1Count++
		}
	}
	if stage1Count > 0 {
		hvi -= float64(stage1Count) * 15.0
	}

	// Stage 2 penalties with statistical sample size guards
	// Burstiness penalty (only evaluate with at least 8 sentences)
	if metrics.TotalSentences >= 8 && metrics.BurstinessCV < profile.TargetBurstinessMin {
		delta := profile.TargetBurstinessMin - metrics.BurstinessCV
		penalty := delta * 80.0
		if penalty > 25.0 {
			penalty = 25.0
		}
		hvi -= penalty
	}

	// Zombie nominal penalty (only evaluate with at least 150 words)
	if metrics.TotalWords >= 150 && metrics.ZombieNominalsPct > profile.MaxZombieNominalsPct {
		deltaNom := metrics.ZombieNominalsPct - profile.MaxZombieNominalsPct
		penHVI := deltaNom * 10.0
		if penHVI > 20.0 {
			penHVI = 20.0
		}
		hvi -= penHVI

		penTPI := deltaNom * 5.0
		if penTPI > 15.0 {
			penTPI = 15.0
		}
		tpi -= penTPI
	}

	// Em-dash penalty (only evaluate with at least 150 words)
	if metrics.TotalWords >= 150 && metrics.EmDashesPer100w > profile.MaxEmDashesPer100w {
		hvi -= 10.0
	}

	// Demonstrative anchoring penalty (only evaluate with at least 3 demonstratives)
	if metrics.SentenceInitialThisTotal >= 3 && metrics.DemonstrativeAnchoringIndex < profile.MinDemonstrativeAnchoring {
		deltaDAI := profile.MinDemonstrativeAnchoring - metrics.DemonstrativeAnchoringIndex
		hvi -= deltaDAI * 30.0
	}

	// Syntactic overhead penalty (only evaluate with at least 150 words and 3 sentences)
	if metrics.TotalWords >= 150 && metrics.TotalSentences >= 3 && metrics.SyntacticOverhead > profile.MaxSyntacticOverhead {
		tpi -= 15.0
	}

	metrics.HumanVoiceIndex = math.Max(0.0, round1(hvi))
	metrics.TechnicalPrecisionIndex = math.Max(0.0, round1(tpi))

	if metrics.HumanVoiceIndex < profile.MinHVI {
		addViolation(
			"Low Human Voice Index",
			fmt.Sprintf("Human Voice Index (%.1f) is below minimum %.1f.", metrics.HumanVoiceIndex, profile.MinHVI),
			nil,
			"Composite voice score failed",
			"Address Stage 1 and Stage 2 violations to recover authentic human cadence.",
		)
	}

	if metrics.TechnicalPrecisionIndex < profile.MinTPI {
		addViolation(
			"Low Technical Precision Index",
			fmt.Sprintf("Technical Precision Index (%.1f) is below minimum %.1f.", metrics.TechnicalPrecisionIndex, profile.MinTPI),
			nil,
			"Composite precision score failed",
			"Ground assertions in exact domain primitives and concrete physical referents.",
		)
	}
}
