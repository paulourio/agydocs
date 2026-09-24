package gate

import (
	"fmt"
	"math"
	"os"
	"path/filepath"
	"testing"
)

func TestAll9MarkdownFilesPassWithParity(t *testing.T) {
	docs := []struct {
		relPath string
		profile string
		words   int
		sents   int
		cv      float64
		ovh     float64
		zmCount int
		zmPct   float64
		em      int
		pbr     float64
		lag     *int
	}{
		{
			relPath: "references/scientific_papers.md",
			profile: "paper",
			words:   960,
			sents:   54,
			cv:      0.533,
			ovh:     5.46,
			zmCount: 8,
			zmPct:   0.83,
			em:      0,
			pbr:     37.00,
			lag:     intPtr(69),
		},
		{
			relPath: "references/technical_systems.md",
			profile: "rfc",
			words:   516,
			sents:   27,
			cv:      0.451,
			ovh:     3.87,
			zmCount: 3,
			zmPct:   0.58,
			em:      0,
			pbr:     24.00,
			lag:     intPtr(58),
		},
		{
			relPath: "references/guides_tutorials.md",
			profile: "tutorial",
			words:   280,
			sents:   16,
			cv:      0.558,
			ovh:     3.11,
			zmCount: 0,
			zmPct:   0.00,
			em:      0,
			pbr:     8.00,
			lag:     intPtr(54),
		},
		{
			relPath: "references/conversational_pairing.md",
			profile: "chat",
			words:   397,
			sents:   27,
			cv:      0.416,
			ovh:     3.89,
			zmCount: 3,
			zmPct:   0.76,
			em:      0,
			pbr:     11.00,
			lag:     nil,
		},
		{
			relPath: "SKILL.md",
			profile: "essay",
			words:   501,
			sents:   30,
			cv:      0.534,
			ovh:     3.90,
			zmCount: 5,
			zmPct:   1.00,
			em:      0,
			pbr:     23.00,
			lag:     intPtr(244),
		},
		{
			relPath: "references/global_guidance.md",
			profile: "essay",
			words:   1511,
			sents:   78,
			cv:      0.590,
			ovh:     5.45,
			zmCount: 10,
			zmPct:   0.66,
			em:      3,
			pbr:     17.75,
			lag:     intPtr(184),
		},
		{
			relPath: "resources/anti_patterns_catalog.md",
			profile: "essay",
			words:   299,
			sents:   25,
			cv:      0.411,
			ovh:     3.10,
			zmCount: 2,
			zmPct:   0.67,
			em:      0,
			pbr:     7.00,
			lag:     intPtr(71),
		},
		{
			relPath: "resources/metric_cheat_sheet.md",
			profile: "rfc",
			words:   539,
			sents:   36,
			cv:      0.605,
			ovh:     5.45,
			zmCount: 5,
			zmPct:   0.93,
			em:      0,
			pbr:     36.00,
			lag:     intPtr(70),
		},
		{
			relPath: "examples/before_after_transformations.md",
			profile: "essay",
			words:   709,
			sents:   52,
			cv:      0.470,
			ovh:     4.67,
			zmCount: 4,
			zmPct:   0.56,
			em:      0,
			pbr:     22.00,
			lag:     intPtr(31),
		},
	}

	for _, d := range docs {
		t.Run(d.relPath, func(t *testing.T) {
			path := filepath.Join("../..", d.relPath)
			content, err := os.ReadFile(path)
			if err != nil {
				t.Fatalf("Failed to read %s: %v", path, err)
			}
			rep, err := AuditDocument(string(content), d.profile)
			if err != nil {
				t.Fatalf("AuditDocument failed for %s: %v", d.relPath, err)
			}

			if !rep.Passed {
				for _, v := range rep.Violations {
					t.Errorf("Unexpected violation in %s: %s - %s", d.relPath, v.Rule, v.Message)
				}
			}

			m := rep.Metrics
			if m.TotalWords != d.words {
				t.Errorf("%s: words = %d, want %d", d.relPath, m.TotalWords, d.words)
			}
			if m.TotalSentences != d.sents {
				t.Errorf("%s: sentences = %d, want %d", d.relPath, m.TotalSentences, d.sents)
			}
			if math.Abs(m.BurstinessCV-d.cv) > 0.005 {
				t.Errorf("%s: burstiness CV = %.3f, want %.3f", d.relPath, m.BurstinessCV, d.cv)
			}
			if math.Abs(m.SyntacticOverhead-d.ovh) > 0.01 {
				t.Errorf("%s: syntactic overhead = %.2f, want %.2f", d.relPath, m.SyntacticOverhead, d.ovh)
			}
			if m.ZombieNominalsCount != d.zmCount {
				t.Errorf("%s: zombie nominals count = %d, want %d", d.relPath, m.ZombieNominalsCount, d.zmCount)
			}
			if math.Abs(m.ZombieNominalsPct-d.zmPct) > 0.01 {
				t.Errorf("%s: zombie nominals pct = %.2f, want %.2f", d.relPath, m.ZombieNominalsPct, d.zmPct)
			}
			if m.EmDashesCount != d.em {
				t.Errorf("%s: em dashes = %d, want %d", d.relPath, m.EmDashesCount, d.em)
			}
			if math.Abs(m.PunctuationBalanceRatio-d.pbr) > 0.01 {
				t.Errorf("%s: punctuation balance ratio = %.2f, want %.2f", d.relPath, m.PunctuationBalanceRatio, d.pbr)
			}
			if d.lag != nil {
				if m.ConcreteAnchorLagWords == nil || *m.ConcreteAnchorLagWords != *d.lag {
					val := "<nil>"
					if m.ConcreteAnchorLagWords != nil {
						val = fmt.Sprintf("%d", *m.ConcreteAnchorLagWords)
					}
					t.Errorf("%s: lag = %s, want %d", d.relPath, val, *d.lag)
				}
			} else {
				if m.ConcreteAnchorLagWords != nil {
					t.Errorf("%s: lag = %v, want nil", d.relPath, *m.ConcreteAnchorLagWords)
				}
			}

			if m.HumanVoiceIndex != 100.0 {
				t.Errorf("%s: HVI = %.1f, want 100.0", d.relPath, m.HumanVoiceIndex)
			}
			if m.TechnicalPrecisionIndex != 100.0 {
				t.Errorf("%s: TPI = %.1f, want 100.0", d.relPath, m.TechnicalPrecisionIndex)
			}
		})
	}
}

func TestAllBenchmarksAndNewReferencesPassQualityGate(t *testing.T) {
	docs := []struct {
		relPath string
		profile string
	}{
		{relPath: "references/briefing_format.md", profile: "essay"},
		{relPath: "benchmarks/rfc_kernel_bypass.md", profile: "rfc"},
		{relPath: "benchmarks/paper_async_fixed_point.md", profile: "paper"},
		{relPath: "benchmarks/tutorial_lockfree_spsc.md", profile: "tutorial"},
		{relPath: "benchmarks/essay_leaky_abstractions.md", profile: "essay"},
		{relPath: "benchmarks/chat_socket_starvation.md", profile: "chat"},
		{relPath: "benchmarks/briefing_incident_summary.md", profile: "briefing"},
	}

	for _, d := range docs {
		t.Run(d.relPath, func(t *testing.T) {
			path := filepath.Join("../..", d.relPath)
			content, err := os.ReadFile(path)
			if err != nil {
				t.Fatalf("Failed to read %s: %v", path, err)
			}
			rep, err := AuditDocument(string(content), d.profile)
			if err != nil {
				t.Fatalf("AuditDocument failed for %s: %v", d.relPath, err)
			}
			if !rep.Passed {
				for _, v := range rep.Violations {
					t.Errorf("Unexpected violation in %s: %s - %s", d.relPath, v.Rule, v.Message)
				}
			}
		})
	}
}

