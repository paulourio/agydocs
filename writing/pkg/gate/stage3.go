package gate

import (
	"fmt"
	"math"
)

// AuditStage3CompositeScoring audits Stage 3: Composite Index (HVI & TPI) and overall pass/fail determination.
func AuditStage3CompositeScoring(profile ProfileConfig, metrics *QualityMetrics, violations *[]Violation) {
	hvi := 100.0
	tpi := 100.0

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

	// Stage 2 penalties
	// Burstiness penalty
	if metrics.BurstinessCV < profile.TargetBurstinessMin {
		delta := profile.TargetBurstinessMin - metrics.BurstinessCV
		penalty := delta * 80.0
		if penalty > 25.0 {
			penalty = 25.0
		}
		hvi -= penalty
	}

	// Zombie nominal penalty
	if metrics.ZombieNominalsPct > profile.MaxZombieNominalsPct {
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

	// Em-dash penalty
	if metrics.EmDashesPer100w > profile.MaxEmDashesPer100w {
		hvi -= 10.0
	}

	// Demonstrative anchoring penalty
	if metrics.DemonstrativeAnchoringIndex < profile.MinDemonstrativeAnchoring {
		deltaDAI := profile.MinDemonstrativeAnchoring - metrics.DemonstrativeAnchoringIndex
		hvi -= deltaDAI * 30.0
	}

	// Syntactic overhead penalty
	if metrics.SyntacticOverhead > profile.MaxSyntacticOverhead {
		tpi -= 15.0
	}

	metrics.HumanVoiceIndex = math.Max(0.0, round1(hvi))
	metrics.TechnicalPrecisionIndex = math.Max(0.0, round1(tpi))

	if metrics.HumanVoiceIndex < profile.MinHVI {
		*violations = append(*violations, Violation{
			Stage:          3,
			Rule:           "Low Human Voice Index",
			Message:        fmt.Sprintf("Human Voice Index (%.1f) is below minimum %.1f.", metrics.HumanVoiceIndex, profile.MinHVI),
			Line:           nil,
			Snippet:        "Composite voice score failed",
			Recommendation: "Address Stage 1 and Stage 2 violations to recover authentic human cadence.",
		})
	}

	if metrics.TechnicalPrecisionIndex < profile.MinTPI {
		*violations = append(*violations, Violation{
			Stage:          3,
			Rule:           "Low Technical Precision Index",
			Message:        fmt.Sprintf("Technical Precision Index (%.1f) is below minimum %.1f.", metrics.TechnicalPrecisionIndex, profile.MinTPI),
			Line:           nil,
			Snippet:        "Composite precision score failed",
			Recommendation: "Ground assertions in exact domain primitives and concrete physical referents.",
		})
	}
}
